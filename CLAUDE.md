# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Django-based Laboratory Information Management System (LIMS) for water testing laboratories. Implements a complete workflow from customer registration through sample testing to report generation with role-based access control.

## Development Commands

```bash
# Database management
./switch_database.sh development    # Switch to SQLite for development
./switch_database.sh production     # Switch to PostgreSQL for production  
./switch_database.sh reset         # Reset database with dummy data

# Django commands
python manage.py runserver          # Start development server
python manage.py migrate            # Apply database migrations
python manage.py create_dummy_users # Create test users for all roles
python manage.py create_test_parameters # Setup standard water test parameters
python manage.py create_admin       # Create admin user interactively
python manage.py collectstatic      # Collect static files for production

# Docker deployment
docker-compose up --build          # Build and run with Docker
./build.sh                         # Production build script
```

## Architecture Overview

### Core Models & Relationships
- **User**: Extended with roles (admin, lab, frontdesk, consultant) and employee_id
- **Customer**: Kerala-specific address fields (district, taluk, panchayat)
- **Sample**: UUID tracking with status workflow (RECEIVED → SENT_TO_LAB → TESTING_IN_PROGRESS → RESULTS_ENTERED → REVIEW_PENDING → APPROVED → SENT)
- **TestParameter**: Configurable tests with limits and units
- **TestResult**: Individual test outcomes with validation
- **ConsultantReview**: Approval/rejection workflow for test results
- **AuditTrail**: Comprehensive change tracking with JSON storage

### Authentication System
Multi-portal design:
- `/admin-login/` - Admin access
- `/user-login/` - Regular user access  
- `/` - Login selector page

Role-based dashboards automatically redirect users to appropriate interfaces.

### Business Logic Patterns
- Status transitions managed in model methods
- Role validation through custom decorators: `@admin_required`, `@lab_required`, `@frontdesk_required`, `@consultant_required`
- Audit trail automatically captures all model changes
- Test result validation against parameter limits

### URL Structure
```
/dashboard/                    # Role-specific dashboards
/customers/                    # Customer CRUD operations
/samples/                      # Sample CRUD operations  
/samples/{id}/test-results/    # Test result entry interface
/samples/{id}/review/          # Consultant review workflow
/audit/                        # Audit trail (admin only)
/setup/test-parameters/        # Test parameter configuration
```

## Database Configuration

Environment-controlled database switching via `USE_POSTGRESQL` variable:
- Development: SQLite (default)
- Production: PostgreSQL with connection pooling

Migration scripts handle both database types automatically.

## Development Workflow

1. Use `switch_database.sh development` for local development
2. Run `create_dummy_users` and `create_test_parameters` for test data
3. Test with different user roles (admin/lab/frontdesk/consultant accounts created by dummy data script)
4. Use audit trail interface to verify business logic changes
5. Switch to PostgreSQL mode before deployment testing

## Testing Strategy

Test with role-based scenarios:
- **Front Desk**: Customer registration, sample intake, status updates
- **Lab Technician**: Test result entry, sample processing updates  
- **Consultant**: Result review, approval/rejection decisions
- **Admin**: User management, system configuration, audit review

## Key Business Rules

- Sample collection dates cannot be future dates
- Test results validate against parameter min/max limits  
- Status transitions follow strict workflow progression
- Only consultants can approve/reject test results
- All changes tracked in audit trail with user attribution

## Production Deployment

Supports multiple deployment methods:
- **Render.com**: Configured via `render.yaml`
- **Docker**: Multi-stage build with health checks via `Dockerfile`
- **Manual**: Use `build.sh` script with `requirements_production.txt`

Database automatically switches to PostgreSQL in production environments.