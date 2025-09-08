# Quick Start Guide - Lily Media AI for Pressure Washing

Get your pressure washing social media automation running in minutes!

## 🚀 One-Command Setup

```bash
# Interactive setup wizard (recommended)
python scripts/setup_wizard.py
```

The setup wizard will guide you through:
- ✅ System requirements check
- ✅ Pressure washing industry configuration  
- ✅ AI services setup for exterior cleaning
- ✅ Social platform integrations
- ✅ Field service software connections (Housecall Pro, Jobber)
- ✅ Database setup and job tracking

## 📋 Prerequisites

Before starting, ensure you have:

### Required Software
- **Python 3.11+** - [Download](https://python.org/downloads)
- **Node.js 18+** - [Download](https://nodejs.org)
- **PostgreSQL 14+** - [Download](https://postgresql.org/download) (optional for local dev)
- **Redis 6+** - [Download](https://redis.io/download) (optional for local dev)

### Required API Keys
- **OpenAI API Key** - [Get here](https://platform.openai.com/api-keys) (Required)
- **xAI API Key** - [Get here](https://x.ai) (Optional, for image generation)

### Optional API Keys
- **Meta App ID/Secret** - [Facebook Developers](https://developers.facebook.com)
- **X Client ID/Secret** - [Twitter Developers](https://developer.twitter.com)
- **LinkedIn Client ID/Secret** - [LinkedIn Developers](https://developers.linkedin.com)

## 🎯 Quick Setup (5 Minutes)

### 1. Clone & Navigate
```bash
git clone <repository-url>
cd lily-media-ai
```

### 2. Run Setup Wizard
```bash
python scripts/setup_wizard.py
```

### 3. Start the Platform
```bash
# All-in-one startup
./start_platform.sh

# Or start services individually:
./start_backend.sh   # Terminal 1
./start_frontend.sh  # Terminal 2
```

### 4. Access Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000  
- **API Docs**: http://localhost:8000/docs

## 🔧 Manual Setup (Advanced)

If you prefer manual configuration:

### 1. Environment Files
```bash
# Copy templates
cp .env.example .env
cp frontend/.env.example frontend/.env

# Edit configuration
nano .env
nano frontend/.env
```

### 2. Install Dependencies
```bash
# Backend
pip install -r requirements.txt

# Frontend
cd frontend && npm install
```

### 3. Database Setup
```bash
# Run migrations
alembic upgrade head
```

### 4. Start Services
```bash
# Backend
uvicorn app:app --host 0.0.0.0 --port 8000 --reload

# Frontend (new terminal)
cd frontend && npm run dev

# Celery worker (new terminal)
celery -A backend.tasks.celery_app worker --loglevel=info
```

## 🎉 First Steps

After setup:

1. **Create Account**: Visit http://localhost:3000 and sign up
2. **Configure AI**: Add your OpenAI API key in Settings
3. **Connect Platforms**: Link your social media accounts
4. **Create Content**: Generate your first AI-powered post!

## 🔍 Verify Installation

```bash
# Check backend health
curl http://localhost:8000/health

# Check frontend
curl http://localhost:3000

# Check API documentation
open http://localhost:8000/docs
```

## 🆘 Troubleshooting

### Common Issues

**"Module not found" errors:**
```bash
# Ensure you're in project directory
pwd
# Should show: /path/to/lily-media-ai

# Activate virtual environment if using one
source venv/bin/activate
```

**Database connection fails:**
```bash
# Check PostgreSQL is running
pg_ctl status

# Start PostgreSQL if needed
brew services start postgresql  # macOS
sudo systemctl start postgresql # Linux
```

**Port already in use:**
```bash
# Kill process using port 8000
lsof -ti:8000 | xargs kill -9

# Kill process using port 3000  
lsof -ti:3000 | xargs kill -9
```

**Frontend won't start:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Get Help

- 📚 **Documentation**: Check README.md and docs folder
- 🐛 **Issues**: Create GitHub issue with error details
- 💬 **Discussions**: Use GitHub Discussions for questions

## 🎯 Next Steps

Once running:

1. **Explore Features**: Try content generation, scheduling, analytics
2. **Customize Settings**: Configure AI models, posting preferences  
3. **Add Team Members**: Invite collaborators to your organization
4. **Set up Production**: Follow deployment guide for live usage
5. **Custom Domain**: Use Cloudflare setup guide for branding

## 📚 Additional Resources

- [Complete Setup Guide](README.md)
- [Environment Configuration](ENVIRONMENT_SETUP.md)  
- [Custom Domain Setup](CLOUDFLARE_SETUP.md)
- [Monitoring Guide](MONITORING.md)
- [API Documentation](http://localhost:8000/docs)

---

**Ready to transform your social media management? Start with the setup wizard above! 🚀**