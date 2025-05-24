import logging
from contextlib import asynccontextmanager
from http import HTTPStatus
from typing import Any, AsyncGenerator

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from jinja2 import Environment, FileSystemLoader
from pydantic import ValidationError
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.staticfiles import StaticFiles

from opsiapi import OpsiApi, OpsiException
from routers import boot, root
from settings import Settings, StaticDirectoriesSetting
from utils.utils import render_error_template

logger = logging.getLogger('uvicorn.error')


@asynccontextmanager
async def lifespan(lifespan_app: FastAPI) -> AsyncGenerator[None, Any]:
    # Load settings and validate on startup
    logger.info("Load settings...")
    try:
        lifespan_app.state.settings = Settings()
    except ValidationError as e:
        logger.critical(f'Failed to load settings:')
        raise SystemExit(e)

    # Load Jinja templates
    logger.info("Load jinja templates...")
    lifespan_app.state.jinja_environment = Environment(loader=FileSystemLoader('templates'))

    # Check if OPSI is reachable
    logger.info("Check OPSI reachability...")
    try:
        async with OpsiApi(settings=lifespan_app.state.settings.opsi) as opsi_api:
            result = await opsi_api.backend_info()
            logger.info(
                f"Successfully checked connection to {lifespan_app.state.settings.opsi.rpc_url}: "
                f"OPSI Version: {result['opsiVersion']}"
            )
    except Exception as e:
        raise RuntimeError("Error while connecting to the Opsi API") from e

    logger.info("Mount static files...")
    lifespan_app.mount('/static/public',
                       StaticFiles(directory=lifespan_app.state.settings.directories.static.public),
                       name='static_public')

    # Start Server
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(root.router)
app.include_router(boot.router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return PlainTextResponse(
        render_error_template(request.app.state.jinja_environment, str(exc.detail)),
        headers=exc.headers,
        status_code=exc.status_code
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return PlainTextResponse(
        render_error_template(request.app.state.jinja_environment, str(exc)),
        status_code=HTTPStatus.BAD_REQUEST
    )


@app.exception_handler(OpsiException)
async def http_exception_handler(request: Request, exc: OpsiException):
    return PlainTextResponse(render_error_template(request.app.state.jinja_environment, exc.message),
                             status_code=exc.code)
