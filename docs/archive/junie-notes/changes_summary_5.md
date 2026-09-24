# Project Structure and Documentation Update Summary

## Changes Made

### Folder Structure Changes
1. Created `data_raw/` directory for storing raw data files
2. Created `data_cleaned/` directory for storing processed data files
3. Removed the original `data/` directory after moving files
4. Organized scripts into functional subdirectories:
   - `scripts/email/` for email-related scripts
   - `scripts/box/` for Box integration scripts
   - `scripts/vendor/` for vendor-related scripts
   - `scripts/utils/` for utility scripts

### Documentation Updates
1. Created `.junie/tasks.md` file for tracking project tasks using checkbox format
2. Updated `README.md` to reflect the new project structure
3. Updated `CHANGELOG.md` to document the folder structure changes

## Verification

The project structure now follows the guidelines:
- Scripts are organized in the `scripts/` directory with subdirectories for specific functionality
- Raw data is stored in `data_raw/` and processed data in `data_cleaned/`
- Documentation is organized in the `docs/` directory
- Tasks are tracked in `.junie/tasks.md` using checkbox format

All documentation follows the markdown formatting rules:
- GitHub Flavored Markdown (GFM) is used
- Task lists use `- [ ]` for open tasks and `- [x]` for completed tasks
- Code blocks use triple backticks with language identifiers
- Lines are kept under 80 characters
- H1 (`#`) is used only for top-level headings

## Next Steps

The project structure and documentation are now up to date with the guidelines. Future work should maintain this structure:
- New scripts should be placed in the appropriate subdirectory based on functionality
- Raw data should be stored in `data_raw/` and processed data in `data_cleaned/`
- New tasks should be added to `.junie/tasks.md` using the checkbox format
- Documentation should follow the markdown formatting rules