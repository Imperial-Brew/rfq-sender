import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from scripts.email import config as email_config


def test_load_config():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    config_dir = os.path.join(project_root, "config")
    cfg = email_config.load_config(config_dir)
    assert "email" in cfg
    assert "vendors" in cfg

