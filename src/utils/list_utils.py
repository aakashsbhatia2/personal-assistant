import requests
import os
import json
import re
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

def add_item_to_list(list_name, item):
    if not list_name or not list_name.strip():
        print("Error: list_name cannot be empty.")
        return

    if not item or not item.strip():
        print("Error: item cannot be empty.")
        return

    slug = re.sub(r"[^a-z0-9_]", "_", list_name.strip().lower())
    entity_id = f"todo.{slug}"

    headers = getHeaders()
    service_url = f"{HA_URL}/api/services/todo/add_item"

    payload = {
        "entity_id": entity_id,
        "item": item.strip()
    }

    try:
        res = requests.post(service_url, headers=headers, json=payload, timeout=10)
    except requests.RequestException as e:
        print("Request failed:", e)
        return

    if res.ok:
        print(f"Added '{item}' to {entity_id}")
    else:
        # This is ALL the data HA provides
        print("Failed to add item")
        print("Status:", res.status_code)
        print("Reason:", res.reason)
        print("Headers:", dict(res.headers))
        print("Body:", res.text)

def remove_item_from_list(list_name, item):
    if not list_name or not list_name.strip():
        print("Error: list_name cannot be empty.")
        return

    if not item or not item.strip():
        print("Error: item cannot be empty.")
        return

    # Normalize list name → entity_id
    slug = re.sub(r"[^a-z0-9_]", "_", list_name.strip().lower())
    entity_id = f"todo.{slug}"

    headers = getHeaders()
    service_url = f"{HA_URL}/api/services/todo/remove_item"

    payload = {
        "entity_id": entity_id,
        "item": item.strip()
    }

    try:
        res = requests.post(service_url, headers=headers, json=payload, timeout=10)
    except   requests.RequestException as e:
        print("Request failed:", e)
        return

    if res.ok:
        print(f"Removed '{item}' from {entity_id}")
    else:
        print("Failed to remove item")
        print("Status:", res.status_code)
        print("Reason:", res.reason)
        print("Headers:", dict(res.headers))
        print("Body:", res.text)

def list_all_lists():
    """Fetch all to-do lists from Home Assistant and return as ToDoList objects."""
    headers = getHeaders()
    
    # Query all states with entity_id starting with "todo."
    states_url = f"{HA_URL}/api/states"
    
    try:
        res = requests.get(states_url, headers=headers, timeout=10)
        res.raise_for_status()
    except requests.RequestException as e:
        print(f"Failed to fetch lists: {e}")
        return []
    
    states = res.json()
    todo_states = [s for s in states if s.get("entity_id", "").startswith("todo.")]
    
    if not todo_states:
        print("No to-do lists found.")
        return []

    return todo_states
