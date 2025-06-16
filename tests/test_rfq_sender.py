"""
Tests for the RFQ Sender system.

This module contains tests for the core functionality of the RFQ Sender system.
"""

import os
import sys
import tempfile
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


def test_get_attachments():
    """Test file attachment retrieval function."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test files
        part_no = "0250-20000"
        process = "cleaning"
        
        # Files that should match
        matching_file1 = os.path.join(temp_dir, f"{part_no}_{process}.pdf")
        matching_file2 = os.path.join(temp_dir, f"{part_no}_drawing.pdf")
        
        # Files that should not match
        non_matching_file = os.path.join(temp_dir, "other_part.pdf")
        
        # Create the files
        for file_path in [matching_file1, matching_file2, non_matching_file]:
            with open(file_path, "w") as f:
                f.write("Test file")
        
        # Test attachment retrieval
        with patch("rfq_sender.logger"):  # Mock logger to avoid logging during tests
            attachments = rfq_sender.get_attachments(part_no, process, temp_dir)
            
            # Should find the two matching files
            assert len(attachments) == 2
            assert matching_file1 in attachments
            assert matching_file2 in attachments
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


if __name__ == "__main__":
    pytest.main()