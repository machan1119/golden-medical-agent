from fastapi import APIRouter, Request
from core.store import form_service

router = APIRouter()


@router.post("/")
async def store_endpoint(request: Request):
    body = await request.json()
    success = form_service.store_intake_data(
        intent=body.get("intent"), data=body.get("data")
    )
    if success:
        print("Data storing is successfully.")
    return
