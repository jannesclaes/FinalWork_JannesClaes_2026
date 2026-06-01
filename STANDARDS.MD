# Coding Standards

To ensure consistency and maintainability throughout the project, please adhere to the following coding standards.

## 1. General Principles

    6 *   **Consistency is Key:** If you see existing code following a pattern, stick to it.
    7 *   **Readable Code:** Code should be self-explanatory. Use comments only to explain why complex logic exists, not what it does.
    8 *   **English Only:** All variable names, comments, and documentation must be in English.
    9

## 2. File Naming

_ **Python Files:** Use `snake_case` for Python scripts and modules (e.g., `app.py`, `data_processor.py`).
_ **Generic Files:** Use `kebab-case` or standard uppercase for generic configuration and documentation files (e.g., `docker-compose.yml`, `README.md`).

## 3. Python Standards

Because this project relies heavily on Python, we follow the standard conventions:
_ **PEP 8:** Follow standard [PEP 8](https://peps.python.org/pep-0008/) style guidelines.
_ **Indentation:** 4 spaces per indentation level.
_ **Variables & Functions:** Use `snake_case` (e.g., `get_driver_data`, `is_active`).
_ **Classes:** Use `PascalCase` (e.g., `RaceDataAnalyzer`).
_ **Constants:** Use `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`).
_ **Type Hinting:** Use type hints where possible to improve readability and tooling support.

## 4. Git & Commits

We follow the [Conventional Commits](https://www.conventionalcommits.org/) style for clear history:

_ `feat:` ... for a new feature.
_ `fix:` ... for a bug fix.
_ `docs:` ... for documentation changes.
_ `style:` ... for formatting changes (missing semi-colons, etc).

- `refactor:` ... for code changes that neither fix a bug nor add a feature.

\*Example:\* `feat: add driver lap time comparison`
