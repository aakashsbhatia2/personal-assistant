from fastapi import APIRouter
from pydantic import BaseModel

from services.voiceProcessor import handleVoiceRequest

router = APIRouter()

class AssistantRequest(BaseModel):
    text: str

@router.post("/assistant")
async def assistant(payload: AssistantRequest):
    
    body = payload.dict()
    resp = await handleVoiceRequest(body)

    return {"message": "Success"}
