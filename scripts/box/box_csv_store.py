from io import BytesIO
from typing import Optional, List
import pandas as pd
from boxsdk.exception import BoxAPIException


class BoxCSVStore:
    """
    Generic CSV store backed by Box.
    Can target a file by file_id, or by name within a folder (folder_id).
    If the file does not exist and a header is provided, it will create the file with that header.
    """

    def __init__(self, box_integration, *, filename: str,
                 file_id: Optional[str] = None,
                 folder_id: Optional[str] = None,
                 header: Optional[List[str]] = None,
                 logger=None):
        self.box = box_integration  # BoxIntegration with .client
        self.filename = filename
        self.file_id = file_id
        self.folder_id = folder_id
        self.header = header or []
        self.logger = logger

    def _ensure_file(self) -> tuple:
        """Ensure the target file exists in Box; create if missing.
        Returns (file_obj, etag)
        """
        if self.file_id:
            f = self.box.client.file(self.file_id).get()
            return f, f.etag

        # Must have a folder_id to search/create
        folder = self.box.client.folder(self.folder_id).get()
        items = folder.get_items(limit=1000)
        for it in items:
            if getattr(it, 'name', None) == self.filename:
                self.file_id = it.id
                f = self.box.client.file(self.file_id).get()
                return f, f.etag

        # Create new CSV using header
        line = ",".join(self.header) + "\n" if self.header else "\n"
        bio = BytesIO(line.encode('utf-8'))
        new_file = self.box.client.folder(self.folder_id).upload_stream(bio, self.filename)
        self.file_id = new_file.id
        new_file = self.box.client.file(self.file_id).get()
        return new_file, new_file.etag

    def load_df(self) -> pd.DataFrame:
        f, _ = self._ensure_file()
        bio = BytesIO()
        f.download_to(bio)
        bio.seek(0)
        try:
            return pd.read_csv(bio)
        except Exception:
            # If empty file, return empty DataFrame with header if known
            if self.header:
                return pd.DataFrame(columns=self.header)
            return pd.DataFrame()

    def save_df(self, df: pd.DataFrame) -> None:
        f, etag = self._ensure_file()
        bio = BytesIO()
        df.to_csv(bio, index=False)
        bio.seek(0)
        try:
            f.update_contents_with_stream(bio, etag=etag)
        except BoxAPIException as e:
            if e.status == 412:
                # Retry with latest
                latest = self.load_df()
                # merge: prefer concatenate; caller should dedupe based on domain logic
                try:
                    merged = pd.concat([latest, df], ignore_index=True)
                except Exception:
                    merged = df
                bio2 = BytesIO()
                merged.to_csv(bio2, index=False)
                bio2.seek(0)
                f2, etag2 = self._ensure_file()
                f2.update_contents_with_stream(bio2, etag=etag2)
            else:
                raise
