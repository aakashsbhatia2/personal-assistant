from fastapi import APIRouter
from pydantic import BaseModel

from services.assistantUtils import process_request

router = APIRouter()

class AssistantRequest(BaseModel):
    text: str

@router.post("/assistant")
async def assistant(payload: AssistantRequest):
    
    body = payload.dict()
    resp = await process_request(body)

    return {"message": resp}
