# WaterLab LIMS - Quick Start Guide

This guide helps you get the WaterLab LIMS application running locally as quickly as possible. Choose either the Automated Setup (recommended for speed) or the Manual Setup.

## Prerequisites

Before you start, ensure you have:

1.  **Python** (version 3.8 or higher) installed.
2.  **Git** installed.
3.  The ability to create and activate a Python virtual environment.

## Method 1: Automated Setup (Fastest)

This method uses the `start_dev.py` script to automate most of the setup steps.

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/itzpraveen/waterlab.git
    cd waterlab
    ```

2.  **Create and Activate Virtual Environment:**
    ```bash
    # On macOS and Linux:
    python3 -m venv venv
    source venv/bin/activate

    # On Windows:
    python -m venv venv
    .\venv\Scripts\activate
    ```
    *(Your prompt should now show `(venv)`)*

3.  **Run the Development Setup Script:**
    ```bash
    python start_dev.py
    ```
    The script will guide you through:
    *   Checking and installing dependencies (from `requirements.txt`).
    *   Setting up the `.env` file (from `.env.example`, configured for local SQLite development).
    *   Running database migrations.
    *   Creating an admin user and essential test parameters.
    *   Starting the development server.

4.  **Access the Application:**
    Once the script starts the server, open your browser and go to `http://127.0.0.1:8000`.

## Method 2: Manual Setup (Condensed)

Follow these steps for a manual setup:

1.  **Clone the Repository & Navigate into it:**
    ```bash
    git clone https://github.com/itzpraveen/waterlab.git
    cd waterlab
    ```

2.  **Create and Activate Virtual Environment:**
    ```bash
    # macOS/Linux
    python3 -m venv venv
    source venv/bin/activate

    # Windows
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    For a minimal development setup:
    ```bash
    pip install -r requirements_dev.txt
    ```
    Or, for all dependencies (including production ones):
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    *   Copy `.env.development` (if available) or `.env.example` to a new file named `.env` in the project root.
        ```bash
        # If .env.development exists:
        cp .env.development .env
        # Or, if using .env.example:
        # cp .env.example .env
        ```
    *   **Edit `.env`** and ensure the following are set for local development:
        *   `SECRET_KEY='your_unique_strong_secret_key'` (Replace with a real secret key)
        *   `DEBUG=True`
        *   `DATABASE_URL=sqlite:///db.sqlite3` (This uses SQLite, which is simplest for local dev)
        *   `DJANGO_SETTINGS_MODULE=waterlab.settings` (Ensures development settings are used)

5.  **Apply Database Migrations:**
    ```bash
    python manage.py migrate
    ```

6.  **Create an Administrator Account:**
    ```bash
    python manage.py create_admin
    ```
    Follow the prompts. Alternatively, use `python manage.py createsuperuser` and then optionally `python manage.py fix_admin_role --username YOUR_ADMIN_USERNAME`.

7.  **Create Essential Test Parameters:**
    The application needs test parameters to function correctly.
    ```bash
    python manage.py create_test_parameters
    ```

8.  **Run the Development Server:**
    ```bash
    python manage.py runserver
    ```

9.  **Access the Application:**
    Open your browser and go to `http://127.0.0.1:8000`.

## Next Steps

Once the application is running:

*   **Log in** with the admin credentials you created.
*   **Navigate** through the dashboard, customer management, sample registration, and results entry pages to see the new UI/UX in action.
*   **Test on different screen sizes** using your browser's developer tools to verify mobile responsiveness.
*   **Create dummy users** (optional, for more thorough testing): `python manage.py create_dummy_users --count 5`

For more detailed setup instructions, troubleshooting, or information on using other databases like PostgreSQL, refer to the `DEVELOPMENT_SETUP.md` guide.
