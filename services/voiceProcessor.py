import httpx
from services.voiceProcessorConstants import VOICE_ASSISTANT_SYSTEM_PROMPT

async def handleVoiceRequest(body):
    url = "http://localhost:11434/api/chat"
    payload = {
        "model": "llama3.2:3b",    # or whichever model you pulled
        "stream": False,
        "messages": [
            { "role": "system", "content": VOICE_ASSISTANT_SYSTEM_PROMPT },
            { "role": "user", "content": body["text"] }
        ]
    }
    try: 
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()["message"]["content"]
    except httpx.HTTPStatusError as e:
        print("status:", e.response.status_code)
        print("body:", e.response.text)
        raise
