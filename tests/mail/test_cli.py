import argparse
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from scripts.mail import cli


def test_cli_argument_parsing(monkeypatch):
    test_args = [
        "prog",
        "--part_no",
        "0250-20000",
        "--process",
        "cleaning",
        "--file_location",
        "/tmp",
        "--quantities",
        "1,2,5,10",
        "show-log",
        "--limit",
        "5",
    ]
    monkeypatch.setattr(sys, "argv", test_args)
    args = cli.parse_args()
    assert args.part_no == "0250-20000"
    assert args.process == "cleaning"
    assert args.file_location == "/tmp"
    assert args.quantities == "1,2,5,10"
    assert args.command == "show-log"
    assert args.limit == 5


def test_validate_args():
    with tempfile.TemporaryDirectory() as temp_dir:
        valid_args = argparse.Namespace(
            part_no="0250-20000",
            process="cleaning",
            file_location=temp_dir,
            quantities="1,2,5,10",
        )
        is_valid, error_message = cli.validate_args(valid_args)
        assert is_valid is True
        assert error_message is None

        invalid_args = argparse.Namespace(
            part_no="",
            process="cleaning",
            file_location=temp_dir,
            quantities="1,2,5,10",
        )
        is_valid, error_message = cli.validate_args(invalid_args)
        assert is_valid is False
        assert "Part number cannot be empty" in error_message

        invalid_args = argparse.Namespace(
            part_no="0250-20000",
            process="",
            file_location=temp_dir,
            quantities="1,2,5,10",
        )
        is_valid, error_message = cli.validate_args(invalid_args)
        assert is_valid is False
        assert "Process cannot be empty" in error_message

        invalid_args = argparse.Namespace(
            part_no="0250-20000",
            process="cleaning",
            file_location=os.path.join(temp_dir, "missing"),
            quantities="1,2,5,10",
        )
        is_valid, error_message = cli.validate_args(invalid_args)
        assert is_valid is False
        assert "does not exist" in error_message

        invalid_args = argparse.Namespace(
            part_no="0250-20000",
            process="cleaning",
            file_location=temp_dir,
            quantities="1,2,abc,10",
        )
        is_valid, error_message = cli.validate_args(invalid_args)
        assert is_valid is False
        assert "comma-separated integers" in error_message

        invalid_args = argparse.Namespace(
            part_no="0250-20000",
            process="cleaning",
            file_location=temp_dir,
            quantities="1,0,5,10",
        )
        is_valid, error_message = cli.validate_args(invalid_args)
        assert is_valid is False
        assert "positive integers" in error_message

