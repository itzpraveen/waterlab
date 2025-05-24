#!/bin/bash
# Database Switching Script for Water Lab LIMS

show_help() {
    echo "🧪 Water Lab LIMS Database Switcher"
    echo ""
    echo "Usage: ./switch_database.sh [development|production|reset]"
    echo ""
    echo "Commands:"
    echo "  development  - Switch to SQLite (for testing & development)"
    echo "  production   - Switch to PostgreSQL (for production deployment)"
    echo "  reset        - Reset development database with dummy data"
    echo "  help         - Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./switch_database.sh development"
    echo "  ./switch_database.sh production"
    echo "  ./switch_database.sh reset"
}

setup_development() {
    echo "🗃️  Switching to SQLite (Development Mode)"
    cp .env.development .env
    echo "✅ Environment set to development"
    echo "📝 Using SQLite database for fast development"
    echo ""
    echo "Next steps:"
    echo "  python manage.py runserver"
}

setup_production() {
    echo "🐘 Switching to PostgreSQL (Production Mode)"
    
    # Check if PostgreSQL is available
    if ! command -v psql &> /dev/null; then
        echo "❌ PostgreSQL not found. Please install PostgreSQL first:"
        echo "   Ubuntu/Debian: sudo apt install postgresql postgresql-contrib"
        echo "   CentOS/RHEL: sudo yum install postgresql-server postgresql-contrib"
        exit 1
    fi
    
    cp .env.production .env
    echo "✅ Environment set to production"
    echo "🔧 Using PostgreSQL database for professional deployment"
    echo ""
    echo "Next steps:"
    echo "1. Setup PostgreSQL database:"
    echo "   sudo -u postgres psql -f setup_postgresql.sql"
    echo "2. Run migrations:"
    echo "   python manage.py migrate"
    echo "3. Create superuser:"
    echo "   python manage.py createsuperuser"
    echo "4. Load data:"
    echo "   python manage.py create_dummy_users"
    echo "   python manage.py create_test_parameters"
}

reset_development() {
    echo "🔄 Resetting Development Database"
    
    # Ensure we're in development mode
    cp .env.development .env
    
    # Remove existing database
    if [ -f "db.sqlite3" ]; then
        rm db.sqlite3
        echo "🗑️  Removed existing SQLite database"
    fi
    
    # Run migrations
    echo "📋 Running migrations..."
    python manage.py migrate
    
    # Create dummy users
    echo "👥 Creating dummy users..."
    python manage.py create_dummy_users
    
    # Create test parameters
    echo "🧪 Creating test parameters..."
    python manage.py create_test_parameters
    
    # Collect static files
    echo "📁 Collecting static files..."
    python manage.py collectstatic --noinput
    
    echo ""
    echo "✅ Development database reset complete!"
    echo "🔑 Login with: admin/admin123, frontdesk/front123, labtech/lab123, consultant/consult123"
    echo "🚀 Start server: python manage.py runserver"
}

# Main script logic
case "$1" in
    "development"|"dev")
        setup_development
        ;;
    "production"|"prod")
        setup_production
        ;;
    "reset")
        reset_development
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    "")
        echo "❓ No command specified. Use 'help' for usage information."
        show_help
        ;;
    *)
        echo "❌ Unknown command: $1"
        show_help
        exit 1
        ;;
esac