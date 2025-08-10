import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from scripts.email import sender


def test_validate_email():
    assert sender.validate_email("test@example.com") is True
    assert sender.validate_email("invalid") is False


def test_check_attachments():
    with tempfile.TemporaryDirectory() as temp_dir:
        valid = os.path.join(temp_dir, "valid.txt")
        with open(valid, "w", encoding="utf-8") as f:
            f.write("data")
        missing = os.path.join(temp_dir, "missing.txt")

        all_valid, valid_list, invalid_list = sender.check_attachments([valid, missing])
        assert all_valid is False
        assert valid_list == [valid]
        assert invalid_list == [missing]


def test_send_email_dry_run():
    with tempfile.TemporaryDirectory() as temp_dir:
        attachment = os.path.join(temp_dir, "file.txt")
        with open(attachment, "w", encoding="utf-8") as f:
            f.write("hello")

        config = {
            "email": {
                "smtp": {
                    "from_name": "Tester",
                    "from_email": "from@example.com",
                    "server": "smtp.example.com",
                    "port": 587,
                    "use_tls": True,
                    "username": "user",
                    "password": "pass",
                },
                "settings": {"cc_emails": ""},
            }
        }

        assert sender.send_email(
            "to@example.com",
            "Subject",
            "Body",
            [attachment],
            config,
            dry_run=True,
        ) is True

