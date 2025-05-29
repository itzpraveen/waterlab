import os
import sys
import subprocess
import shutil
import random
import string

# --- Configuration ---
VENV_DIR = "venv"
REQUIREMENTS_FILE = "requirements_dev.txt" # Changed to dev requirements
ENV_EXAMPLE_FILE = ".env.example"
ENV_FILE = ".env"
MANAGE_PY = "manage.py"
DB_SQLITE_DEFAULT = "db.sqlite3" # Default name if using SQLite

# --- Helper Functions ---
def print_color(text, color_code):
    """Prints text in a given color."""
    print(f"\033[{color_code}m{text}\033[0m")

def print_success(text):
    print_color(f"✅ {text}", "92") # Green

def print_warning(text):
    print_color(f"⚠️ {text}", "93") # Yellow

def print_info(text):
    print_color(f"ℹ️ {text}", "94") # Blue

def print_error(text):
    print_color(f"❌ {text}", "91") # Red

def run_command(command, **kwargs):
    """Runs a shell command and returns True on success, False on failure."""
    print_info(f"Running: {' '.join(command)}")
    try:
        process = subprocess.Popen(command, **kwargs)
        process.wait() # Wait for the command to complete
        if process.returncode == 0:
            print_success(f"Command successful: {' '.join(command)}")
            return True
        else:
            print_error(f"Command failed with exit code {process.returncode}: {' '.join(command)}")
            return False
    except FileNotFoundError:
        print_error(f"Error: Command not found. Make sure '{command[0]}' is installed and in your PATH.")
        return False
    except Exception as e:
        print_error(f"An error occurred while running command: {' '.join(command)}\n{e}")
        return False

def check_django_importable():
    """Checks if Django can be imported."""
    try:
        import django
        print_success(f"Django version {django.get_version()} is installed.")
        return True
    except ImportError:
        return False

def generate_secret_key(length=50):
    """Generates a random secret key."""
    chars = string.ascii_letters + string.digits + string.punctuation.replace("'", "").replace('"', "").replace("\\", "")
    return "".join(random.choice(chars) for _ in range(length))

# --- Main Setup Steps ---
def check_virtual_environment():
    print_info("Step 1: Checking virtual environment...")
    if not os.path.exists(VENV_DIR):
        print_warning(f"Virtual environment directory '{VENV_DIR}' not found.")
        print_info(f"Please create and activate a virtual environment first.")
        print_info(f"Example: python3 -m venv {VENV_DIR} && source {VENV_DIR}/bin/activate (or .\\{VENV_DIR}\\Scripts\\activate on Windows)")
        return False

    virtual_env_path = os.environ.get("VIRTUAL_ENV")
    if not virtual_env_path or VENV_DIR not in virtual_env_path:
        print_warning("Virtual environment does not seem to be activated.")
        print_info(f"Please activate it: source {VENV_DIR}/bin/activate (or .\\{VENV_DIR}\\Scripts\\activate on Windows)")
        return False
    print_success("Virtual environment is active.")
    return True

def check_dependencies():
    print_info("Step 2: Checking dependencies...")
    if not os.path.exists(REQUIREMENTS_FILE):
        print_error(f"'{REQUIREMENTS_FILE}' not found. Cannot check dependencies.")
        return False

    if not check_django_importable():
        print_warning("Django is not importable. Dependencies might not be installed.")
        install_q = input(f"Do you want to install dependencies from '{REQUIREMENTS_FILE}' now? (y/n): ").lower()
        if install_q == 'y':
            if not run_command([sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS_FILE]):
                print_error("Failed to install dependencies.")
                return False
            if not check_django_importable(): # Re-check after install
                print_error("Django still not importable after installation attempt.")
                return False
        else:
            print_info("Skipping dependency installation.")
            return False
    print_success("Dependencies seem to be installed.")
    return True

def setup_env_file():
    print_info("Step 3: Setting up .env file...")
    if os.path.exists(ENV_FILE):
        print_success(f"'{ENV_FILE}' already exists.")
        # Optionally, check for key variables
        with open(ENV_FILE, 'r') as f:
            content = f.read()
            if 'SECRET_KEY' not in content or 'your-very-secret-key-here' in content:
                print_warning("SECRET_KEY in .env might be missing or default. Please ensure it's set to a unique, strong value.")
            if 'DEBUG=True' not in content:
                print_warning("DEBUG is not set to True in .env. For local development, DEBUG=True is recommended.")
        return True

    if not os.path.exists(ENV_EXAMPLE_FILE):
        print_error(f"'{ENV_EXAMPLE_FILE}' not found. Cannot create '{ENV_FILE}'.")
        print_info("Please create an .env file manually with necessary settings (SECRET_KEY, DEBUG=True, DATABASE_URL).")
        return False

    print_info(f"'{ENV_FILE}' not found. Creating from '{ENV_EXAMPLE_FILE}'.")
    shutil.copy(ENV_EXAMPLE_FILE, ENV_FILE)

    # Modify for local development
    new_content = []
    secret_key_found = False
    debug_found = False
    default_secret_key = generate_secret_key()

    with open(ENV_FILE, "r") as f:
        for line in f:
            if line.startswith("SECRET_KEY="):
                new_content.append(f"SECRET_KEY='{default_secret_key}' # Auto-generated for local dev\n")
                secret_key_found = True
            elif line.startswith("DEBUG="):
                new_content.append("DEBUG=True\n") # Removed trailing comment
                new_content.append("# DEBUG=True is set for local development\n") # Comment on a new line
                debug_found = True
            elif line.startswith("DJANGO_SETTINGS_MODULE="):
                 new_content.append("DJANGO_SETTINGS_MODULE=waterlab.settings # Default to local settings\n")
            elif line.startswith("DATABASE_URL="): # Ensure example is commented out or set to sqlite
                if "postgres" in line and line.strip().startswith("#"): # if postgres is commented, keep it
                    new_content.append(line)
                elif "postgres" in line: # if postgres is active, comment it and add sqlite
                    new_content.append(f"# {line.strip()} # Commented out for local dev, using SQLite by default\n")
                    new_content.append(f"DATABASE_URL=sqlite:///{DB_SQLITE_DEFAULT}\n")
                else: # if it's already sqlite or something else, keep it
                    new_content.append(line)
            else:
                new_content.append(line)

    if not secret_key_found:
        new_content.insert(0, f"SECRET_KEY='{default_secret_key}' # Auto-generated for local dev\n")
    if not debug_found:
        new_content.insert(1, "DEBUG=True # Set for local development\n")
    if not any("DATABASE_URL=" in line for line in new_content):
        new_content.append(f"DATABASE_URL=sqlite:///{DB_SQLITE_DEFAULT} # Default SQLite for local dev\n")


    with open(ENV_FILE, "w") as f:
        f.writelines(new_content)

    print_success(f"'{ENV_FILE}' created and configured for local development.")
    print_warning(f"A default SECRET_KEY has been generated in '{ENV_FILE}'. For production, ensure this is a strong, unique key.")
    print_info(f"Default database is SQLite ('{DB_SQLITE_DEFAULT}').")
    return True

def run_migrations():
    print_info("Step 4: Running database migrations...")
    if not run_command([sys.executable, MANAGE_PY, "migrate"]):
        print_error("Failed to run migrations.")
        return False
    print_success("Database migrations applied.")
    return True

def create_initial_data():
    print_info("Step 5: Creating initial data (admin, test parameters)...")
    # Configure Django settings to allow model imports
    # This is a bit of a hack for a script outside manage.py context
    # but necessary to check database state before running commands.
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'waterlab.settings')
        import django
        django.setup()
        from django.contrib.auth import get_user_model
        User = get_user_model()
        from core.models import TestParameter # Assuming TestParameter is in core.models
    except Exception as e:
        print_error(f"Could not set up Django to check database: {e}")
        print_info("Will attempt to run data creation commands anyway.")
        User = None # To skip checks if Django setup fails
        TestParameter = None

    admin_exists = False
    if User and User.objects.filter(is_superuser=True).exists():
        admin_exists = True
        print_success("Admin user already exists.")

    if not admin_exists:
        print_info("No admin user found. Creating one...")
        if not run_command([sys.executable, MANAGE_PY, "create_admin"]):
            print_warning("Failed to create admin user using 'create_admin'.")
            print_info("You might need to create one manually using 'python manage.py createsuperuser'.")
            # Don't return False, as user might create it manually
        else:
            print_success("Admin user creation process initiated.")
    
    parameters_exist = False
    if TestParameter and TestParameter.objects.exists():
        parameters_exist = True
        print_success("Test parameters already exist.")

    if not parameters_exist:
        print_info("No test parameters found. Creating them...")
        if not run_command([sys.executable, MANAGE_PY, "create_test_parameters"]):
            print_warning("Failed to create test parameters. The application might not function correctly without them.")
        else:
            print_success("Test parameters created.")

    create_dummies_q = input("Do you want to create dummy users for testing (e.g., lab_technician, customer)? (y/n): ").lower()
    if create_dummies_q == 'y':
        if not run_command([sys.executable, MANAGE_PY, "create_dummy_users"]): # Removed --count argument
            print_warning("Failed to create dummy users.")
        else:
            print_success("Dummy users created.")
    return True

def start_development_server():
    print_info("Step 6: Starting development server...")
    print_success("Access the application at http://127.0.0.1:8000 (or the port shown below).")
    print_info("Press CTRL+C to stop the server.")
    if not run_command([sys.executable, MANAGE_PY, "runserver"]):
        print_error("Failed to start development server.")
        return False
    return True

# --- Main Execution ---
if __name__ == "__main__":
    print_color("🚀 WaterLab LIMS Development Setup Script 🚀", "95") # Magenta

    if not os.path.exists(MANAGE_PY):
        print_error(f"'{MANAGE_PY}' not found. Please run this script from the root of your Django project.")
        sys.exit(1)

    if not check_virtual_environment():
        sys.exit(1)

    if not check_dependencies():
        sys.exit(1)

    if not setup_env_file():
        sys.exit(1)

    if not run_migrations():
        # Allow proceeding if migrations failed but user wants to try anyway or fix manually
        if input("Migrations failed. Do you want to attempt to continue anyway? (y/n): ").lower() != 'y':
            sys.exit(1)


    if not create_initial_data():
        # Allow proceeding if data creation failed
        if input("Initial data creation had issues. Do you want to attempt to continue anyway? (y/n): ").lower() != 'y':
            sys.exit(1)

    print_success("\n🎉 Setup seems complete! 🎉")
    start_development_server()
