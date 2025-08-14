import os
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from scripts.mail import rfq_sender


def test_get_attachments():
    with tempfile.TemporaryDirectory() as temp_dir:
        part_no = "0250-20000"
        process = "cleaning"

        exact = os.path.join(temp_dir, f"{part_no}_{process}.pdf")
        normalized = os.path.join(temp_dir, f"{part_no}_clean-ing.pdf")
        part_only = os.path.join(temp_dir, f"{part_no}_drawing.pdf")
        other = os.path.join(temp_dir, "other.pdf")

        for path in [exact, normalized, part_only, other]:
            with open(path, "w", encoding="utf-8") as f:
                f.write("x")

        with patch.object(rfq_sender, "logger"):
            attachments = rfq_sender.get_attachments(part_no, process, temp_dir)

        assert exact in attachments
        assert normalized in attachments
        assert part_only in attachments
        assert other not in attachments


def test_render_template():
    context = {
        "vendor": {"first_name": "Alice"},
        "sample_table": None,
        "attachments": [],
    }
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    with patch("scripts.mail.rfq_sender.os.path.dirname", return_value=project_root):
        rendered = rfq_sender.render_template("cover_letter.j2", context)
    assert "Hello Alice" in rendered

