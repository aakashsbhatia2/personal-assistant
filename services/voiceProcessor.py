import requests
from services.voiceProcessorConstants import VOICE_ASSISTANT_SYSTEM_PROMPT

async def handleVoiceRequest(body):
    print(body)
    url = "http://localhost:11434/api/chat"
    payload = {
        "model": "llama3.1:8b",    # or whichever model you pulled
        "stream": False,
        "messages": [
            { "role": "system", "content": VOICE_ASSISTANT_SYSTEM_PROMPT },
            { "role": "user", "content": body['text'] }
        ]
    }

    response = requests.post(url, json=payload)
    response.raise_for_status()

    return response.json()["message"]["content"]
