# box_queue_store.py
from io import BytesIO
import pandas as pd
from boxsdk.exception import BoxAPIException

class BoxQueueStore:
    def __init__(self, box_integration, file_id: str = None, folder_id: str = None, logger=None):
        self.box = box_integration  # your existing BoxIntegration, with .client
        self.file_id = file_id
        self.folder_id = folder_id
        self.logger = logger

    def _ensure_file(self) -> tuple:
        # returns (file_obj, etag)
        if self.file_id:
            f = self.box.client.file(self.file_id).get()
            return f, f.etag
        # create if missing by name in folder
        folder = self.box.client.folder(self.folder_id).get()
        items = folder.get_items(limit=100)
        for it in items:
            if it.name == "queue.csv":
                self.file_id = it.id
                f = self.box.client.file(self.file_id).get()
                return f, f.etag
        # create new empty CSV
        bio = BytesIO(b"part_number,process,spec,quantities\n")
        new_file = self.box.client.folder(self.folder_id).upload_stream(bio, "queue.csv")
        self.file_id = new_file.id
        new_file = self.box.client.file(self.file_id).get()
        return new_file, new_file.etag

    def load_df(self) -> pd.DataFrame:
        f, _ = self._ensure_file()
        bio = BytesIO()
        f.download_to(bio)
        bio.seek(0)
        return pd.read_csv(bio)

    def save_df(self, df: pd.DataFrame) -> None:
        # Upload with ETag precondition to prevent overwriting concurrent changes
        f, etag = self._ensure_file()
        bio = BytesIO()
        df.to_csv(bio, index=False)
        bio.seek(0)
        try:
            f.update_contents_with_stream(bio, etag=etag)  # If-Match is used under the hood
        except BoxAPIException as e:
            if e.status == 412:  # Precondition Failed — etag mismatch
                if self.logger:
                    self.logger.info("ETag mismatch; reloading and retrying merge")
                # simple retry: reload, merge, and retry
                latest = self.load_df()
                merged = self._merge(latest, df)
                bio2 = BytesIO()
                merged.to_csv(bio2, index=False)
                bio2.seek(0)
                f, etag2 = self._ensure_file()
                f.update_contents_with_stream(bio2, etag=etag2)
            else:
                raise

    def _merge(self, latest: pd.DataFrame, ours: pd.DataFrame) -> pd.DataFrame:
        # Implement a domain-appropriate merge (e.g., by part_number + process)
        # For a first cut, prefer latest then append new rows from ours that aren’t in latest
        key_cols = [c for c in ["part_number", "process", "spec"] if c in latest.columns]
        if not key_cols:
            return ours  # fallback
        keys_latest = set(tuple(latest[k] for k in key_cols) for _, latest in latest[key_cols].drop_duplicates().iterrows())
        new_rows = ours[~ours[key_cols].apply(tuple, axis=1).isin(keys_latest)]
        return pd.concat([latest, new_rows], ignore_index=True)