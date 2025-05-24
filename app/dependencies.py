import secrets
from http import HTTPStatus

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPBasicCredentials, HTTPBasic
from jinja2 import Environment
from starlette.requests import Request

from settings import Settings

security = HTTPBasic()


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_jinja_environment(request: Request) -> Environment:
    return request.app.state.jinja_environment

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security),
                       settings: Settings = Depends(get_settings)):
    is_correct_username = secrets.compare_digest(credentials.username.encode("utf8"),
                                                 settings.ipxe.username.encode("utf8"))

    is_correct_password = secrets.compare_digest(credentials.password.encode("utf8"),
                                                 settings.ipxe.password.get_secret_value().encode("utf8"))

    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
