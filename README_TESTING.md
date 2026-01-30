# Testing Guide

This project uses `pytest` for automated testing.

## Prerequisites

Ensure you have the testing dependencies installed. They are listed in `requirements.txt` but you might need to install them if you haven't already:

```bash
pip install pytest pytest-asyncio httpx coverage
```

## Running Tests

To run all tests:

```bash
pytest
```

To run with coverage report:

```bash
pytest --cov=. --cov-report=term-missing
```

## Test Structure

- `tests/conftest.py`: Global fixtures (database setup, test client, authentication helpers).
- `tests/test_models.py`: Unit tests for database models and relationships.
- `tests/test_auth.py`: Integration tests for authentication flows (Register, Login).
- `tests/test_api_devices.py`: Tests for Device Catalog API (Search, Get).
- `tests/test_api_tracking.py`: Tests for User Tracking API.
- `tests/test_reports.py`: Tests for Report generation.

## Database

Tests use a temporary SQLite database (`test.db`) which is created and destroyed automatically. This ensures tests are isolated from your local development database.
