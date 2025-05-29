# WaterLab LIMS - Local Development Setup Guide

This guide provides comprehensive instructions for setting up the WaterLab LIMS project for local development and testing.

## 1. System Requirements and Prerequisites

Before you begin, ensure your system meets the following requirements:

*   **Python**: Version 3.8 or higher. You can download it from [python.org](https://www.python.org/).
*   **Pip**: Python package installer (usually comes with Python).
*   **Git**: Version control system. Download from [git-scm.com](https://git-scm.com/).
*   **Virtual Environment Tool**: `venv` (recommended, built-in with Python 3) or `virtualenv`.
*   **Web Browser**: A modern web browser like Chrome, Firefox, Safari, or Edge.
*   **Code Editor/IDE**: A code editor of your choice, such as VS Code, PyCharm, or Sublime Text.

## 2. Step-by-Step Local Development Setup

Follow these steps to get the project running on your local machine:

### 2.1. Clone the Repository

Open your terminal or command prompt and clone the `waterlab` repository:

```bash
git clone https://github.com/itzpraveen/waterlab.git
cd waterlab
```

### 2.2. Create and Activate a Virtual Environment

It's highly recommended to use a virtual environment to manage project dependencies.

**Using `venv` (Python 3 built-in):**

```bash
# Create a virtual environment (e.g., named 'venv')
python3 -m venv venv

# Activate the virtual environment
# On macOS and Linux:
source venv/bin/activate
# On Windows:
.\venv\Scripts\activate
```

Your terminal prompt should now indicate that you are in the virtual environment (e.g., `(venv) ...`).

### 2.3. Install Dependencies

Install the required Python packages using `pip` and the `requirements.txt` file:

```bash
pip install -r requirements.txt
```
This file contains all development and production dependencies. For a production-like setup, you might consider `requirements_production.txt` after the initial setup.

## 3. Database Setup and Configuration

The project is configured to use SQLite by default for ease of development.

### 3.1. SQLite (Default)

No special setup is required for SQLite. Django will automatically create a `db.sqlite3` file in the project root directory when you run migrations.

### 3.2. PostgreSQL (Optional)

If you prefer to use PostgreSQL:

1.  **Install PostgreSQL**: Download and install PostgreSQL from [postgresql.org](https://www.postgresql.org/).
2.  **Create a Database**:
    *   Open `psql` or a GUI tool like pgAdmin.
    *   Create a new database (e.g., `waterlab_dev`).
    *   Create a database user with a password and grant it privileges to the `waterlab_dev` database.
3.  **Install Psycopg2**:
    ```bash
    pip install psycopg2-binary
    ```
4.  **Configure Environment Variables**: Update your `.env` file (see section 4) with your PostgreSQL connection details:
    ```env
    DATABASE_URL=postgres://YOUR_DB_USER:YOUR_DB_PASSWORD@YOUR_DB_HOST:YOUR_DB_PORT/YOUR_DB_NAME
    # Example:
    # DATABASE_URL=postgres://waterlab_user:securepassword@localhost:5432/waterlab_dev
    ```
5.  **Update Django Settings (if necessary)**: The `waterlab/settings.py` file uses `dj_database_url` to parse `DATABASE_URL`. Ensure this is correctly configured if you deviate from the standard setup.

### 3.3. Apply Database Migrations

Once your database is configured (SQLite or PostgreSQL), apply the database migrations to create the necessary tables:

```bash
python manage.py migrate
```

## 4. Environment Variables Configuration

The project uses a `.env` file to manage environment-specific settings.

1.  **Create a `.env` file**: In the root directory of the project, create a new file named `.env`. You can copy the example file:
    ```bash
    cp .env.example .env
    ```
2.  **Populate `.env`**: Open the `.env` file and fill in the required variables. At a minimum, you'll need:

    ```env
    SECRET_KEY='your_strong_secret_key_here'  # Replace with a strong random string
    DEBUG=True
    ALLOWED_HOSTS=127.0.0.1,localhost

    # Database URL (defaults to SQLite if not set, or if set to sqlite:///...)
    # For SQLite (default, if you want to be explicit or name the file):
    DATABASE_URL=sqlite:///db.sqlite3
    # For PostgreSQL (example, uncomment and modify if using PostgreSQL):
    # DATABASE_URL=postgres://user:password@host:port/dbname

    # Email settings (optional, for password reset, etc.)
    # EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend # For development
    # EMAIL_HOST=
    # EMAIL_PORT=
    # EMAIL_USE_TLS=
    # EMAIL_HOST_USER=
    # EMAIL_HOST_PASSWORD=
    ```

    *   **`SECRET_KEY`**: Generate a strong secret key. You can use an online generator or Django's `get_random_secret_key()` utility.
    *   **`DEBUG`**: Set to `True` for development.
    *   **`DATABASE_URL`**: If you're using SQLite and named your database file something other than `db.sqlite3` in `settings.py`, or if you're using PostgreSQL, set this accordingly.

## 5. Running the Development Server

Once the setup is complete, you can run the Django development server:

```bash
python manage.py runserver
```

By default, the server will run at `http://127.0.0.1:8000/`. Open this URL in your web browser to see the application.

## 6. Creating Sample Data for Testing

The project includes custom management commands to populate the database with sample data, which is useful for testing.

### 6.1. Create an Administrator Account

First, create a superuser (administrator) account to access the Django admin interface and certain application features:

```bash
python manage.py create_admin
```
Follow the prompts to set the username, email, and password for the admin user. This command also ensures the admin role is correctly assigned.

Alternatively, you can use Django's built-in command:
```bash
python manage.py createsuperuser
```
And then, if needed, ensure the admin user has the 'ADMIN' role in the application by running:
```bash
python manage.py fix_admin_role --username YOUR_ADMIN_USERNAME
```

### 6.2. Create Dummy Users (Optional)

To test different user roles and interactions:

```bash
python manage.py create_dummy_users --count 10
```
This will create 10 dummy users with various roles (Lab Technician, Consultant, Front Desk, Customer).

### 6.3. Create Test Parameters (Important for Functionality)

The application requires test parameters to be set up for sample registration and result entry.

```bash
python manage.py create_test_parameters
```
This command will populate the `TestParameter` model with a predefined set of common water quality test parameters.

### 6.4. Load Initial Data from JSON (Alternative)

The repository contains a `waterlab_data.json` fixture. You can load this data using:
```bash
python manage.py loaddata waterlab_data.json
```
This might create users, customers, samples, and other data. Review the fixture content to understand what it includes. It's generally recommended to use the custom commands for a cleaner setup, but this can be an alternative for specific scenarios.

## 7. Troubleshooting Common Issues

*   **`ModuleNotFoundError`**: Ensure your virtual environment is activated and you've installed all packages from `requirements.txt`.
*   **Database Connection Errors (PostgreSQL)**:
    *   Verify `DATABASE_URL` in your `.env` file is correct.
    *   Ensure your PostgreSQL server is running.
    *   Check that the database user has the correct permissions.
    *   Make sure `psycopg2-binary` is installed.
*   **Static Files Not Loading / Styles Missing**:
    *   Ensure `DEBUG=True` in your `.env` file.
    *   Run `python manage.py collectstatic` if you've made changes to static files and `DEBUG=False` (though for development, `DEBUG=True` usually handles this).
    *   Clear your browser cache.
*   **Permission Denied for `db.sqlite3`**: Ensure you have write permissions in the project directory.
*   **Port Already in Use**: If port 8000 is in use, you can run the server on a different port:
    ```bash
    python manage.py runserver 8001
    ```
*   **Secret Key Missing**: Ensure `SECRET_KEY` is set in your `.env` file.

## 8. Testing the Improved UI/UX Features

After setting up the project and populating it with some sample data:

1.  **Navigate the Application**:
    *   Visit the Dashboard, Customer List, Sample List, Test Result Entry pages, etc.
    *   Check the overall layout, typography, colors, and spacing.
2.  **Test Responsiveness**:
    *   Open your browser's developer tools (usually F12 or right-click -> Inspect).
    *   Use the device toolbar to simulate different screen sizes (e.g., mobile, tablet).
    *   Verify that:
        *   Navigation adapts (sidenav on mobile).
        *   Tables transform into card views on smaller screens (e.g., Sample List).
        *   Content reflows correctly without horizontal scrolling.
        *   Buttons and interactive elements are easily tappable.
3.  **Check UI Components**:
    *   Test buttons, forms, cards, modals, dropdowns, and alerts.
    *   Ensure they follow the new Material Design 3-inspired styling.
4.  **Form Interactions**:
    *   Test form validation messages and styling.
    *   Verify input field focus states.
5.  **JavaScript Enhancements**:
    *   Test table search and filtering functionalities.
    *   Observe page transitions and loading indicators.
    *   Check if Materialize components (modals, tooltips, selects) are working as expected with the new `main.js`.
6.  **Accessibility**:
    *   Try navigating using the keyboard (Tab, Shift+Tab, Enter).
    *   Check if "Skip to main content" link works.
7.  **Dark Mode (If Browser Supports `prefers-color-scheme`)**:
    *   Switch your OS/browser to dark mode to see how the UI adapts (if the dark mode CSS is enabled and functioning).

## 9. Development Workflow Recommendations

*   **Branching**: Use Git branches for new features or bug fixes (e.g., `feature/new-dashboard-widget`, `fix/login-bug`).
*   **Commit Frequently**: Make small, logical commits with clear messages.
*   **Linters and Formatters**: Consider using tools like Flake8 (Python) and Prettier (CSS/JS) to maintain code quality and consistency.
*   **Run Migrations**: After pulling changes that include model updates, always run `python manage.py migrate`.
*   **Keep Dependencies Updated**: Periodically review and update packages in `requirements.txt`.
*   **Test Thoroughly**: Before pushing changes, test on different browsers and screen sizes.
*   **Consult `README.md` and `DEPLOYMENT.md`**: These files may contain additional project-specific information.

---

Happy Coding! If you encounter any issues not covered here, please refer to the Django and Materialize CSS documentation or seek help from the project maintainers.
