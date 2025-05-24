import logging
from contextlib import AbstractAsyncContextManager
from functools import wraps
from typing import Optional, List, Dict

import aiohttp
from aiohttp import BasicAuth
from jsonrpcclient import request, parse, Error

from settings import OpsiSettings

logger = logging.getLogger('uvicorn.error')


def check_session(f):
    async def wrapper(self, *args, **kwargs):
        if self._session is None:
            raise AttributeError("You have to call the api methods in an async with block")

        return await f(self, *args, **kwargs)

    return wrapper


class OpsiException(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message

    @staticmethod
    def from_rcp_response(error: Error) -> "OpsiException":
        code = error.code if error.code != 0 else 500
        return OpsiException(code, error.message)


class OpsiApi(AbstractAsyncContextManager):
    def __init__(self, settings: OpsiSettings):
        self._settings = settings
        self._session: Optional[aiohttp.ClientSession] = None
        self._rpc_url = self._settings.rpc_url

    async def __aenter__(self) -> "OpsiApi":
        auth = BasicAuth(login=self._settings.username, password=self._settings.password.get_secret_value())
        self._session = aiohttp.ClientSession(auth=auth, connector=aiohttp.TCPConnector(verify_ssl=False))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._session.close()

    @check_session
    async def backend_info(self):
        return await self._rpc_request(request("backend_info"))

    @check_session
    async def get_netboot_product_ids(self):
        netboot_products = await self._rpc_request(
            request("productOnDepot_getObjects", {"productType": "NetbootProduct"}))

        product_ids = {netboot_product["productId"] for netboot_product in netboot_products}
        return product_ids

    @check_session
    async def get_product_group_ids(self) -> List[str]:
        product_groups = await self._get_product_group_with_filter()

        # Create a set of unique product groups
        product_group_ids = set()

        for product_group_association in product_groups:
            product_group_ids.add(product_group_association["groupId"])

        return list(product_group_ids)

    @check_session
    async def install_netboot_product(self, product_id: str, client_id: str):
        requested_product_action = {
            "clientId": client_id,
            "productId": product_id,
            "actionRequest": "setup",
            "type": "ProductOnClient",
            "productType": "NetbootProduct"
        }

        await self._update_product_actions([requested_product_action])

    @check_session
    async def install_localboot_product_group(self, product_group_id: str, client_id: str):
        # Get products for a specific product_group
        product_group_members = await self._get_product_group_with_filter(group_id=product_group_id)

        # Add all product members of the product group as payload to the setup request
        requested_product_actions = []
        for member in product_group_members:
            requested_product_actions.append({
                "clientId": client_id,
                "productId": member["objectId"],
                "actionRequest": "setup",
                "type": "ProductOnClient",
                "productType": "LocalbootProduct"
            })

        await self._update_product_actions(requested_product_actions)

    @check_session
    async def reset_requested_product_actions(self, client_id: str):
        opsi_filter = {
            "clientId": client_id,
            "actionRequest": [
                "setup", "uninstall", "once"
            ]
        }

        result = await self._rpc_request(request("productOnClient_getObjects", opsi_filter))

        requested_product_actions = []
        for member in result:
            requested_product_actions.append({
                "clientId": client_id,
                "productId": member["productId"],
                "actionRequest": "none",
                "type": member["type"],
                "productType": member["productType"]
            })

        if requested_product_actions:
            await self._update_product_actions(requested_product_actions)
        else:
            logger.info(f"No products need a reset on {client_id}")

    @check_session
    async def create_client(self, fqdn: str, mac: str, system_uuid: str, depot: str, check_if_exists=True):
        if check_if_exists:
            # Check if client with FQDN already exists
            for opsi_filter in [{"id": fqdn}, {"hardwareAddress": mac}]:
                exists = await self._rpc_request(request("host_getObjects", opsi_filter))

                if exists:
                    client = exists[0]
                    raise OpsiException(
                        400,
                        f"Client {fqdn} or MAC {mac} already exists."
                        f" Created at {client["created"]}. "
                        f" Last Seen {client["lastSeen"]}."
                        f" IP-Address: {client['ipAddress']}."
                    )

        host = {
            "hardwareAddress": mac,
            "id": fqdn,
            "systemUUID": system_uuid,
            "notes": "Automatically created by iPXE loader",
            "type": "OpsiClient"
        }

        # Create client
        await self._rpc_request(request("host_createObjects", [host]))

        depot_config = {
            "configId": "clientconfig.depot.id",
            "values": [depot],
            "type": "ConfigState",
            "objectId": fqdn
        }

        # Set depot for client
        await self._rpc_request(request("configState_updateObjects", [[depot_config]]))

    @check_session
    async def get_client(self, mac: str = None, fqdn: str = None, system_uuid: str = None) -> Optional[Dict]:
        opsi_filter = {}

        if mac is not None:
            opsi_filter["hardwareAddress"] = mac

        if fqdn is not None:
            opsi_filter["id"] = fqdn

        if system_uuid is not None:
            opsi_filter["systemUUID"] = system_uuid

        result = await self._rpc_request(request("host_getObjects", opsi_filter))

        if not isinstance(result, List):
            raise OpsiException(500, "Client list is not a list")

        if not result:
            return None

        if len(result) > 1:
            raise OpsiException(400, "Request returned multiple clients")

        return result[0]

    async def _get_product_group_with_filter(self, group_id: str = None) -> List[Dict]:
        opsi_filter = {
            "groupType": "ProductGroup"
        }

        if group_id is not None:
            opsi_filter["groupId"] = group_id

        result = await self._rpc_request(request("objectToGroup_getObjects", opsi_filter))

        if not isinstance(result, List):
            raise OpsiException(500, "Result of product groups is not a list")

        return result

    async def _rpc_request(self, rpc_json):
        response = await self._session.post(self._rpc_url, json=rpc_json)

        if not response.ok:
            match response.status:
                case 401:
                    message = "Unauthorized. Check username and password."
                case _:
                    message = f"Unexpected status response from Opsi API"

            raise OpsiException(response.status, message)

        rpc_response = parse(await response.json())

        if isinstance(rpc_response, Error):
            raise OpsiException.from_rcp_response(rpc_response)

        return rpc_response.result

    async def _update_product_actions(self, requested_product_actions: List[Dict]):
        for product in requested_product_actions:
            logger.info(f"[{product["clientId"]}][{product["productId"]}] Set action {product['actionRequest']}")

        await self._rpc_request(request("productOnClient_updateObjects", [requested_product_actions]))
