import requests
import os
import json
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

HA_URL = os.getenv("HA_URL")
TOKEN = os.getenv("HA_TOKEN")

def getHeaders():
    return {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    }


def create_todo_list(list_name):
    if (not list_name):
        print("Error: List name cannot be empty.")
        return

    headers = getHeaders()

    # Step 1: Initialize the configuration flow for local_todo
    print(f"Connecting to: {HA_URL}...")
    init_url = f"{HA_URL}/api/config/config_entries/flow"
    try:
        init_res = requests.post(init_url, headers=headers, json={"handler": "local_todo"})
        init_res.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Connection failed: {e}")
        return

    flow_id = init_res.json().get("flow_id")
    print(f"Flow initialized (ID: {flow_id})")

    # Step 2: Submit the list name using the specific 'todo_list_name' key
    conf_url = f"{HA_URL}/api/config/config_entries/flow/{flow_id}"
    conf_res = requests.post(conf_url, headers=headers, json={"todo_list_name": list_name})
    
    if conf_res.status_code == 200:
        result_data = conf_res.json()
        if result_data.get("type") == "create_entry":
            print(f"Success! To-do list '{list_name}' created.")
        else:
            print(f"Unexpected result type: {result_data.get('type')}")
            print(f"Response: {json.dumps(result_data, indent=2)}")
    else:
        print(f"Configuration failed ({conf_res.status_code}): {conf_res.text}")
