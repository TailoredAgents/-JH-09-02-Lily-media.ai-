#!/usr/bin/env python3
"""
Interactive Setup Wizard for Lily Media AI Platform
Guides users through the complete setup process with validation and testing
"""

import os
import sys
import subprocess
import json
import secrets
import string
from pathlib import Path
from typing import Dict, Any, List, Optional
import re
from urllib.parse import urlparse

# Add the project root to the path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class Colors:
    """Color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class SetupWizard:
    """Interactive setup wizard for Lily Media AI"""
    
    def __init__(self):
        self.config = {}
        self.project_root = Path(__file__).parent.parent
        self.env_file = self.project_root / ".env"
        self.frontend_env_file = self.project_root / "frontend" / ".env"
        
    def print_header(self, text: str):
        """Print colored header text"""
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")
    
    def print_success(self, text: str):
        """Print success message"""
        print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")
    
    def print_warning(self, text: str):
        """Print warning message"""
        print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")
    
    def print_error(self, text: str):
        """Print error message"""
        print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")
    
    def print_info(self, text: str):
        """Print info message"""
        print(f"{Colors.OKBLUE}ℹ️  {text}{Colors.ENDC}")
    
    def generate_secret_key(self, length: int = 32) -> str:
        """Generate a secure secret key"""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def validate_email(self, email: str) -> bool:
        """Validate email address format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def validate_url(self, url: str) -> bool:
        """Validate URL format"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def prompt_user(self, question: str, default: str = "", required: bool = True, 
                   password: bool = False, validator=None) -> str:
        """Prompt user for input with validation"""
        while True:
            if password:
                import getpass
                prompt = f"{Colors.OKCYAN}🔹 {question}"
                if default:
                    prompt += f" (default: {'*' * len(default)})"
                prompt += f": {Colors.ENDC}"
                value = getpass.getpass(prompt)
            else:
                prompt = f"{Colors.OKCYAN}🔹 {question}"
                if default:
                    prompt += f" (default: {default})"
                prompt += f": {Colors.ENDC}"
                value = input(prompt).strip()
            
            if not value and default:
                value = default
            
            if required and not value:
                self.print_error("This field is required. Please enter a value.")
                continue
            
            if validator and value and not validator(value):
                self.print_error("Invalid format. Please try again.")
                continue
            
            return value
    
    def prompt_choice(self, question: str, choices: List[str], default: int = 0) -> str:
        """Prompt user to choose from a list of options"""
        while True:
            print(f"\n{Colors.OKCYAN}🔹 {question}{Colors.ENDC}")
            for i, choice in enumerate(choices):
                marker = "→" if i == default else " "
                print(f"  {marker} {i + 1}. {choice}")
            
            try:
                choice_input = input(f"\nEnter choice (1-{len(choices)}) [default: {default + 1}]: ").strip()
                if not choice_input:
                    return choices[default]
                
                choice_num = int(choice_input) - 1
                if 0 <= choice_num < len(choices):
                    return choices[choice_num]
                else:
                    self.print_error(f"Please enter a number between 1 and {len(choices)}")
            except ValueError:
                self.print_error("Please enter a valid number")
    
    def check_system_requirements(self) -> bool:
        """Check system requirements"""
        self.print_header("SYSTEM REQUIREMENTS CHECK")
        
        requirements_met = True
        
        # Check Python version
        python_version = sys.version_info
        if python_version.major == 3 and python_version.minor >= 11:
            self.print_success(f"Python {python_version.major}.{python_version.minor}.{python_version.micro} ✓")
        else:
            self.print_error(f"Python 3.11+ required, found {python_version.major}.{python_version.minor}")
            requirements_met = False
        
        # Check Node.js
        try:
            result = subprocess.run(['node', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                node_version = result.stdout.strip()
                self.print_success(f"Node.js {node_version} ✓")
            else:
                self.print_error("Node.js not found")
                requirements_met = False
        except FileNotFoundError:
            self.print_error("Node.js not found")
            requirements_met = False
        
        # Check npm
        try:
            result = subprocess.run(['npm', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                npm_version = result.stdout.strip()
                self.print_success(f"npm {npm_version} ✓")
            else:
                self.print_error("npm not found")
                requirements_met = False
        except FileNotFoundError:
            self.print_error("npm not found")
            requirements_met = False
        
        # Check PostgreSQL
        try:
            result = subprocess.run(['psql', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                pg_version = result.stdout.strip()
                self.print_success(f"PostgreSQL {pg_version} ✓")
            else:
                self.print_warning("PostgreSQL not found (optional for local development)")
        except FileNotFoundError:
            self.print_warning("PostgreSQL not found (optional for local development)")
        
        # Check Redis
        try:
            result = subprocess.run(['redis-cli', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                redis_version = result.stdout.strip()
                self.print_success(f"Redis {redis_version} ✓")
            else:
                self.print_warning("Redis not found (optional for local development)")
        except FileNotFoundError:
            self.print_warning("Redis not found (optional for local development)")
        
        return requirements_met
    
    def setup_environment(self):
        """Setup environment configuration"""
        self.print_header("ENVIRONMENT CONFIGURATION")
        
        # Environment type
        env_type = self.prompt_choice(
            "What environment are you setting up?",
            ["Development (local)", "Production (deployment)", "Testing"],
            default=0
        )
        
        environment = "development" if "Development" in env_type else "production" if "Production" in env_type else "testing"
        self.config['ENVIRONMENT'] = environment
        
        # Basic settings
        self.config['SECRET_KEY'] = self.generate_secret_key()
        self.config['JWT_SECRET_KEY'] = self.generate_secret_key()
        self.config['DEBUG'] = 'true' if environment == 'development' else 'false'
        
        self.print_success(f"Generated secure SECRET_KEY and JWT_SECRET_KEY")
        
        # Database configuration
        self.print_info("Database Configuration")
        
        db_choice = self.prompt_choice(
            "Database setup type:",
            ["Local PostgreSQL", "External PostgreSQL", "Skip (use defaults)"],
            default=0
        )
        
        if "Local" in db_choice:
            db_host = self.prompt_user("Database host", "localhost")
            db_port = self.prompt_user("Database port", "5432")
            db_name = self.prompt_user("Database name", "lily_media_ai")
            db_user = self.prompt_user("Database username", "postgres")
            db_password = self.prompt_user("Database password", "", password=True)
            
            self.config['DATABASE_URL'] = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            
        elif "External" in db_choice:
            db_url = self.prompt_user(
                "Database URL (postgresql://user:pass@host:port/dbname)", 
                validator=self.validate_url
            )
            self.config['DATABASE_URL'] = db_url
        else:
            self.config['DATABASE_URL'] = "postgresql://postgres:password@localhost:5432/lily_media_ai"
        
        # Redis configuration
        redis_choice = self.prompt_choice(
            "Redis setup type:",
            ["Local Redis", "External Redis", "Skip (use defaults)"],
            default=0
        )
        
        if "Local" in redis_choice:
            redis_host = self.prompt_user("Redis host", "localhost")
            redis_port = self.prompt_user("Redis port", "6379")
            redis_db = self.prompt_user("Redis database", "0")
            self.config['REDIS_URL'] = f"redis://{redis_host}:{redis_port}/{redis_db}"
        elif "External" in redis_choice:
            redis_url = self.prompt_user(
                "Redis URL (redis://host:port/db)", 
                validator=self.validate_url
            )
            self.config['REDIS_URL'] = redis_url
        else:
            self.config['REDIS_URL'] = "redis://localhost:6379/0"
    
    def setup_ai_services(self):
        """Setup AI service API keys"""
        self.print_header("AI SERVICES CONFIGURATION")
        
        # OpenAI Configuration
        self.print_info("OpenAI API Setup (Required for content generation)")
        print("Get your API key from: https://platform.openai.com/api-keys")
        
        openai_key = self.prompt_user("OpenAI API Key", password=True, required=True)
        self.config['OPENAI_API_KEY'] = openai_key
        
        # OpenAI Model Configuration
        self.config['OPENAI_MODEL'] = 'gpt-4o'
        self.config['OPENAI_RESEARCH_MODEL'] = 'gpt-4o-mini'
        self.config['OPENAI_EMBEDDING_MODEL'] = 'text-embedding-3-large'
        
        # xAI Configuration (optional)
        use_xai = self.prompt_choice(
            "Setup xAI Grok-2 for image generation?",
            ["Yes (recommended for image features)", "No (skip for now)"],
            default=0
        )
        
        if "Yes" in use_xai:
            print("Get your API key from: https://x.ai/")
            xai_key = self.prompt_user("xAI API Key", password=True, required=False)
            if xai_key:
                self.config['XAI_API_KEY'] = xai_key
                self.config['XAI_MODEL'] = 'grok-2-image'
                self.config['XAI_BASE_URL'] = 'https://api.x.ai/v1'
        
        self.print_success("AI services configured")
    
    def setup_social_platforms(self):
        """Setup social media platform integrations"""
        self.print_header("SOCIAL MEDIA PLATFORM SETUP")
        
        self.print_info("Configure social media platform integrations")
        self.print_warning("You can skip any platforms and configure them later in the application")
        
        # Meta (Facebook/Instagram) Setup
        setup_meta = self.prompt_choice(
            "Setup Meta (Facebook/Instagram) OAuth?",
            ["Yes (recommended)", "No (setup later)"],
            default=1
        )
        
        if "Yes" in setup_meta:
            print("\nMeta Developer Setup:")
            print("1. Go to https://developers.facebook.com/")
            print("2. Create a new app for 'Business' use case")
            print("3. Add Facebook Login and Instagram products")
            print("4. Get App ID and App Secret")
            
            meta_app_id = self.prompt_user("Meta App ID", required=False)
            meta_app_secret = self.prompt_user("Meta App Secret", password=True, required=False)
            
            if meta_app_id and meta_app_secret:
                self.config['META_APP_ID'] = meta_app_id
                self.config['META_APP_SECRET'] = meta_app_secret
                self.config['VITE_FEATURE_PARTNER_OAUTH'] = 'true'
        
        # X (Twitter) Setup
        setup_x = self.prompt_choice(
            "Setup X (Twitter) OAuth?",
            ["Yes (recommended)", "No (setup later)"],
            default=1
        )
        
        if "Yes" in setup_x:
            print("\nX Developer Setup:")
            print("1. Go to https://developer.twitter.com/")
            print("2. Create a new app with OAuth 2.0 enabled")
            print("3. Get Client ID and Client Secret")
            print("4. Note: Posting requires paid plan ($200/month)")
            
            x_client_id = self.prompt_user("X Client ID", required=False)
            x_client_secret = self.prompt_user("X Client Secret", password=True, required=False)
            
            if x_client_id and x_client_secret:
                self.config['X_CLIENT_ID'] = x_client_id
                self.config['X_CLIENT_SECRET'] = x_client_secret
                self.config['VITE_FEATURE_PARTNER_OAUTH'] = 'true'
        
        # LinkedIn Setup
        setup_linkedin = self.prompt_choice(
            "Setup LinkedIn OAuth?",
            ["Yes", "No (setup later)"],
            default=1
        )
        
        if "Yes" in setup_linkedin:
            print("\nLinkedIn Developer Setup:")
            print("1. Go to https://www.linkedin.com/developers/")
            print("2. Create a new app")
            print("3. Get Client ID and Client Secret")
            
            linkedin_client_id = self.prompt_user("LinkedIn Client ID", required=False)
            linkedin_client_secret = self.prompt_user("LinkedIn Client Secret", password=True, required=False)
            
            if linkedin_client_id and linkedin_client_secret:
                self.config['LINKEDIN_CLIENT_ID'] = linkedin_client_id
                self.config['LINKEDIN_CLIENT_SECRET'] = linkedin_client_secret
    
    def setup_monitoring(self):
        """Setup monitoring and observability"""
        self.print_header("MONITORING & OBSERVABILITY SETUP")
        
        # Sentry Setup (optional)
        setup_sentry = self.prompt_choice(
            "Setup Sentry for error tracking?",
            ["Yes (recommended for production)", "No (skip for now)"],
            default=1
        )
        
        if "Yes" in setup_sentry:
            print("Get your DSN from: https://sentry.io/")
            sentry_dsn = self.prompt_user("Sentry DSN", validator=self.validate_url, required=False)
            if sentry_dsn:
                self.config['SENTRY_DSN'] = sentry_dsn
        
        # Email Setup (optional)
        setup_email = self.prompt_choice(
            "Setup email notifications?",
            ["Yes", "No (skip for now)"],
            default=1
        )
        
        if "Yes" in setup_email:
            self.print_info("Email Configuration for notifications")
            
            email_provider = self.prompt_choice(
                "Email provider:",
                ["Gmail", "Custom SMTP", "Skip"],
                default=0
            )
            
            if "Gmail" in email_provider:
                gmail_email = self.prompt_user("Gmail address", validator=self.validate_email, required=False)
                gmail_password = self.prompt_user("Gmail App Password", password=True, required=False)
                
                if gmail_email and gmail_password:
                    self.config['SMTP_HOST'] = 'smtp.gmail.com'
                    self.config['SMTP_PORT'] = '587'
                    self.config['SMTP_USERNAME'] = gmail_email
                    self.config['SMTP_PASSWORD'] = gmail_password
                    self.config['EMAIL_FROM'] = gmail_email
            
            elif "Custom" in email_provider:
                smtp_host = self.prompt_user("SMTP Host", required=False)
                smtp_port = self.prompt_user("SMTP Port", "587", required=False)
                smtp_user = self.prompt_user("SMTP Username", required=False)
                smtp_pass = self.prompt_user("SMTP Password", password=True, required=False)
                email_from = self.prompt_user("From Email", validator=self.validate_email, required=False)
                
                if all([smtp_host, smtp_port, smtp_user, smtp_pass, email_from]):
                    self.config['SMTP_HOST'] = smtp_host
                    self.config['SMTP_PORT'] = smtp_port
                    self.config['SMTP_USERNAME'] = smtp_user
                    self.config['SMTP_PASSWORD'] = smtp_pass
                    self.config['EMAIL_FROM'] = email_from
    
    def create_env_files(self):
        """Create .env files with configuration"""
        self.print_header("CREATING CONFIGURATION FILES")
        
        # Backend .env file
        backend_env_content = f"""# Lily Media AI Platform Configuration
# Generated by Setup Wizard on {os.popen('date').read().strip()}

# ================================
# CORE APPLICATION SETTINGS
# ================================
ENVIRONMENT={self.config.get('ENVIRONMENT', 'development')}
SECRET_KEY={self.config.get('SECRET_KEY', self.generate_secret_key())}
JWT_SECRET_KEY={self.config.get('JWT_SECRET_KEY', self.generate_secret_key())}
DEBUG={self.config.get('DEBUG', 'true')}
API_VERSION=v1

# ================================
# DATABASE CONFIGURATION
# ================================
DATABASE_URL={self.config.get('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/lily_media_ai')}
REDIS_URL={self.config.get('REDIS_URL', 'redis://localhost:6379/0')}

# ================================
# AI SERVICES
# ================================
OPENAI_API_KEY={self.config.get('OPENAI_API_KEY', 'your-openai-api-key')}
OPENAI_MODEL={self.config.get('OPENAI_MODEL', 'gpt-4o')}
OPENAI_RESEARCH_MODEL={self.config.get('OPENAI_RESEARCH_MODEL', 'gpt-4o-mini')}
OPENAI_EMBEDDING_MODEL={self.config.get('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-large')}
"""
        
        # Add xAI if configured
        if 'XAI_API_KEY' in self.config:
            backend_env_content += f"""
# xAI Services
XAI_API_KEY={self.config['XAI_API_KEY']}
XAI_MODEL={self.config.get('XAI_MODEL', 'grok-2-image')}
XAI_BASE_URL={self.config.get('XAI_BASE_URL', 'https://api.x.ai/v1')}
"""
        
        # Add social platform OAuth if configured
        if any(key.startswith(('META_', 'X_', 'LINKEDIN_')) for key in self.config.keys()):
            backend_env_content += f"""
# ================================
# PARTNER OAUTH CONFIGURATION
# ================================
"""
            if 'META_APP_ID' in self.config:
                backend_env_content += f"""META_APP_ID={self.config['META_APP_ID']}
META_APP_SECRET={self.config['META_APP_SECRET']}
"""
            
            if 'X_CLIENT_ID' in self.config:
                backend_env_content += f"""X_CLIENT_ID={self.config['X_CLIENT_ID']}
X_CLIENT_SECRET={self.config['X_CLIENT_SECRET']}
"""
            
            if 'LINKEDIN_CLIENT_ID' in self.config:
                backend_env_content += f"""LINKEDIN_CLIENT_ID={self.config['LINKEDIN_CLIENT_ID']}
LINKEDIN_CLIENT_SECRET={self.config['LINKEDIN_CLIENT_SECRET']}
"""
        
        # Add email configuration if set
        if 'SMTP_HOST' in self.config:
            backend_env_content += f"""
# ================================
# EMAIL CONFIGURATION
# ================================
SMTP_HOST={self.config['SMTP_HOST']}
SMTP_PORT={self.config['SMTP_PORT']}
SMTP_USERNAME={self.config['SMTP_USERNAME']}
SMTP_PASSWORD={self.config['SMTP_PASSWORD']}
EMAIL_FROM={self.config['EMAIL_FROM']}
EMAIL_VERIFICATION_ENABLED=false
"""
        
        # Add monitoring if configured
        if 'SENTRY_DSN' in self.config:
            backend_env_content += f"""
# ================================
# MONITORING
# ================================
SENTRY_DSN={self.config['SENTRY_DSN']}
"""
        
        # Add defaults
        backend_env_content += f"""
# ================================
# PERFORMANCE & DEFAULTS
# ================================
CACHE_TTL=300
MAX_CACHE_SIZE=1000
CONNECTION_POOL_SIZE=100
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600
LOG_LEVEL=INFO
"""
        
        # Write backend .env file
        with open(self.env_file, 'w') as f:
            f.write(backend_env_content)
        
        self.print_success(f"Created backend .env file: {self.env_file}")
        
        # Frontend .env file
        frontend_env_content = f"""# Frontend Configuration
# Generated by Setup Wizard

VITE_API_URL=http://localhost:8000
VITE_ENVIRONMENT={self.config.get('ENVIRONMENT', 'development')}
VITE_FEATURE_PARTNER_OAUTH={self.config.get('VITE_FEATURE_PARTNER_OAUTH', 'false')}
VITE_APP_NAME=Lily Media AI

# Feature Flags
VITE_FEATURE_AUTONOMOUS_POSTING=true
VITE_FEATURE_DEEP_RESEARCH=true
VITE_FEATURE_BILLING=true
"""
        
        # Create frontend directory if it doesn't exist
        self.frontend_env_file.parent.mkdir(exist_ok=True)
        
        # Write frontend .env file
        with open(self.frontend_env_file, 'w') as f:
            f.write(frontend_env_content)
        
        self.print_success(f"Created frontend .env file: {self.frontend_env_file}")
    
    def install_dependencies(self):
        """Install Python and Node.js dependencies"""
        self.print_header("INSTALLING DEPENDENCIES")
        
        install_deps = self.prompt_choice(
            "Install dependencies now?",
            ["Yes (recommended)", "No (install manually later)"],
            default=0
        )
        
        if "Yes" not in install_deps:
            self.print_info("Skipping dependency installation")
            return
        
        # Install Python dependencies
        self.print_info("Installing Python dependencies...")
        try:
            result = subprocess.run([
                sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'
            ], cwd=self.project_root, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.print_success("Python dependencies installed")
            else:
                self.print_error("Failed to install Python dependencies")
                print(result.stderr)
        except Exception as e:
            self.print_error(f"Error installing Python dependencies: {e}")
        
        # Install Node.js dependencies
        self.print_info("Installing Node.js dependencies...")
        try:
            result = subprocess.run([
                'npm', 'install'
            ], cwd=self.project_root / 'frontend', capture_output=True, text=True)
            
            if result.returncode == 0:
                self.print_success("Node.js dependencies installed")
            else:
                self.print_error("Failed to install Node.js dependencies")
                print(result.stderr)
        except Exception as e:
            self.print_error(f"Error installing Node.js dependencies: {e}")
    
    def setup_database(self):
        """Setup database"""
        self.print_header("DATABASE SETUP")
        
        setup_db = self.prompt_choice(
            "Setup database now?",
            ["Yes (run migrations)", "No (setup manually later)"],
            default=0
        )
        
        if "Yes" not in setup_db:
            self.print_info("Skipping database setup")
            return
        
        # Test database connection first
        self.print_info("Testing database connection...")
        try:
            # Import after env file is created
            os.environ.update(self.config)
            
            import psycopg2
            from urllib.parse import urlparse
            
            db_url = self.config.get('DATABASE_URL', '')
            parsed = urlparse(db_url)
            
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                database=parsed.path[1:],  # Remove leading slash
                user=parsed.username,
                password=parsed.password
            )
            conn.close()
            
            self.print_success("Database connection successful")
            
            # Run Alembic migrations
            self.print_info("Running database migrations...")
            try:
                result = subprocess.run([
                    'alembic', 'upgrade', 'head'
                ], cwd=self.project_root, capture_output=True, text=True)
                
                if result.returncode == 0:
                    self.print_success("Database migrations completed")
                else:
                    self.print_error("Database migration failed")
                    print(result.stderr)
            except Exception as e:
                self.print_error(f"Error running migrations: {e}")
                
        except ImportError:
            self.print_warning("psycopg2 not available, skipping database test")
        except Exception as e:
            self.print_error(f"Database connection failed: {e}")
    
    def create_startup_scripts(self):
        """Create startup scripts for development"""
        self.print_header("CREATING STARTUP SCRIPTS")
        
        # Backend startup script
        backend_script = f"""#!/bin/bash
# Lily Media AI Backend Startup Script
# Generated by Setup Wizard

export $(cat .env | grep -v '^#' | xargs)

echo "🚀 Starting Lily Media AI Backend..."
echo "Environment: $ENVIRONMENT"
echo "Database: ${{DATABASE_URL%@*}}@***"

# Start backend server
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
"""
        
        backend_script_path = self.project_root / "start_backend.sh"
        with open(backend_script_path, 'w') as f:
            f.write(backend_script)
        os.chmod(backend_script_path, 0o755)
        
        # Frontend startup script
        frontend_script = f"""#!/bin/bash
# Lily Media AI Frontend Startup Script
# Generated by Setup Wizard

cd frontend

echo "🎨 Starting Lily Media AI Frontend..."
echo "API URL: ${{VITE_API_URL:-http://localhost:8000}}"

# Start frontend development server
npm run dev
"""
        
        frontend_script_path = self.project_root / "start_frontend.sh"
        with open(frontend_script_path, 'w') as f:
            f.write(frontend_script)
        os.chmod(frontend_script_path, 0o755)
        
        # Combined startup script
        combined_script = f"""#!/bin/bash
# Lily Media AI Full Stack Startup Script
# Generated by Setup Wizard

echo "🚀 Starting Lily Media AI Platform..."

# Start backend in background
./start_backend.sh &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Start frontend
./start_frontend.sh &
FRONTEND_PID=$!

echo "✅ Backend started (PID: $BACKEND_PID)"
echo "✅ Frontend started (PID: $FRONTEND_PID)"
echo ""
echo "🌐 Access your application at:"
echo "   Frontend: http://localhost:3000"
echo "   Backend API: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for user to stop
wait
"""
        
        combined_script_path = self.project_root / "start_platform.sh"
        with open(combined_script_path, 'w') as f:
            f.write(combined_script)
        os.chmod(combined_script_path, 0o755)
        
        self.print_success("Created startup scripts:")
        self.print_info(f"  • {backend_script_path}")
        self.print_info(f"  • {frontend_script_path}")
        self.print_info(f"  • {combined_script_path}")
    
    def show_completion_summary(self):
        """Show setup completion summary"""
        self.print_header("SETUP COMPLETED SUCCESSFULLY!")
        
        print(f"{Colors.OKGREEN}🎉 Lily Media AI Platform is ready to use!{Colors.ENDC}\n")
        
        print(f"{Colors.BOLD}📁 Configuration Files Created:{Colors.ENDC}")
        print(f"  • {self.env_file}")
        print(f"  • {self.frontend_env_file}")
        print(f"  • Startup scripts in project root")
        
        print(f"\n{Colors.BOLD}🚀 Next Steps:{Colors.ENDC}")
        print("  1. Start the platform:")
        print(f"     {Colors.OKCYAN}./start_platform.sh{Colors.ENDC}")
        print("  2. Access the application:")
        print(f"     {Colors.OKCYAN}http://localhost:3000{Colors.ENDC}")
        print("  3. Create your first account (first user becomes admin)")
        print("  4. Configure social media connections in the app")
        
        print(f"\n{Colors.BOLD}📚 Documentation:{Colors.ENDC}")
        print("  • README.md - Complete setup and usage guide")
        print("  • CLOUDFLARE_SETUP.md - Custom domain setup")
        print("  • MONITORING.md - Monitoring and observability")
        
        if 'VITE_FEATURE_PARTNER_OAUTH' in self.config and self.config['VITE_FEATURE_PARTNER_OAUTH'] == 'true':
            print(f"\n{Colors.BOLD}🔗 OAuth Integration:{Colors.ENDC}")
            print("  Partner OAuth is enabled! You can connect accounts in:")
            print("  Settings → Integrations → Connect Accounts")
        
        print(f"\n{Colors.BOLD}🆘 Need Help?{Colors.ENDC}")
        print("  • Check the documentation for troubleshooting")
        print("  • Verify all services are running: ./check_services.sh")
        print("  • View logs: tail -f logs/*.log")
        
        print(f"\n{Colors.OKGREEN}✨ Welcome to Lily Media AI Platform! ✨{Colors.ENDC}")
    
    def run(self):
        """Run the complete setup wizard"""
        try:
            # Welcome message
            self.print_header("LILY MEDIA AI PLATFORM SETUP WIZARD")
            print("Welcome to the interactive setup wizard!")
            print("This will guide you through configuring your platform.\n")
            
            # Check system requirements
            if not self.check_system_requirements():
                self.print_error("System requirements not met. Please install missing dependencies.")
                return False
            
            # Run setup steps
            self.setup_environment()
            self.setup_ai_services()
            self.setup_social_platforms()
            self.setup_monitoring()
            self.create_env_files()
            self.install_dependencies()
            self.setup_database()
            self.create_startup_scripts()
            
            # Show completion summary
            self.show_completion_summary()
            
            return True
            
        except KeyboardInterrupt:
            print(f"\n\n{Colors.WARNING}Setup interrupted by user{Colors.ENDC}")
            return False
        except Exception as e:
            self.print_error(f"Setup failed: {e}")
            return False

def main():
    """Main entry point"""
    wizard = SetupWizard()
    success = wizard.run()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()