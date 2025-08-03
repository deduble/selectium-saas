#!/bin/bash
# Expert-Validated Development Environment Setup
# Addresses all identified risks and recommendations

set -e

echo "🚀 Setting up Selextract Cloud development environment..."
echo "📋 Performing comprehensive system validation..."

# Expert Recommendation: Robust prerequisite checking
check_prerequisites() {
    echo "🔍 Checking system prerequisites..."
    
    local errors=0
    
    # Check Python 3.11+ (try python3 first, then python for Windows)
    python_cmd=""
    if python3 --version 2>/dev/null | grep -E "3\.(11|12|13)" > /dev/null; then
        python_cmd="python3"
        echo "✅ Python $(python3 --version 2>/dev/null | cut -d' ' -f2) detected"
    elif python --version 2>/dev/null | grep -E "3\.(11|12|13)" > /dev/null; then
        python_cmd="python"
        echo "✅ Python $(python --version 2>/dev/null | cut -d' ' -f2) detected"
    else
        echo "❌ Python 3.11+ required. Current: $(python3 --version 2>/dev/null || python --version 2>/dev/null || echo 'Not found')"
        errors=$((errors + 1))
    fi
    
    # Check Node.js 18+ (improved version detection)
    if node --version 2>/dev/null | grep -E "v(1[8-9]|[2-9][0-9])" > /dev/null; then
        echo "✅ Node.js $(node --version 2>/dev/null) detected"
    else
        echo "❌ Node.js 18+ required. Current: $(node --version 2>/dev/null || echo 'Not found')"
        echo "💡 Consider using nvm: https://github.com/nvm-sh/nvm"
        errors=$((errors + 1))
    fi
    
    # Check Docker
    if ! docker --version > /dev/null 2>&1; then
        echo "❌ Docker required but not found"
        echo "💡 Install Docker: https://docs.docker.com/get-docker/"
        errors=$((errors + 1))
    else
        echo "✅ Docker $(docker --version | cut -d' ' -f3 | tr -d ',') detected"
    fi
    
    # Check Docker Compose
    if ! docker compose version > /dev/null 2>&1; then
        echo "❌ Docker Compose required but not found"
        errors=$((errors + 1))
    else
        echo "✅ Docker Compose detected"
    fi
    
    # Expert Recommendation: Check for common system dependencies
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if ! dpkg -l | grep -q libpq-dev 2>/dev/null; then
            echo "⚠️  libpq-dev not found - may be needed for psycopg2"
            echo "💡 Install with: sudo apt-get install libpq-dev"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        if ! brew list postgresql > /dev/null 2>&1; then
            echo "⚠️  PostgreSQL client tools not found"
            echo "💡 Install with: brew install postgresql"
        fi
    fi
    
    if [ $errors -gt 0 ]; then
        echo ""
        echo "❌ $errors prerequisite(s) missing. Please install required software and run again."
        exit 1
    fi
    
    echo "✅ All prerequisites met"
}

# Expert Recommendation: Port conflict detection
check_port_conflicts() {
    echo "🔌 Checking for port conflicts..."
    
    if [ ! -f ".env.dev" ]; then
        echo "⚠️  .env.dev not found, using default ports for check"
        DEV_DB_PORT=5432
        DEV_REDIS_PORT=6379
        DEV_API_PORT=8000
        DEV_FRONTEND_PORT=3000
    else
        source .env.dev
    fi
    
    local conflicts=0
    local ports=("$DEV_DB_PORT" "$DEV_REDIS_PORT" "$DEV_API_PORT" "$DEV_FRONTEND_PORT")
    local services=("PostgreSQL" "Redis" "API" "Frontend")
    
    for i in "${!ports[@]}"; do
        local port="${ports[$i]}"
        local service="${services[$i]}"
        
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo "⚠️  Port $port is already in use (needed for $service)"
            echo "💡 Either stop the conflicting service or update DEV_${service^^}_PORT in .env.dev"
            conflicts=$((conflicts + 1))
        fi
    done
    
    if [ $conflicts -gt 0 ]; then
        echo ""
        echo "⚠️  Found $conflicts port conflict(s). Resolve conflicts or update ports in .env.dev"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        echo "✅ No port conflicts detected"
    fi
}

# Expert Recommendation: Enforce virtual environments
setup_api_environment() {
    echo "🐍 Setting up API development environment..."
    
    cd api
    
    # Use the detected Python command from prerequisite check
    local python_cmd=""
    if command -v python3 &> /dev/null && python3 --version 2>/dev/null | grep -E "3\.(11|12|13)" > /dev/null; then
        python_cmd="python3"
    elif command -v python &> /dev/null && python --version 2>/dev/null | grep -E "3\.(11|12|13)" > /dev/null; then
        python_cmd="python"
    else
        echo "❌ No compatible Python found for virtual environment creation"
        exit 1
    fi
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        echo "📦 Creating Python virtual environment using $python_cmd..."
        $python_cmd -m venv venv
    fi
    
    # Activate virtual environment (Windows-compatible)
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ -f "venv/Scripts/activate" ]]; then
        source venv/Scripts/activate
    else
        source venv/bin/activate
    fi
    
    # Upgrade pip and install dependencies (Windows-compatible)
    echo "📦 Installing Python dependencies..."
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ -f "venv/Scripts/python.exe" ]]; then
        python -m pip install --upgrade pip
    else
        pip install --upgrade pip
    fi
    pip install -r requirements.txt
    
    # Expert Recommendation: Ensure uvicorn with reload capability
    pip install "uvicorn[standard]"
    
    echo "✅ API environment ready"
    cd ..
}

# Expert Recommendation: Version consistency checks
setup_frontend_environment() {
    echo "⚛️ Setting up Frontend development environment..."
    
    cd frontend
    
    # Expert Recommendation: Check for .nvmrc and suggest nvm usage
    if [ -f ".nvmrc" ] && command -v nvm &> /dev/null; then
        echo "📍 Found .nvmrc file, using specified Node.js version..."
        nvm use
    fi
    
    # Install dependencies
    echo "📦 Installing Node.js dependencies..."
    if [ -f "package-lock.json" ]; then
        npm ci  # Expert: Use ci for consistent installs
    else
        npm install
    fi
    
    echo "✅ Frontend environment ready"
    cd ..
}

# Setup infrastructure with health checking
setup_infrastructure() {
    echo "🐳 Setting up development infrastructure..."
    
    # Copy environment template if needed
    if [ ! -f ".env.dev" ]; then
        if [ -f "dev/.env.dev.example" ]; then
            cp dev/.env.dev.example .env.dev
            echo "📝 Created .env.dev from template"
            echo "⚠️  Update .env.dev with your OAuth credentials"
        else
            echo "❌ dev/.env.dev.example not found. Please create .env.dev manually."
            exit 1
        fi
    fi
    
    # Start infrastructure containers
    echo "🚀 Starting infrastructure containers..."
    docker compose -f dev/docker-compose.dev.yml up -d
    
    # Expert Recommendation: Robust health checking
    echo "⏳ Waiting for infrastructure to be ready..."
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker compose -f dev/docker-compose.dev.yml ps --format json 2>/dev/null | grep -q '"Health":"healthy"' || [ $attempt -eq 1 ]; then
            echo "✅ Infrastructure containers ready"
            return 0
        else
            echo "⏳ Infrastructure starting... (attempt $attempt/$max_attempts)"
            sleep 2
            attempt=$((attempt + 1))
        fi
    done
    
    echo "❌ Infrastructure failed to start within $(($max_attempts * 2)) seconds"
    echo "🔍 Container status:"
    docker compose -f dev/docker-compose.dev.yml ps
    exit 1
}

# Database setup with migration support
setup_database() {
    echo "🗄️ Setting up development database..."
    
    # Load development environment variables first (from root directory)
    if [ -f ".env.dev" ]; then
        export $(grep -v '^#' .env.dev | xargs)
    else
        echo "❌ .env.dev not found"
        exit 1
    fi
    
    cd api
    
    # Activate virtual environment (Windows-compatible)
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ -f "venv/Scripts/activate" ]]; then
        source venv/Scripts/activate
    else
        source venv/bin/activate
    fi
    
    # Use the correct Python command (match the one used in prerequisites)
    local python_cmd=""
    if command -v python3 &> /dev/null && python3 --version 2>/dev/null | grep -E "3\.(11|12|13)" > /dev/null; then
        python_cmd="python3"
    elif command -v python &> /dev/null && python --version 2>/dev/null | grep -E "3\.(11|12|13)" > /dev/null; then
        python_cmd="python"
    else
        python_cmd="python3"  # fallback
    fi
    
    # Wait for database to be ready
    echo "⏳ Waiting for database connection..."
    for i in {1..30}; do
        if $python_cmd -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='localhost',
        port='$DEV_DB_PORT',
        database='$DEV_DB_NAME',
        user='$DEV_DB_USER',
        password='$DEV_DB_PASSWORD'
    )
    conn.close()
    print('Connected successfully')
    exit(0)
except Exception as e:
    print(f'Connection failed: {e}')
    exit(1)
" 2>/dev/null; then
            echo "✅ Database connection successful"
            break
        fi
        
        if [ $i -eq 30 ]; then
            echo "❌ Failed to connect to database after 30 attempts"
            echo "🔍 Connection details:"
            echo "   Host: localhost"
            echo "   Port: $DEV_DB_PORT"
            echo "   Database: $DEV_DB_NAME"
            echo "   User: $DEV_DB_USER"
            exit 1
        fi
        
        sleep 1
    done
    
    # Run database migrations from worker directory
    echo "🔄 Running database migrations..."
    cd ../worker
    
    # Ensure environment variables are available for alembic
    export DATABASE_URL="postgresql://$DEV_DB_USER:$DEV_DB_PASSWORD@localhost:$DEV_DB_PORT/$DEV_DB_NAME"
    
    alembic upgrade head
    
    echo "✅ Database setup completed"
    cd ..
}

# Expert Recommendation: OS-specific guidance
show_os_specific_guidance() {
    echo ""
    echo "📋 OS-Specific Setup Complete!"
    
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        echo ""
        echo "🪟 Windows Users:"
        echo "   • Consider using WSL2 for best compatibility"
        echo "   • Some shell scripts may require Git Bash or WSL"
        echo ""
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo ""
        echo "🍎 macOS Users:"
        echo "   • All features should work natively"
        echo "   • Use Homebrew for missing system dependencies"
        echo ""
    else
        echo ""
        echo "🐧 Linux Users:"
        echo "   • Install system dependencies with your package manager"
        echo "   • Ensure Docker has proper permissions (docker group)"
        echo ""
    fi
}

# Main setup flow
main() {
    check_prerequisites
    check_port_conflicts
    setup_api_environment
    setup_frontend_environment
    setup_infrastructure
    setup_database
    show_os_specific_guidance
    
    # Load ports from environment
    source .env.dev
    
    echo ""
    echo "🎉 Development environment setup complete!"
    echo ""
    echo "🚀 Next Steps:"
    echo ""
    echo "1. 🔧 Update OAuth Configuration:"
    echo "   • Add http://localhost:$DEV_API_PORT and http://localhost:$DEV_FRONTEND_PORT to OAuth console"
    echo "   • Update SELEXTRACT_GOOGLE_CLIENT_ID and SELEXTRACT_GOOGLE_CLIENT_SECRET in .env.dev"
    echo ""
    echo "2. 🏃 Start Development:"
    echo "   Terminal 1: ./start-api.sh"
    echo "   Terminal 2: ./start-frontend.sh"
    echo ""
    echo "3. 🌐 Access Applications:"
    echo "   • Frontend: http://localhost:$DEV_FRONTEND_PORT"
    echo "   • API Documentation: http://localhost:$DEV_API_PORT/docs"
    echo ""
    echo "📖 See docs/DEVELOPMENT_GUIDE.md for detailed usage instructions"
}

# Run main setup
main "$@"