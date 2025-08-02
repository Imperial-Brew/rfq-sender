import pandas as pd
import os
from pathlib import Path

# Get the project root directory
ROOT_DIR = Path(__file__).parent.parent
QUEUE_PATH = os.path.join(ROOT_DIR, "docs", "queue.csv")

def load_queue(path=QUEUE_PATH):
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path)

def add_to_queue(path, entry: dict):
    df = load_queue(path)
    df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
    df.to_csv(path, index=False)
