# LIMS for Water Testing Lab (Kerala, India)

## 1. Project Overview

This project is a custom web-based Laboratory Information Management System (LIMS) for a water testing lab located in Kerala, India. The system aims to streamline the entire laboratory workflow, from customer registration and sample collection to test result entry, expert review, report generation, and administrative oversight.

The system is designed to support multiple user roles, facilitate efficient task management, ensure data integrity, and integrate AI capabilities to enhance operational efficiency and data analysis.

## 2. Technology Stack

- **Backend:** Python with Django Framework
- **Database:** PostgreSQL
- **Frontend:** (To be determined - likely React, Vue.js, or Angular, or Django templates)
- **AI Model Interaction:** Planned via API

## 3. Project Structure

The Django project is named `waterlab`. Key application logic is organized within apps.

- `core/`: This app contains the primary models and business logic for the LIMS.
  - `models.py`: Defines the database schema for core entities.
  - `admin.py`: Configures the Django admin interface for the models.
  - `views.py`, `urls.py`: Will contain view logic and URL routing.
- `waterlab/`: Contains project-level settings (`settings.py`) and URL configuration (`urls.py`).

## 4. Core Models Defined

The following Django models have been defined in `core/models.py`:

-   **`Customer`**: Stores customer information (name, contact details, address).
-   **`TestParameter`**: Defines configurable test parameters (e.g., pH, TDS), including units, methods, and permissible limits.
-   **`Sample`**: Manages sample details, including customer linkage, collection information, source, status, and requested tests (linking to `TestParameter`).
-   **`TestResult`**: Stores the results for each test parameter for a given sample, including the result value, observations, and technician details.
-   **`ConsultantReview`**: Records the expert review of test results for a sample, including comments, recommendations, and approval status.

## 5. Setup and Running the Project (General Steps)

1.  **Clone the repository.** (Assuming this will be in a repo)
2.  **Set up a Python virtual environment** and activate it.
3.  **Install dependencies:** `pip install -r requirements.txt` (A `requirements.txt` file will need to be created).
4.  **Configure the database:**
    -   Ensure PostgreSQL is running and configured.
    -   The `waterlab/settings.py` is configured to connect to a PostgreSQL database named `waterlab` with a user `waterlab` and a password (see environment configuration) on `localhost:5432`.
    -   You must ensure:
        1.  Your PostgreSQL server is running.
        2.  A database named `waterlab` exists. (e.g., `CREATE DATABASE waterlab;`)
        3.  A user named `waterlab` exists with the appropriate password. (e.g., `CREATE USER waterlab WITH PASSWORD 'your_password_here';`)
        4.  The `waterlab` user has all necessary privileges on the `waterlab` database. (e.g., `GRANT ALL PRIVILEGES ON DATABASE waterlab TO waterlab;`)
        5.  If you encounter `FATAL: password authentication failed for user "waterlab"`, double-check the user's password and ensure your PostgreSQL server's `pg_hba.conf` file is configured to allow password authentication (e.g., `md5` or `scram-sha-256`) for the `waterlab` user from `localhost`. You might need to reload PostgreSQL configuration after changing `pg_hba.conf`.
    -   If using different credentials, update the `DATABASES` setting in `waterlab/settings.py` accordingly.
5.  **Apply database migrations:**
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```
6.  **Create a superuser** to access the Django admin:
    ```bash
    python manage.py createsuperuser
    ```
7.  **Run the development server:**
    ```bash
    python manage.py runserver
    ```
    The application will typically be available at `http://127.0.0.1:8000/`. The admin interface will be at `http://127.0.0.1:8000/admin/`.

## 6. Current Status (as of this README's last update)

-   Django project structure initialized.
-   `core` app created.
-   Core models (`Customer`, `Sample`, `TestParameter`, `TestResult`, `ConsultantReview`) defined.
-   Models registered with the Django admin interface.
-   Initial database migrations created.
-   Database connection is configured for PostgreSQL; migrations should be applied.

## 7. AI Integration Requirements (Summary)

-   **Phase 1 (Core AI):**
    -   Intelligent data validation during result entry.
    -   AI-assisted preliminary draft report generation.
-   **Phase 2 (Advanced AI - Future):**
    -   Trend analysis of historical test data.
    -   Anomaly detection in test results.
    -   NLP for consultant notes analysis.

This README is intended to help AI models and developers understand the project's context, current state, and overall goals.
