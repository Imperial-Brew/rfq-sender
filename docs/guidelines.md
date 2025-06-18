# Project Style Guidelines

This project follows the style guidelines outlined below. These guidelines are designed to ensure consistency, readability, and maintainability of the codebase.

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
- Include performance and load tests for critical components
- Test with realistic data volumes to identify bottlenecks

## Logging
- Use `logger.info()` for successes, `logger.warning()` for recoverable issues, `logger.error()` for failures
- Include context information in log messages
- Use structured logging where appropriate
- Configure log rotation to prevent log files from growing too large
- Consider using a centralized logging service for production environments

## Security
- Store sensitive information in environment variables, never in code
- Use .env file for local development only (never commit)
- Follow least privilege principle for API tokens and AWS credentials
- Use pre-commit hooks to prevent committing secrets
- Implement proper input validation to prevent injection attacks
- Regularly update dependencies to address security vulnerabilities

## Scalability and Performance
- Design for horizontal scaling where possible
- Use connection pooling for database and external services
- Implement caching for frequently accessed data
- Consider using a more robust database for production (PostgreSQL, MySQL)
- Implement batch processing for large operations
- Use asynchronous processing for I/O-bound operations
- Monitor performance metrics in production

## Deployment and Operations
- Use containerization (Docker) for consistent environments
- Implement CI/CD pipelines for automated testing and deployment
- Use infrastructure as code for reproducible deployments
- Implement health checks and monitoring
- Have a rollback strategy for failed deployments
- Document operational procedures for common tasks
