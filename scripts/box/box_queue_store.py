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
        # Ensure we don't persist legacy columns even on initial save
        merged = df.copy()
        try:
            # Drop known-legacy columns
            drop_cols = [
                "rfq #", "RFQ #",
                "box_rfq_root_id",
                "box_access",
                "file_manifest",
                "box_quote_folder_id",
                "quote_id",
            ]
            merged = merged.drop(columns=drop_cols, errors="ignore")
        except Exception:
            pass
        merged.to_csv(bio, index=False)
        bio.seek(0)
        try:
            f.update_contents_with_stream(bio, etag=etag)  # If-Match is used under the hood
        except BoxAPIException as e:
            if e.status == 412:  # Precondition Failed — etag mismatch
                if self.logger:
                    self.logger.info("ETag mismatch; reloading and retrying merge")
                # simple retry: reload, merge, prune legacy cols, align schema, and retry
                latest = self.load_df()
                merged = self._merge(latest, df)
                try:
                    drop_cols = [
                        "rfq #", "RFQ #",
                        "box_rfq_root_id",
                        "box_access",
                        "file_manifest",
                        "box_quote_folder_id",
                        "quote_id",
                    ]
                    merged = merged.drop(columns=drop_cols, errors="ignore")
                except Exception:
                    pass
                # Prefer our current schema column order first, then any additional cols at the end
                try:
                    preferred = [c for c in df.columns if c in merged.columns]
                    rest = [c for c in merged.columns if c not in preferred]
                    merged = merged.loc[:, preferred + rest]
                except Exception:
                    pass
                bio2 = BytesIO()
                merged.to_csv(bio2, index=False)
                bio2.seek(0)
                f, etag2 = self._ensure_file()
                f.update_contents_with_stream(bio2, etag=etag2)
            else:
                raise

    def _merge(self, latest: pd.DataFrame, ours: pd.DataFrame) -> pd.DataFrame:
        """Merge strategy on ETag conflict.

        Strategy: OUR version wins for existing rows (we just wrote those updates),
        but rows that exist ONLY in the Box-latest version are preserved (concurrent
        additions from another session).

        Step-by-step:
        1. Rows in `ours` — keep as-is (includes our updates to sent, box_share_link, etc.)
        2. Rows in `latest` that don’t exist in `ours` — append (concurrent additions)
        3. Result preserves our updates AND concurrent new rows.
        """
        key_cols = [c for c in ["part_number", "process", "spec"] if c in latest.columns and c in ours.columns]
        if not key_cols:
            return ours  # no common key — just trust ours

        # Build a frozenset key for each row in ours
        ours_keys = set(
            tuple(str(v) for v in row)
            for row in ours[key_cols].itertuples(index=False)
        )
        # Rows in latest that are NOT already in ours (true concurrent additions)
        latest_only = latest[
            ~latest[key_cols].apply(
                lambda r: tuple(str(v) for v in r), axis=1
            ).isin(ours_keys)
        ]

        # Align columns: add any columns in latest_only that ours lacks, and vice versa
        for col in latest_only.columns:
            if col not in ours.columns:
                ours = ours.copy()
                ours[col] = ""
        for col in ours.columns:
            if col not in latest_only.columns:
                latest_only = latest_only.copy()
                latest_only[col] = ""

        # Our rows first (preserves our update order), then concurrent additions
        merged = pd.concat([ours, latest_only[ours.columns]], ignore_index=True)
        return merged