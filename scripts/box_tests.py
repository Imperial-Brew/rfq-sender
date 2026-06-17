from __future__ import annotations
from boxsdk import Client
from boxsdk.exception import BoxAPIException
from typing import Iterable
from typing import Sequence
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.secrets import get_section

def get_box_client():
    from scripts.box.box_integration import BoxIntegration
    bi = BoxIntegration()
    return bi.client

def _check_folder(client: Client, folder_id: str) -> dict:
    f = client.folder(folder_id).get()
    return {"id": f.id, "name": f.name, "type": f.type}

def _check_file(client: Client, file_id: str) -> dict:
    f = client.file(file_id).get()
    return {
        "id": f.id,
        "name": f.name,
        "size": getattr(f, "size", None),
        "sha1": getattr(f, "sha1", None),
        "type": f.type,
    }

def validate_box_resources(ids: dict[str, str]) -> list[tuple[str, dict]]:
    client = get_box_client()
    results: list[tuple[str, dict]] = []
    for label, rid in ids.items():
        if not rid:
            results.append((label, {"ok": False, "error": "ID is empty"}))
            continue
        try:
            if label.endswith("_FOLDER_ID"):
                meta = _check_folder(client, rid)
            else:
                meta = _check_file(client, rid)
            results.append((label, {"ok": True, "meta": meta}))
        except BoxAPIException as e:
            results.append((label, {"ok": False, "error": str(e)}))
        except Exception as e:  # fallback
            results.append((label, {"ok": False, "error": str(e)}))
    return results

# Example usage
box_secrets = get_section("box")
ids_to_check = {
    "BOX_APP_DATA_FOLDER_ID": box_secrets.get("BOX_APP_DATA_FOLDER_ID"),
    "BOX_QUEUE_FILE_ID": box_secrets.get("BOX_QUEUE_FILE_ID"),
    "BOX_RFQ_MASTER_FILE_ID": box_secrets.get("BOX_RFQ_MASTER_FILE_ID"),
    "BOX_RFQ_RESPONSES_FILE_ID": box_secrets.get("BOX_RFQ_RESPONSES_FILE_ID"),
    "BOX_APP_CONFIG_FOLDER_ID": box_secrets.get("BOX_APP_CONFIG_FOLDER_ID"),
    "BOX_CONTACTS_FILE_ID": box_secrets.get("BOX_CONTACTS_FILE_ID"),
    "BOX_VENDOR_OPTIONS_FILE_ID": box_secrets.get("BOX_VENDOR_OPTIONS_FILE_ID"),
    "BOX_FAMILIAR_SPECS_FILE_ID": box_secrets.get("BOX_FAMILIAR_SPECS_FILE_ID"),
    "BOX_VENDORS_JSON_FILE_ID": box_secrets.get("BOX_VENDORS_JSON_FILE_ID"),
}

for label, outcome in validate_box_resources(ids_to_check):
    if outcome["ok"]:
        print(f"OK {label}: {outcome['meta']}")
    else:
        print(f"ERR {label}: {outcome['error']}")