# Junie Project Style Guidelines

## Python Code Style
- Use type hints for all function parameters and return values
- Maximum line length: 79 characters (per .flake8) or 100 characters (per pre-commit)
- Follow PEP 8 style guidelines with exceptions noted in .flake8
- Use docstrings for all classes and methods with Args/Returns sections
- Use async/await for asynchronous operations
- Use specific exception types and comprehensive error handling

## Markdown Formatting
- Use GitHub Flavored Markdown (GFM)
- Task lists: `- [ ]` for open, `- [x]` when done
- Code blocks: triple backticks with language identifier (```python)
- Keep lines <= 80 characters
- Use H1 (`#`) only for top-level headings
- Include file path in doc headings (e.g., `docs/tasks.md`)

## Commit Messages
- Use the format: `<scope>(<module>): <short summary>`
- Example: `pipeline(acquisition): filter revisions by range`
- Avoid direct commits to main/master branches (enforced by pre-commit)

## Documentation
- Maintain comprehensive README.md with sections for different aspects
- Document all classes and methods with detailed docstrings
- Update CHANGELOG.md for all notable changes using Added/Changed/Fixed sections
- Organize specialized documentation in the docs/ directory
- Track tasks in .junie/tasks.md using checkbox format

## Project Structure
- Place scripts in scripts/ directory with subdirectories for specific functionality
- Store raw data in data_raw/ and processed data in data_cleaned/ or data_real/
- Use pipeline architecture with stages for acquisition, validation, transformation, loading
- Create modular, reusable components

## Testing and Quality
- Write unit and integration tests using pytest
- Use pre-commit hooks for code quality checks
- Run flake8 for linting with configuration in .flake8
- Use isort for import sorting with black profile

## Logging
- Use `logger.info()` for successes, `logger.warning()` for recoverable issues, `logger.error()` for failures
- Include context information in log messages
- Use structured logging where appropriate

## Security
- Store sensitive information in environment variables, never in code
- Use .env file for local development only (never commit)
- Follow least privilege principle for API tokens and AWS credentials
- Use pre-commit hooks to prevent committing secrets
