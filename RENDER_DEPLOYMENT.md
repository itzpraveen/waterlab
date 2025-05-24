# Render.com Deployment Guide - Water Lab LIMS

## 🚀 Deploy to Render.com

Render.com is a modern cloud platform perfect for Django applications with managed PostgreSQL databases.

## Prerequisites

1. **GitHub Repository**: Your code must be in a GitHub repository
2. **Render Account**: Sign up at [render.com](https://render.com)

## Step-by-Step Deployment

### 1. Prepare Your Repository

Make sure your code is pushed to GitHub with these files:
- `requirements.txt` ✅
- `build.sh` ✅ 
- `settings_render.py` ✅
- `render.yaml` ✅

### 2. Create Render Services

#### Option A: Using render.yaml (Recommended)

1. **Connect GitHub** to Render
2. **Create New Blueprint** from your repository
3. Render will automatically read `render.yaml` and create:
   - Web Service (Django app)
   - PostgreSQL Database

#### Option B: Manual Setup

##### Create Database First
1. Go to Render Dashboard
2. Click **"New +"** → **"PostgreSQL"**
3. Configure:
   - **Name**: `waterlab-db`
   - **Database**: `waterlab_prod`
   - **User**: `waterlab`
   - **Region**: Choose closest to your users
   - **Plan**: Select based on needs (Free tier available)

##### Create Web Service
1. Click **"New +"** → **"Web Service"**
2. **Connect Repository**: Select your GitHub repo
3. Configure:
   - **Name**: `waterlab-lims`
   - **Environment**: `Python`
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn waterlab.wsgi:application`
   - **Plan**: Select based on needs

### 3. Environment Variables

In your Web Service settings, add these environment variables:

#### Required Variables:
```bash
DJANGO_SETTINGS_MODULE=waterlab.settings_render
SECRET_KEY=your-generated-secret-key-here
DATABASE_URL=postgresql://user:password@host:port/database
```

#### Optional Variables:
```bash
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
WEB_CONCURRENCY=4
```

### 4. Generate Secret Key

Run this command locally to generate a secret key:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 5. Database Connection

Render automatically provides `DATABASE_URL` when you link your database to the web service.

To link database:
1. Go to your **Web Service** settings
2. Click **"Environment"** tab
3. Click **"Add Environment Variable"**
4. Key: `DATABASE_URL`
5. Value: Select your database from dropdown

### 6. Deploy

1. **Push to GitHub**: Any push to your main branch triggers deployment
2. **Watch Build Logs**: Monitor the deployment in Render dashboard
3. **Access Application**: Use the provided `.onrender.com` URL

## 🔧 Post-Deployment Setup

### Create Superuser

After successful deployment:

1. Go to your Web Service dashboard
2. Click **"Shell"** tab
3. Run:
```bash
python manage.py createsuperuser
```

### Load Initial Data

If you have fixtures:
```bash
python manage.py loaddata fixtures/initial_data.json
```

## 🛠️ Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `DJANGO_SETTINGS_MODULE` | ✅ | `waterlab.settings_render` |
| `SECRET_KEY` | ✅ | Django secret key |
| `DATABASE_URL` | ✅ | Auto-provided by Render |
| `EMAIL_HOST` | ❌ | SMTP server (default: smtp.gmail.com) |
| `EMAIL_HOST_USER` | ❌ | Email username |
| `EMAIL_HOST_PASSWORD` | ❌ | Email password/app password |
| `WEB_CONCURRENCY` | ❌ | Number of workers (default: 4) |

## 📊 Render Plans & Pricing

### Free Tier Limitations:
- **Web Service**: Spins down after 15 minutes of inactivity
- **Database**: 1GB storage, expires after 90 days
- **Bandwidth**: 100GB/month

### Paid Plans:
- **Starter ($7/month)**: Always-on, custom domains
- **Standard ($25/month)**: More resources, priority support
- **Pro ($85/month)**: High performance, autoscaling

## 🔒 Security Best Practices

1. **Use Environment Variables** for all secrets
2. **Enable HTTPS** (automatically provided by Render)
3. **Set Strong SECRET_KEY**
4. **Use Gmail App Passwords** for email
5. **Regular Database Backups** (available in paid plans)

## 🔄 Custom Domain Setup

1. **Upgrade to Paid Plan**
2. Go to **Settings** → **Custom Domains**
3. Add your domain
4. Update DNS records as instructed

## 📝 Monitoring & Logs

### View Logs:
1. Go to your Web Service
2. Click **"Logs"** tab
3. Monitor real-time application logs

### Metrics:
- **CPU/Memory Usage**
- **Response Times**
- **Error Rates**

## 🆘 Troubleshooting

### Common Issues:

1. **Build Fails**:
   ```bash
   # Check build.sh permissions
   chmod +x build.sh
   git add build.sh
   git commit -m "Make build.sh executable"
   git push
   ```

2. **Database Connection Error**:
   - Verify `DATABASE_URL` is set
   - Check database service is running

3. **Static Files Not Loading**:
   - Ensure WhiteNoise is in requirements.txt
   - Check `collectstatic` runs in build.sh

4. **Service Keeps Spinning Down**:
   - Upgrade to paid plan for always-on service

### Health Check:
Access `https://your-app.onrender.com/health/` to verify deployment.

## 🚀 Deployment Checklist

- [ ] Code pushed to GitHub
- [ ] `requirements.txt` updated
- [ ] `build.sh` is executable
- [ ] Environment variables configured
- [ ] Database linked to web service
- [ ] SECRET_KEY generated and set
- [ ] Build completed successfully
- [ ] Superuser created
- [ ] Application accessible via URL
- [ ] Health check endpoint works

## 💡 Tips for Success

1. **Test Locally First**: Use `settings_render.py` locally
2. **Monitor Build Logs**: Watch for errors during deployment
3. **Use Render Shell**: For database operations and debugging
4. **Set Up Email**: Configure SMTP for notifications
5. **Plan for Scale**: Consider paid plans for production use

## 📞 Support

- **Render Documentation**: [render.com/docs](https://render.com/docs)
- **Community Forum**: [community.render.com](https://community.render.com)
- **Status Page**: [status.render.com](https://status.render.com)

---

Your Water Lab LIMS is now ready for professional hosting on Render.com! 🎉