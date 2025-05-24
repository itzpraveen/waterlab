# Professional Deployment Guide - Water Lab LIMS

## Overview
This guide provides complete instructions for deploying the Water Lab LIMS system professionally using Docker containers with PostgreSQL, Redis, Django, and Nginx.

## 🚀 Quick Start (Production Deployment)

### Prerequisites
- Ubuntu 20.04+ or CentOS 8+
- Docker and Docker Compose installed
- Domain name (optional but recommended)
- SSL certificate (recommended for production)

### 1. Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Logout and login again for group changes
```

### 2. Deploy Application

```bash
# Clone your repository
git clone <your-repo-url>
cd waterlab

# Copy environment file and configure
cp .env.example .env

# Edit .env with your settings
nano .env
```

### 3. Environment Configuration

Edit `.env` file with your production values:

```bash
# Essential settings to change:
SECRET_KEY=your-generated-secret-key-here
DEBUG=False
DOMAIN_NAME=waterlab.yourdomain.com
DB_PASSWORD=your-strong-database-password
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

### 4. Generate Secret Key

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 5. Start Services

```bash
# Build and start all services
docker-compose up -d

# Check services status
docker-compose ps

# View logs
docker-compose logs -f web
```

### 6. Initialize Database

```bash
# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Load initial data (if any)
docker-compose exec web python manage.py loaddata fixtures/initial_data.json
```

### 7. Test Deployment

```bash
# Check if application is running
curl http://localhost/health/

# Access admin interface
# http://your-domain/admin/
```

## 🔧 Configuration Options

### SSL/HTTPS Setup

1. **Get SSL Certificate:**
   ```bash
   # Using Let's Encrypt
   sudo apt install certbot
   sudo certbot certonly --standalone -d waterlab.yourdomain.com
   ```

2. **Copy certificates:**
   ```bash
   sudo mkdir -p ssl
   sudo cp /etc/letsencrypt/live/waterlab.yourdomain.com/fullchain.pem ssl/
   sudo cp /etc/letsencrypt/live/waterlab.yourdomain.com/privkey.pem ssl/
   sudo chown -R $USER:$USER ssl/
   ```

3. **Update nginx.conf:**
   - Uncomment HTTPS server block
   - Update domain name
   - Set USE_SSL=true in .env

### Database Backup

```bash
# Create backup script
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/var/backups/waterlab"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Database backup
docker-compose exec -T db pg_dump -U waterlab waterlab_prod > $BACKUP_DIR/db_backup_$DATE.sql

# Media files backup
tar -czf $BACKUP_DIR/media_backup_$DATE.tar.gz media/

# Keep only last 30 days
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
EOF

chmod +x backup.sh

# Add to crontab (daily backup at 2 AM)
echo "0 2 * * * /path/to/waterlab/backup.sh" | crontab -
```

### Monitoring Setup

1. **Log Management:**
   ```bash
   # View application logs
   docker-compose logs -f web

   # View database logs  
   docker-compose logs -f db

   # View nginx logs
   docker-compose logs -f nginx
   ```

2. **Health Monitoring:**
   ```bash
   # Check all services
   docker-compose ps

   # Health check script
   cat > health_check.sh << 'EOF'
   #!/bin/bash
   if curl -f http://localhost/health/ > /dev/null 2>&1; then
       echo "✅ Application is healthy"
   else
       echo "❌ Application is down"
       docker-compose restart web
   fi
   EOF
   ```

## 🔒 Security Checklist

- [ ] Changed default SECRET_KEY
- [ ] Set DEBUG=False
- [ ] Configured proper ALLOWED_HOSTS
- [ ] Set up SSL/HTTPS
- [ ] Configured secure session cookies
- [ ] Set up database backups
- [ ] Configured firewall (UFW)
- [ ] Updated server packages
- [ ] Set up monitoring
- [ ] Configured rate limiting

### Firewall Configuration

```bash
# Enable UFW
sudo ufw enable

# Allow SSH
sudo ufw allow ssh

# Allow HTTP/HTTPS
sudo ufw allow 80
sudo ufw allow 443

# Allow only necessary ports
sudo ufw deny 5432  # PostgreSQL
sudo ufw deny 6379  # Redis
sudo ufw deny 8000  # Django (behind nginx)
```

## 📊 Performance Optimization

### 1. Database Optimization

```bash
# Add to docker-compose.yml under db service environment:
POSTGRES_SHARED_PRELOAD_LIBRARIES=pg_stat_statements
POSTGRES_EFFECTIVE_CACHE_SIZE=1GB
POSTGRES_SHARED_BUFFERS=256MB
```

### 2. Redis Configuration

```bash
# Add redis.conf file:
maxmemory 256mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

### 3. Gunicorn Tuning

```bash
# Update Dockerfile CMD:
CMD ["gunicorn", "waterlab.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--worker-class", "sync", "--timeout", "120", "--max-requests", "1000", "--preload"]
```

## 🔄 Maintenance Commands

```bash
# Update application
git pull
docker-compose build web
docker-compose up -d

# Scale workers
docker-compose up -d --scale web=3

# Database maintenance
docker-compose exec web python manage.py clearsessions
docker-compose exec db vacuumdb -U waterlab -d waterlab_prod

# View resource usage
docker stats
```

## 🆘 Troubleshooting

### Common Issues

1. **Application won't start:**
   ```bash
   docker-compose logs web
   # Check for Django errors
   ```

2. **Database connection failed:**
   ```bash
   docker-compose logs db
   # Verify DB_PASSWORD in .env
   ```

3. **Static files not loading:**
   ```bash
   docker-compose exec web python manage.py collectstatic --noinput
   ```

4. **Permission denied errors:**
   ```bash
   sudo chown -R 1000:1000 staticfiles media logs
   ```

### Health Checks

```bash
# Application health
curl http://localhost/health/

# Database health
docker-compose exec db pg_isready -U waterlab

# Redis health
docker-compose exec redis redis-cli ping
```

## 📞 Support

For issues with deployment:
1. Check logs: `docker-compose logs -f`
2. Verify environment variables in `.env`
3. Ensure all services are running: `docker-compose ps`
4. Check firewall settings: `sudo ufw status`

---

**Note:** Replace `waterlab.yourdomain.com` with your actual domain name throughout the configuration files.