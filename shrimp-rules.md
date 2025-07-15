# Development Guidelines

## Project Overview

This project is a Flask-based web application for tracking and analyzing personal golf round data. It allows users to upload their scores from text files, view past rounds, and see detailed statistics for each round.

- **Technology Stack**:
  - **Backend**: Python, Flask
  - **Database**: MySQL
  - **Frontend**: HTML, Jinja2 templates
  - **Testing**: pytest

## Project Architecture

- **`conf/`**: Contains configuration files. `lalagolf.conf` holds database credentials and web app user info.
- **`data/`**: Stores raw golf round data as `.txt` files, organized by year.
- **`scripts/`**: Contains database schema definitions (`schema.sql`).
- **`src/`**: The main source code directory.
  - **`data_parser.py`**: Logic for parsing the raw `.txt` data files.
  - **`db_loader.py`**: Handles all database interactions, including saving and deleting round data.
  - **`webapp/`**: The Flask web application package.
    - **`routes.py`**: Defines all web application routes and view logic.
    - **`templates/`**: HTML templates for the web interface.
- **`tests/`**: Contains all tests for the application.
  - **`test_data_parser.py`**: Tests for the data parsing logic.

## Code Standards

### Naming Conventions

- **Python**: Use `snake_case` for variables and functions. Use `PascalCase` for classes.
- **Files**: Use `snake_case` for file names.
- **Database Tables**: Use plural nouns in `snake_case` (e.g., `rounds`, `holes`, `shots`).

### Formatting

- Adhere to PEP 8 for all Python code.
- Use 4 spaces for indentation.
- Maximum line length is 120 characters.

### Comments

- Use comments to explain *why* something is done, not *what* is being done.
- Add docstrings to all public modules, functions, classes, and methods.

## Functionality Implementation Standards

### Adding a New Web Page

1.  **Define the route**: Add a new route function in `src/webapp/routes.py`.
2.  **Create the template**: Add a new HTML file in `src/webapp/templates/`.
3.  **Add database logic (if needed)**: Add functions to `src/db_loader.py` to fetch or save data.
4.  **Call database logic from route**: Use the new functions from `db_loader.py` in your route function in `routes.py`.
5.  **Render the template**: Pass the data to the new template using `render_template`.

### Modifying the Data Parser

- When changing `src/data_parser.py`, you **must** update the corresponding tests in `tests/test_data_parser.py`.
- Ensure that any changes are backward-compatible with existing data files in the `data/` directory. If not, a migration plan is needed.

## Framework/Plugin/Third-party Library Usage Standards

- **Flask**: Use standard Flask patterns. Use Blueprints if the application grows more complex.
- **mysql-connector-python**: Use the connection pooling provided by the library for any new database interactions to manage connections efficiently. All database interaction should be in `src/db_loader.py`.
- **pytest**: All new functionality must be accompanied by tests.

## Workflow Standards

1.  **Create a new branch**: For any new feature or bug fix.
2.  **Implement changes**: Follow the standards outlined in this document.
3.  **Write/update tests**: Ensure all new code is tested and existing tests pass.
4.  **Run tests**: Execute `pytest` from the root directory.
5.  **Submit a pull request**: For review.

## Key File Interaction Standards

- **`data_parser.py` and `db_loader.py`**: `data_parser.py` is responsible for reading and parsing text files. The parsed data structure is then passed to `db_loader.py` to be persisted in the database. Any change in the data structure returned by `parse_file` will likely require changes in `save_round_data`.
- **`routes.py` and `templates/`**: `routes.py` contains the view logic that renders the HTML templates. Data is passed from Python to the templates.
- **`load_data.py`**: This script uses `data_parser.py` and `db_loader.py` to bulk-load data from the `data/` directory.

## AI Decision-making Standards

- **Ambiguous Requests**: If a request is ambiguous (e.g., "improve the website"), first analyze the existing code to identify areas for improvement. Propose a specific plan (e.g., "Refactor the `round_detail` page to improve performance by optimizing database queries") before making any changes.
- **Error Handling**: When encountering an error, first try to understand the root cause by examining the code and logs. Do not blindly try solutions. If the error is in a third-party library, consult its documentation.

## Prohibited Actions

- **Do not** commit directly to the `main` branch.
- **Do not** add new dependencies to `requirements.txt` without prior approval.
- **Do not** store any secrets or credentials directly in the code. Use the `conf/lalagolf.conf` file.
- **Do not** write database access logic directly in `src/webapp/routes.py`. All database logic must be in `src/db_loader.py`.
