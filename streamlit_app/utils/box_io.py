from __future__ import annotations
from io import BytesIO
from typing import Any
import json
import pandas as pd
from boxsdk import Client
from boxsdk.exception import BoxAPIException


def download_bytes(client: Client, file_id: str) -> bytes:
    """Download raw bytes from a Box file ID with error context."""
    try:
        return client.file(file_id).content()
    except BoxAPIException as e:
        raise RuntimeError(
            f"Box download failed for file_id={file_id}: {e}"  # noqa: EM101
        ) from e


def upload_bytes_overwrite(client: Client, file_id: str, data: bytes) -> None:
    """Overwrite an existing Box file with `data`.

    Args:
        client: Box client.
        file_id: Target Box file id.
        data: Bytes to upload as the new file version.
    """
    try:
        buf = BytesIO(data)
        client.file(file_id).update_contents_with_stream(buf)
    except BoxAPIException as e:
        raise RuntimeError(
            f"Box upload failed for file_id={file_id}: {e}"  # noqa: EM101
        ) from e


def read_csv(client: Client, file_id: str, **read_csv_opts: Any) -> pd.DataFrame:
    content = download_bytes(client, file_id)
    return pd.read_csv(BytesIO(content), **read_csv_opts)


def write_csv(client: Client, file_id: str, df: pd.DataFrame) -> None:
    buf = BytesIO()
    df.to_csv(buf, index=False)
    upload_bytes_overwrite(client, file_id, buf.getvalue())


def read_json_obj(client: Client, file_id: str) -> Any:
    content = download_bytes(client, file_id)
    return json.loads(content.decode("utf-8"))


def read_yaml_obj(client: Client, file_id: str) -> Any:
    import yaml  # pyyaml
    content = download_bytes(client, file_id)
    return yaml.safe_load(content.decode("utf-8"))