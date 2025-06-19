"""
Tests for the RFQ Sender system.

This module contains tests for the core functionality of the RFQ Sender system.
"""

import os
import sys
import tempfile
import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add parent directory to path to import rfq_sender
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))
import rfq_sender


def test_validate_email():
    """Test email validation function."""
    # Valid emails
    assert rfq_sender.validate_email("test@example.com") is True
    assert rfq_sender.validate_email("user.name+tag@example.co.uk") is True
    assert rfq_sender.validate_email("user-name@example.org") is True

    # Invalid emails
    assert rfq_sender.validate_email("test@") is False
    assert rfq_sender.validate_email("@example.com") is False
    assert rfq_sender.validate_email("test@example") is False
    assert rfq_sender.validate_email("test.example.com") is False


def test_check_attachments():
    """Test attachment checking function."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test files
        valid_file1 = os.path.join(temp_dir, "valid1.txt")
        valid_file2 = os.path.join(temp_dir, "valid2.txt")
        with open(valid_file1, "w") as f:
            f.write("Test file 1")
        with open(valid_file2, "w") as f:
            f.write("Test file 2")

        # Non-existent file
        invalid_file = os.path.join(temp_dir, "invalid.txt")

        # Test with all valid files
        all_valid, valid_attachments, invalid_attachments = rfq_sender.check_attachments(
            [valid_file1, valid_file2]
        )
        assert all_valid is True
        assert len(valid_attachments) == 2
        assert len(invalid_attachments) == 0

        # Test with mixed valid and invalid files
        all_valid, valid_attachments, invalid_attachments = rfq_sender.check_attachments(
            [valid_file1, invalid_file]
        )
        assert all_valid is False
        assert len(valid_attachments) == 1
        assert len(invalid_attachments) == 1
        assert valid_attachments[0] == valid_file1
        assert invalid_attachments[0] == invalid_file


def test_get_attachments() -> None:
    """
    Test file attachment retrieval function.

    This test verifies that the get_attachments function correctly identifies
    files that match the part number and process using different patterns.

    Returns:
        None
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test files
        part_no = "0250-20000"
        process = "cleaning"

        # Files that should match different patterns
        # Pattern 1: Exact match with part number and process
        exact_match_file = os.path.join(temp_dir, f"{part_no}_{process}.pdf")

        # Pattern 2: Match with part number and normalized process
        # Test with spaces and hyphens that should be normalized
        normalized_process = "clean ing-process"
        normalized_match_file = os.path.join(
            temp_dir, 
            f"{part_no}_{normalized_process}.pdf"
        )

        # Pattern 3: Match with just the part number
        part_only_match_file = os.path.join(temp_dir, f"{part_no}_drawing.pdf")

        # Files that should not match
        non_matching_file = os.path.join(temp_dir, "other_part.pdf")

        # Create all the test files
        test_files = [
            exact_match_file, 
            normalized_match_file, 
            part_only_match_file, 
            non_matching_file
        ]
        for file_path in test_files:
            with open(file_path, "w") as f:
                f.write("Test file")

        # Test attachment retrieval
        with patch("rfq_sender.logger"):  # Mock logger to avoid logging during tests
            attachments = rfq_sender.get_attachments(part_no, process, temp_dir)

            # Check that all expected files are included
            # Note: The function may return duplicates due to multiple pattern matches
            assert exact_match_file in attachments
            assert normalized_match_file in attachments
            assert part_only_match_file in attachments
            assert non_matching_file not in attachments


def test_render_template():
    """Test template rendering function."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a test template
        template_dir = os.path.join(temp_dir, "templates")
        os.makedirs(template_dir)

        test_template = os.path.join(template_dir, "test.j2")
        with open(test_template, "w") as f:
            f.write("Hello, {{ name }}!")

        # Mock the jinja2 environment
        mock_env = MagicMock()
        mock_template = MagicMock()
        mock_template.render.return_value = "Hello, World!"
        mock_env.get_template.return_value = mock_template

        with patch("jinja2.Environment", return_value=mock_env):
            with patch("os.path.dirname", return_value=temp_dir):
                # Test template rendering
                result = rfq_sender.render_template("test.j2", {"name": "World"})

                # Check that the template was rendered correctly
                assert result == "Hello, World!"
                mock_env.get_template.assert_called_once_with("test.j2")
                mock_template.render.assert_called_once_with(name="World")


def test_cli_argument_parsing():
    """Test command-line argument parsing."""
    # Test with required arguments
    with patch("sys.argv", [
        "rfq_sender.py",
        "--part_no", "0250-20000",
        "--process", "cleaning",
        "--file_location", "path/to/files",
        "--quantities", "1,2,5,10"
    ]):
        args = rfq_sender.parse_args()

        # Check required arguments
        assert args.part_no == "0250-20000"
        assert args.process == "cleaning"
        assert args.file_location == "path/to/files"
        assert args.quantities == "1,2,5,10"

        # Check default values for optional arguments
        assert args.spec is None
        assert args.dry_run is False

    # Test with optional arguments
    with patch("sys.argv", [
        "rfq_sender.py",
        "--part_no", "0250-20000",
        "--process", "cleaning",
        "--file_location", "path/to/files",
        "--quantities", "1,2,5,10",
        "--spec", "Special instructions",
        "--dry-run"
    ]):
        args = rfq_sender.parse_args()

        # Check optional arguments
        assert args.spec == "Special instructions"
        assert args.dry_run is True

    # Test with subcommand
    with patch("sys.argv", [
        "rfq_sender.py",
        "--part_no", "0250-20000",  # Required arguments must be provided
        "--process", "cleaning",
        "--file_location", "path/to/files",
        "--quantities", "1,2,5,10",
        "show-log",  # Subcommand
        "--limit", "5"
    ]):
        args = rfq_sender.parse_args()

        # Check subcommand and its arguments
        assert args.command == "show-log"
        assert args.limit == 5


def test_validate_args():
    """Test argument validation function."""
    # Create a temporary directory for testing file_location validation
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test with valid arguments
        valid_args = argparse.Namespace(
            part_no="0250-20000",
            process="cleaning",
            file_location=temp_dir,
            quantities="1,2,5,10"
        )
        is_valid, error_message = rfq_sender.validate_args(valid_args)
        assert is_valid is True
        assert error_message is None

        # Test with empty part_no
        invalid_args = argparse.Namespace(
            part_no="",
            process="cleaning",
            file_location=temp_dir,
            quantities="1,2,5,10"
        )
        is_valid, error_message = rfq_sender.validate_args(invalid_args)
        assert is_valid is False
        assert "Part number cannot be empty" in error_message

        # Test with whitespace part_no
        invalid_args = argparse.Namespace(
            part_no="   ",
            process="cleaning",
            file_location=temp_dir,
            quantities="1,2,5,10"
        )
        is_valid, error_message = rfq_sender.validate_args(invalid_args)
        assert is_valid is False
        assert "Part number cannot be empty" in error_message

        # Test with empty process
        invalid_args = argparse.Namespace(
            part_no="0250-20000",
            process="",
            file_location=temp_dir,
            quantities="1,2,5,10"
        )
        is_valid, error_message = rfq_sender.validate_args(invalid_args)
        assert is_valid is False
        assert "Process cannot be empty" in error_message

        # Test with whitespace process
        invalid_args = argparse.Namespace(
            part_no="0250-20000",
            process="   ",
            file_location=temp_dir,
            quantities="1,2,5,10"
        )
        is_valid, error_message = rfq_sender.validate_args(invalid_args)
        assert is_valid is False
        assert "Process cannot be empty" in error_message

        # Test with non-existent file_location
        invalid_args = argparse.Namespace(
            part_no="0250-20000",
            process="cleaning",
            file_location=os.path.join(temp_dir, "non_existent"),
            quantities="1,2,5,10"
        )
        is_valid, error_message = rfq_sender.validate_args(invalid_args)
        assert is_valid is False
        assert "does not exist" in error_message

        # Test with empty quantities
        invalid_args = argparse.Namespace(
            part_no="0250-20000",
            process="cleaning",
            file_location=temp_dir,
            quantities=""
        )
        is_valid, error_message = rfq_sender.validate_args(invalid_args)
        assert is_valid is False
        assert "Quantities must be comma-separated integers" in error_message

        # Test with non-integer quantities
        invalid_args = argparse.Namespace(
            part_no="0250-20000",
            process="cleaning",
            file_location=temp_dir,
            quantities="1,2,abc,10"
        )
        is_valid, error_message = rfq_sender.validate_args(invalid_args)
        assert is_valid is False
        assert "Quantities must be comma-separated integers" in error_message

        # Test with negative quantities
        invalid_args = argparse.Namespace(
            part_no="0250-20000",
            process="cleaning",
            file_location=temp_dir,
            quantities="1,2,-5,10"
        )
        is_valid, error_message = rfq_sender.validate_args(invalid_args)
        assert is_valid is False
        assert "Quantities must be positive integers" in error_message

        # Test with zero quantities
        invalid_args = argparse.Namespace(
            part_no="0250-20000",
            process="cleaning",
            file_location=temp_dir,
            quantities="1,0,5,10"
        )
        is_valid, error_message = rfq_sender.validate_args(invalid_args)
        assert is_valid is False
        assert "Quantities must be positive integers" in error_message


if __name__ == "__main__":
    pytest.main()
