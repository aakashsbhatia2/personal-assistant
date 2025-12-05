from fastapi import APIRouter

router = APIRouter()

@router.post("/assistant")
async def assistant(payload: dict):
    return {input: payload}
