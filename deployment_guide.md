# Water Lab LIMS - Professional Deployment Guide

## 🏭 Production Setup with PostgreSQL

### 1. PostgreSQL Installation & Setup

#### Ubuntu/Debian:
```bash
# Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib python3-psycopg2

# Start PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Setup database
sudo -u postgres psql -f setup_postgresql.sql
```

#### CentOS/RHEL:
```bash
# Install PostgreSQL
sudo yum install postgresql-server postgresql-contrib python3-psycopg2
sudo postgresql-setup initdb

# Start PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Setup database
sudo -u postgres psql -f setup_postgresql.sql
```

### 2. Environment Variables Setup

Create a `.env` file for production:
```bash
# Database Configuration
DB_NAME=waterlab
DB_USER=waterlab
DB_PASSWORD=Well_567!
DB_HOST=localhost
DB_PORT=5432

# Django Configuration
SECRET_KEY=your-super-secret-key-here
DEBUG=False

# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

### 3. Migration to PostgreSQL

```bash
# Switch to PostgreSQL settings
export DJANGO_SETTINGS_MODULE=waterlab.settings_production

# Install required packages
pip install psycopg2-binary python-decouple whitenoise

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Create dummy users
python manage.py create_dummy_users

# Create test parameters
python manage.py create_test_parameters

# Collect static files
python manage.py collectstatic --noinput
```

### 4. Production Server Setup

#### Using Gunicorn + Nginx:

1. **Install Gunicorn:**
```bash
pip install gunicorn
```

2. **Create systemd service file:**
```bash
sudo nano /etc/systemd/system/waterlab.service
```

```ini
[Unit]
Description=Water Lab LIMS
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/waterlab
Environment="DJANGO_SETTINGS_MODULE=waterlab.settings_production"
ExecStart=/path/to/venv/bin/gunicorn --workers 3 --bind unix:/path/to/waterlab.sock waterlab.wsgi:application

[Install]
WantedBy=multi-user.target
```

3. **Nginx Configuration:**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        root /path/to/waterlab;
    }
    
    location /media/ {
        root /path/to/waterlab;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/path/to/waterlab.sock;
    }
}
```

### 5. Security Hardening

#### Database Security:
```sql
-- Restrict user permissions
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO waterlab;

-- Enable SSL connections
ALTER SYSTEM SET ssl = on;
SELECT pg_reload_conf();
```

#### Application Security:
```python
# In settings_production.py
ALLOWED_HOSTS = ['your-domain.com', 'www.your-domain.com']
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

### 6. Backup Strategy

#### Automated PostgreSQL Backups:
```bash
#!/bin/bash
# backup_waterlab.sh
BACKUP_DIR="/var/backups/waterlab"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="waterlab"

mkdir -p $BACKUP_DIR

# Database backup
pg_dump -U waterlab -h localhost $DB_NAME | gzip > $BACKUP_DIR/waterlab_$DATE.sql.gz

# Media files backup
tar -czf $BACKUP_DIR/media_$DATE.tar.gz /path/to/waterlab/media/

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

# Log backup completion
echo "$(date): Backup completed - waterlab_$DATE" >> /var/log/waterlab_backup.log
```

Add to crontab:
```bash
# Daily backup at 2 AM
0 2 * * * /path/to/backup_waterlab.sh
```

### 7. Monitoring & Maintenance

#### System Monitoring:
```bash
# Database connections
SELECT count(*) FROM pg_stat_activity WHERE datname = 'waterlab';

# Table sizes
SELECT schemaname,tablename,pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size 
FROM pg_tables WHERE schemaname = 'public';

# Performance monitoring
SELECT query, calls, total_time, mean_time FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;
```

#### Application Monitoring:
```python
# Add to settings_production.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/waterlab/app.log',
            'maxBytes': 1024*1024*10,  # 10MB
            'backupCount': 5,
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

### 8. Performance Optimization

#### PostgreSQL Tuning:
```sql
-- postgresql.conf optimizations
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.7
wal_buffers = 16MB
default_statistics_target = 100
```

#### Django Optimizations:
```python
# Database connection pooling
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'CONN_MAX_AGE': 600,
        'OPTIONS': {
            'MAX_CONNS': 20,
            'connect_timeout': 20,
        }
    }
}

# Cache configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
        'LOCATION': '127.0.0.1:11211',
    }
}
```

## 🎯 Professional Benefits

### Why PostgreSQL for LIMS:

1. **Concurrent Access:** Multiple users can work simultaneously
2. **Data Integrity:** ACID compliance ensures data consistency
3. **Advanced Queries:** Complex reporting and analytics
4. **JSON Support:** Flexible data storage for test results
5. **Full-Text Search:** Advanced search capabilities
6. **Scalability:** Handles growing data volumes
7. **Backup & Recovery:** Enterprise-grade data protection
8. **Security:** User roles, SSL, and audit trails

### Professional Features Enabled:

- **Multi-laboratory Support:** Scale to multiple locations
- **Audit Trails:** Track all data changes
- **Advanced Reporting:** Complex queries and analytics
- **Integration APIs:** Connect with instruments and other systems
- **Data Export:** Various formats for regulatory compliance
- **Performance Monitoring:** Real-time system metrics

## 🚀 Quick Production Migration

To migrate your current setup to PostgreSQL:

```bash
# 1. Setup PostgreSQL database
sudo -u postgres psql -f setup_postgresql.sql

# 2. Switch settings
cp waterlab/settings.py waterlab/settings_dev.py
cp waterlab/settings_production.py waterlab/settings.py

# 3. Run migrations
python manage.py migrate

# 4. Create users and data
python manage.py create_dummy_users
python manage.py create_test_parameters

# 5. Test the system
python manage.py runserver
```

Your LIMS is now ready for professional deployment! 🏆