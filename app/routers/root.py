from fastapi import APIRouter
from starlette.responses import PlainTextResponse

router = APIRouter()

@router.get("/", response_class=PlainTextResponse)
def root():
    return "This is an unofficial OPSI IPXE server"
