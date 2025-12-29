import json
import websockets
import requests
from dotenv import load_dotenv
import os

load_dotenv()
ALLOWED_DOMAINS = {"light"}

def build_entities_with_tags(entities, devices, areas, floors, labels):
    devices_by_id = {d["id"]: d for d in devices}
    areas_by_id = {a["area_id"]: a for a in areas}
    floors_by_id = {f["floor_id"]: f for f in floors}
    labels_by_id  = {l["label_id"]: l["name"] for l in labels}

    result = []

    for e in entities:
        device = devices_by_id.get(e.get("device_id"))
        area_id = e.get("area_id") or (device and device.get("area_id"))
        area = areas_by_id.get(area_id)
        floor = floors_by_id.get(area.get("floor_id")) if area else None
        label_ids = set()
        label_ids.update(e.get("labels", []))
        if device:
            label_ids.update(device.get("labels", []))
        if area:
            label_ids.update(area.get("labels", []))

        result.append({
            "entity_id": e["entity_id"],
            "area": area["name"] if area else None,
            "floor": floor["name"] if floor else None,
            "device_id": e.get("device_id"),
            "labels": [labels_by_id[l] for l in label_ids if l in labels_by_id]
        })

    return result

async def ws_request(ws, msg_id, msg_type):
    await ws.send(json.dumps({
        "id": msg_id,
        "type": msg_type
    }))
    resp = json.loads(await ws.recv())
    return resp["result"]

async def get_entities(ws):
    return await ws_request(ws, 1, "config/entity_registry/list")

async def get_devices(ws):
    return await ws_request(ws, 2, "config/device_registry/list")

async def get_areas(ws):
    return await ws_request(ws, 3, "config/area_registry/list")

async def get_floors(ws):
    return await ws_request(ws, 4, "config/floor_registry/list")

async def get_labels(ws):
    return await ws_request(ws, 5, "config/label_registry/list")

def filter_whitelisted_entities(indexed_entities):
    return [
        e for e in indexed_entities
        if e["entity_id"].split(".", 1)[0] in ALLOWED_DOMAINS
    ]

async def get_home_assistant_data():
    URL = os.getenv('HOME_ASSISTANT_WEB_SOCKET_URL')
    TOKEN = os.getenv('HOME_ASSISTANT_TOKEN')
    async with websockets.connect(URL) as ws:
        # auth_required
        await ws.recv()

        # authenticate
        await ws.send(json.dumps({
            "type": "auth",
            "access_token": TOKEN
        }))
        await ws.recv()  # auth_ok

        entities = await get_entities(ws)
        devices = await get_devices(ws)
        areas = await get_areas(ws)
        floors = await get_floors(ws)
        labels = await get_labels(ws)

        safe_entities = filter_whitelisted_entities(entities)
        result = build_entities_with_tags(safe_entities, devices, areas, floors, labels)

        return result

def get_prompt(command_text, home_assistant_entities):
    return "You are an entity selection engine. \
            Task: Given a user command and a list of Home Assistant entities, select the SINGLE best matching entity. \
            Rules (follow strictly in order):\
            1. Match FLOOR first (exact text match, case-insensitive). \
            2. Then match AREA or LABEL that semantically matches the room name. \
            3. Prefer entities whose LABELS explicitly mention the room. \
            4. Ignore entities on other floors, even if names are similar. \
            5. If multiple entities match equally, choose the one whose labels most closely match the room. \
            6. If no entity clearly matches, return UNKNOWN. \
            7. Do NOT invent entity IDs. \
            8. Only select from the provided list.\
            User command: \"" + command_text + "\" \
            Entities: \"" + json.dumps(home_assistant_entities) + "\" \
            Output format: \
            Return ONLY valid JSON in this exact format: \
            { \"entity_id\": \"<entity_id>\" } \
            If unsure, return: \
            { \"entity_id\": \"UNKNOWN\" }"



async def get_target_entity_id(command, home_assistant_entities):
    url = os.getenv('OLLAMA_URL')
    params = {
        'model': 'llama3.2:3b',
        'stream': False,
        'prompt': get_prompt(command['text'], home_assistant_entities),
        'format': 'json'
    }

    response = requests.post(url + '/generate', json=params)
    return response.json()['response']

async def process_request(command):
    home_assistant_entities = await get_home_assistant_data()
    # with open('entities.json', 'w', encoding='utf-8') as f:
    #     json.dump(home_assistant_entities, f, ensure_ascii=False, indent=4)

    target_entity_id = await get_target_entity_id(command, home_assistant_entities)
    return target_entity_id


