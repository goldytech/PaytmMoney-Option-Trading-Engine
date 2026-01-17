# AGENTS.md - Developer Guidelines for paytm-money-ws

This file contains guidelines for coding agents working on the paytm-money-ws codebase. It includes build/lint/test commands and code style guidelines to maintain consistency across the project.

## Project Overview

This is a Python WebSocket client for Paytm Money's live market data streaming service, built with:
- Python 3.14+
- Pydantic for data modeling
- websockets library for WebSocket connections
- uv for package management
- Microsoft Aspire for hosting/deployment

## Build/Lint/Test Commands

### Package Management
```bash
# Install dependencies (from py-app directory)
uv sync

# Add new dependency
uv add <package_name>

# Add dev dependency
uv add --dev <package_name>

# Update dependencies
uv lock --upgrade
```

### Linting and Code Quality
```bash
# Run Ruff (recommended linter/formatter)
ruff check .
ruff format .

# Alternative: Run mypy for type checking
mypy .

# Alternative: Run flake8 for style checking
flake8 .

# Run all quality checks together
ruff check . && ruff format --check . && mypy .
```

### Testing
```bash
# Run all tests (when tests are added)
pytest

# Run tests with coverage
pytest --cov=.

# Run a specific test file
pytest tests/test_filename.py

# Run a specific test function
pytest tests/test_filename.py::TestClass::test_function

# Run tests in verbose mode
pytest -v
```

### Building and Running
```bash
# Run the application locally (from py-app directory)
python main.py

# Run via Aspire (from root directory)
dotnet run --project apphost.cs

# Build for production (if needed)
# No specific build step required for this Python app
```

### Development Workflow
```bash
# Activate virtual environment (if not using uv shell)
source py-app/.venv/Scripts/activate  # Windows
source py-app/.venv/bin/activate     # Unix

# Format code before committing
ruff format .

# Check code quality before committing
ruff check .
```

## Code Style Guidelines

### General Principles
- Write clean, readable, and maintainable code
- Use descriptive variable and function names
- Follow the principle of single responsibility
- Prefer explicit over implicit behavior
- Add docstrings to all public functions, classes, and modules
- Use type hints consistently

### Python Version and Imports
- Target Python 3.14+
- Organize imports in this order with blank lines between groups:
  1. Standard library imports
  2. Third-party imports
  3. Local imports

```python
import asyncio
import json
import logging
from typing import Dict, List, Optional

import websockets
from pydantic import BaseModel

from models import MarketData
```

### Naming Conventions
- **Variables/Functions**: snake_case
- **Classes**: PascalCase
- **Constants**: UPPER_SNAKE_CASE
- **Modules**: snake_case
- **Type Variables**: PascalCase (T, Generic[T])

### Type Hints
- Use type hints for all function parameters and return values
- Use `Optional[T]` for nullable types instead of `T | None`
- Use `Union[T1, T2]` for multiple possible types
- Define custom types for complex type aliases

```python
from typing import Dict, List, Optional, Union

def process_data(data: Dict[str, Union[int, str]]) -> Optional[List[str]]:
    # Implementation
    pass
```

### Docstrings
Use Google-style docstrings:

```python
def connect_websocket(self, url: str) -> None:
    """Connect to the WebSocket server.

    Args:
        url: The WebSocket URL to connect to.

    Raises:
        ConnectionError: If the connection fails.
    """
    pass
```

### Error Handling
- Catch specific exceptions rather than bare `Exception`
- Use custom exceptions for business logic errors
- Log errors with appropriate levels and structured data
- Include relevant context in error messages

```python
try:
    # Risky operation
    pass
except websockets.exceptions.ConnectionClosedError as e:
    logger.error("WebSocket connection closed", extra={
        "error": str(e),
        "error_type": type(e).__name__
    })
    raise
except Exception as e:
    logger.error("Unexpected error", extra={
        "error": str(e),
        "error_type": type(e).__name__
    })
    raise
```

### Logging
- Use structured logging with extra fields for context
- Log at appropriate levels: DEBUG, INFO, WARNING, ERROR
- Include relevant business context in log messages
- Use logger names that match module structure

```python
logger = logging.getLogger(__name__)

logger.info("Processing market data", extra={
    "security_id": data.security_id,
    "packet_type": data.packet_type,
    "last_price": getattr(data, 'last_price', None)
})
```

### Async/Await Patterns
- Use async/await for I/O operations
- Prefer asyncio over threading for concurrency
- Use appropriate async context managers
- Handle cancellation properly

```python
async def connect(self):
    try:
        async with websockets.connect(self.url) as websocket:
            await self._handle_messages(websocket)
    except asyncio.CancelledError:
        logger.info("Connection cancelled")
        raise
```

### Data Models (Pydantic)
- Use Pydantic BaseModel for all data structures
- Define field types explicitly
- Use field validators for data validation
- Include default values where appropriate

```python
from pydantic import BaseModel, Field

class MarketDepth(BaseModel):
    buy_quantity: int
    sell_quantity: int
    buy_price: float = Field(gt=0)  # Validation
    sell_price: float = Field(gt=0)
```

### Constants and Configuration
- Define constants at module level
- Use environment variables for sensitive configuration
- Group related constants in classes or dataclasses

```python
class WebSocketConfig:
    BASE_URL = "wss://developer-ws.paytmmoney.com/broadcast/user/v1/data"
    RECONNECT_DELAY = 5.0
    MAX_RETRIES = 3
```

### File Structure
- Keep modules focused and single-purpose
- Use relative imports within the package
- Place tests in a `tests/` directory mirroring the package structure

### Security Best Practices
- Never log sensitive information (tokens, passwords, etc.)
- Validate all input data
- Use secure WebSocket connections (wss://)
- Handle authentication tokens securely

### Performance Considerations
- Use asyncio for concurrent I/O operations
- Avoid blocking operations in async functions
- Use efficient data structures (lists vs deques where appropriate)
- Profile code before optimizing

### Testing Guidelines
- Write unit tests for all business logic
- Use pytest for testing framework
- Mock external dependencies (WebSocket connections, etc.)
- Test both success and failure scenarios
- Aim for high test coverage (>80%)

```python
# Example test structure
def test_parse_ltp_packet():
    # Test LTP packet parsing
    pass

def test_websocket_connection_failure():
    # Test connection error handling
    pass
```

### Git Commit Messages
- Use clear, descriptive commit messages
- Start with a verb (Add, Fix, Update, Refactor, etc.)
- Keep first line under 50 characters
- Add body for complex changes

```
Add WebSocket reconnection logic

- Implement exponential backoff for failed connections
- Add maximum retry limits
- Include proper error logging
```

### Code Review Checklist
- [ ] Code follows style guidelines
- [ ] Type hints are complete and accurate
- [ ] Docstrings are present and informative
- [ ] Error handling is appropriate
- [ ] Logging is structured and informative
- [ ] Tests are included for new functionality
- [ ] No sensitive data is logged or committed
- [ ] Performance considerations are addressed</content>
<parameter name="filePath">C:\Users\Afzal\Projects\paytm-money-ws\AGENTS.md