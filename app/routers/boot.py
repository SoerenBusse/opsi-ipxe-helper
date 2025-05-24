from http import HTTPStatus

from fastapi import APIRouter, Depends, Query
from jinja2 import Environment
from starlette.responses import PlainTextResponse

from dependencies import get_settings, get_jinja_environment, verify_credentials
from opsiapi import OpsiApi
from settings import Settings
from utils.utils import render_error_template

router = APIRouter()


@router.get("/boot")
async def boot(settings: Settings = Depends(get_settings),
               jinja: Environment = Depends(get_jinja_environment)):
    # Get tool entry url without scheme
    template = jinja.get_template("boot.menu.ipxe")
    rendered = template.render(
        external_address=settings.ipxe.external_address,
        tool_entries=settings.ipxe.tools.entries,
        netboot_efi_url=settings.opsi.netboot_efi_url
    )
    return PlainTextResponse(rendered, status_code=HTTPStatus.OK)


@router.get("/boot/opsi-client-setup", dependencies=[Depends(verify_credentials)])
async def boot_opsi_client_setup(mac: str = Query(pattern="^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$"),
                                 settings: Settings = Depends(get_settings),
                                 jinja_environment: Environment = Depends(get_jinja_environment)):
    # Check if client already exists
    async with OpsiApi(settings.opsi) as opsi:
        client = await opsi.get_client(mac=mac)

        if client:
            # Client found
            template = jinja_environment.get_template("opsi-client-found.ipxe")
            return PlainTextResponse(template.render(mac=client["hardwareAddress"], fqdn=client["id"]), status_code=200)

        # Get product ids
        netboot_product_ids = sorted(await opsi.get_netboot_product_ids())
        product_group_ids = sorted(await opsi.get_product_group_ids())

        if not netboot_product_ids or not product_group_ids:
            rendered_error = render_error_template(
                jinja_environment,
                "Missing netboot products or product group. Have you installed / created them?"
            )

            # We need to send it as OK, so that the IPXE client shows the error message
            return PlainTextResponse(rendered_error, status_code=HTTPStatus.OK)

        template = jinja_environment.get_template("create-opsi-client.menu.ipxe")
        rendered = template.render(
            netboot_product_ids=netboot_product_ids,
            product_group_ids=product_group_ids,
            hostname="",
            domain=settings.opsi.domain,
            external_address=settings.ipxe.external_address,
            netboot_efi_url=settings.opsi.netboot_efi_url
        )
        return PlainTextResponse(rendered, status_code=HTTPStatus.OK)


@router.get("/boot/opsi-client-setup/create-client", dependencies=[Depends(verify_credentials)])
async def boot_opsi_create_client(mac: str = Query(pattern="^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$"),
                                  fqdn: str = Query(),
                                  system_uuid: str = Query(alias="system-uuid"),
                                  product_group_id: str = Query(alias="product-group-id"),
                                  netboot_id: str = Query(alias="netboot-id"),
                                  settings: Settings = Depends(get_settings)):
    async with OpsiApi(settings.opsi) as opsi:
        await opsi.create_client(
            fqdn,
            mac,
            system_uuid,
            settings.opsi.depot,
            check_if_exists=True
        )

        await opsi.reset_requested_product_actions(fqdn)
        await opsi.install_localboot_product_group(product_group_id, fqdn)
        await opsi.install_netboot_product(netboot_id, fqdn)

    return PlainTextResponse("Client created successful", status_code=HTTPStatus.CREATED)
