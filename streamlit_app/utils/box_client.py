from __future__ import annotations
import json
from typing import Any
import streamlit as st
from boxsdk import JWTAuth, Client
from boxsdk.exception import BoxAPIException


def get_box_client() -> Client:
    """Build a Box Client from `st.secrets`.

    Returns:
        Client: Authenticated Box client using JWT.

    Raises:
        KeyError: If required secrets are missing.
        ValueError: If the JWT JSON is malformed.
    """
    jwt_json = st.secrets["box"]["BOX_JWT_JSON"]
    data: dict[str, Any] = json.loads(jwt_json)
    auth = JWTAuth(
        client_id=data["boxAppSettings"]["clientID"],
        client_secret=data["boxAppSettings"]["clientSecret"],
        enterprise_id=data.get("enterpriseID"),
        jwt_key_id=data["boxAppSettings"]["appAuth"]["publicKeyID"],
        rsa_private_key_data=data["boxAppSettings"]["appAuth"]["privateKey"],
        rsa_private_key_passphrase=data["boxAppSettings"]["appAuth"][
            "passphrase"
        ].encode("utf-8"),
    )
    return Client(auth)