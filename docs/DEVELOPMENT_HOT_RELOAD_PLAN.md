# Selextract Cloud - Hot Reloading Development Environment Plan

## 🎯 Objective

Transform the current Docker-heavy development workflow into a fast, native hot-reloading environment that eliminates the need for constant container rebuilds.

## 📊 Current Pain Points

- **Rebuild Time**: 30-60 seconds per code change vs. 1-3 seconds with hot reload
- **Productivity Loss**: ~80% of development time spent waiting for container rebuilds
- **Full Container Dependencies**: API and Frontend unnecessarily containerized during development

## 🏗️ Solution Architecture

### Pure Native Mode (Primary Development)

```
┌─────────────────────────────────────────────────────────────┐
│                    Development Machine                      │
├─────────────────────────────────────────────────────────────┤
│  Native Hot Reloading Layer                                │
│  ┌─────────────────┐    ┌─────────────────┐                │
│  │ FastAPI API     │    │ Next.js Frontend│                │
│  │ localhost:8000  │◄───│ localhost:3000  │                │
│  │ 🔥 Hot Reload   │    │ 🔥 Hot Reload   │                │
│  └─────────────────┘    └─────────────────┘                │
│           │                       ▲                        │
│           ▼                       │                        │
├─────────────────────────────────────────────────────────────┤
│  Containerized Infrastructure                               │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │ PostgreSQL   │ │ Redis        │ │ Celery Worker│        │
│  │ :5432        │ │ :6379        │ │ Background   │        │
│  │ Docker       │ │ Docker       │ │ Docker       │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

## 📁 File Structure Plan

```
selectium-saas/
├── dev/                              # New development utilities
│   ├── docker-compose.dev.yml        # Infrastructure-only containers
│   ├── .env.dev                      # Development environment variables
│   ├── setup-dev.sh                  # One-command development setup
│   ├── start-dev.sh                  # Start development environment
│   ├── stop-dev.sh                   # Stop development environment
│   └── reset-dev.sh                  # Reset development environment
├── scripts/dev/                      # Development scripts
│   ├── setup-api.sh                  # API development setup
│   ├── setup-frontend.sh             # Frontend development setup
│   ├── start-api.sh                  # Start API with hot reload
│   ├── start-frontend.sh             # Start frontend with hot reload
│   └── db-migrate.sh                 # Database migration utility
└── docs/
    └── DEVELOPMENT_GUIDE.md          # Complete development guide
```

## 🐳 Infrastructure-Only Docker Configuration

### `dev/docker-compose.dev.yml`

```yaml
# Infrastructure-only Docker Compose for native development
networks:
  selextract-dev:
    driver: bridge

volumes:
  dev_postgres_data:
  dev_redis_data:

services:
  # PostgreSQL Database
  selextract-postgres-dev:
    image: postgres:14-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${SELEXTRACT_DB_NAME:-selextract_dev}
      POSTGRES_USER: ${SELEXTRACT_DB_USER:-selextract}
      POSTGRES_PASSWORD: ${SELEXTRACT_DB_PASSWORD:-devpassword}
    ports:
      - "5432:5432"  # Expose to host for native API
    volumes:
      - dev_postgres_data:/var/lib/postgresql/data
      - ../db/init.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - selextract-dev
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${SELEXTRACT_DB_USER:-selextract}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis Cache/Queue
  selextract-redis-dev:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --requirepass ${SELEXTRACT_REDIS_PASSWORD:-devpassword}
    ports:
      - "6379:6379"  # Expose to host for native API
    volumes:
      - dev_redis_data:/data
    networks:
      - selextract-dev
    healthcheck:
      test: ["CMD", "redis-cli", "--no-auth-warning", "-a", "${SELEXTRACT_REDIS_PASSWORD:-devpassword}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Celery Worker (Background Tasks)
  selextract-worker-dev:
    build:
      context: ../worker
    restart: unless-stopped
    depends_on:
      selextract-postgres-dev:
        condition: service_healthy
      selextract-redis-dev:
        condition: service_healthy
    environment:
      # Database connection (container names)
      - SELEXTRACT_DB_HOST=selextract-postgres-dev
      - SELEXTRACT_DB_PORT=5432
      - SELEXTRACT_DB_NAME=${SELEXTRACT_DB_NAME:-selextract_dev}
      - SELEXTRACT_DB_USER=${SELEXTRACT_DB_USER:-selextract}
      - SELEXTRACT_DB_PASSWORD=${SELEXTRACT_DB_PASSWORD:-devpassword}
      # Redis connection (container names)
      - SELEXTRACT_REDIS_HOST=selextract-redis-dev
      - SELEXTRACT_REDIS_PORT=6379
      - SELEXTRACT_REDIS_PASSWORD=${SELEXTRACT_REDIS_PASSWORD:-devpassword}
      # Development settings
      - SELEXTRACT_ENVIRONMENT=development
      - SELEXTRACT_DEBUG=true
      - SELEXTRACT_LOG_LEVEL=DEBUG
      # External services
      - SELEXTRACT_WEBSHARE_API_KEY=${SELEXTRACT_WEBSHARE_API_KEY}
    networks:
      - selextract-dev
    volumes:
      - ../worker/results:/app/results
      - ../worker/logs:/app/logs
```

### `dev/.env.dev`

```bash
# Development Environment Variables
# Database (localhost for native API)
SELEXTRACT_DB_HOST=localhost
SELEXTRACT_DB_PORT=5432
SELEXTRACT_DB_NAME=selextract_dev
SELEXTRACT_DB_USER=selextract
SELEXTRACT_DB_PASSWORD=devpassword

# Redis (localhost for native API)
SELEXTRACT_REDIS_HOST=localhost
SELEXTRACT_REDIS_PORT=6379
SELEXTRACT_REDIS_PASSWORD=devpassword

# API Configuration
SELEXTRACT_API_URL=http://localhost:8000
SELEXTRACT_DEBUG=true
SELEXTRACT_ENVIRONMENT=development
SELEXTRACT_LOG_LEVEL=DEBUG

# Frontend Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000

# Development OAuth (use test credentials)
SELEXTRACT_GOOGLE_CLIENT_ID=your-dev-google-client-id
SELEXTRACT_GOOGLE_CLIENT_SECRET=your-dev-google-secret

# Development secrets (simple for local dev)
SELEXTRACT_JWT_SECRET_KEY=dev-jwt-secret-key-not-for-production
SELEXTRACT_API_SECRET_KEY=dev-api-secret-key-not-for-production
```

## 🚀 Development Scripts

### `dev/setup-dev.sh`

```bash
#!/bin/bash
# One-command development environment setup

set -e

echo "🚀 Setting up Selextract Cloud development environment..."

# Check prerequisites
check_prerequisites() {
    echo "📋 Checking prerequisites..."
    
    # Check Python 3.11+
    if ! python3 --version | grep -E "3\.(11|12)" > /dev/null; then
        echo "❌ Python 3.11+ required"
        exit 1
    fi
    
    # Check Node.js 18+
    if ! node --version | grep -E "v(18|19|20)" > /dev/null; then
        echo "❌ Node.js 18+ required"
        exit 1
    fi
    
    # Check Docker
    if ! docker --version > /dev/null 2>&1; then
        echo "❌ Docker required"
        exit 1
    fi
    
    # Check Docker Compose
    if ! docker compose version > /dev/null 2>&1; then
        echo "❌ Docker Compose required"
        exit 1
    fi
    
    echo "✅ All prerequisites met"
}

# Setup API environment
setup_api() {
    echo "🐍 Setting up API development environment..."
    
    cd ../api
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        echo "✅ Created Python virtual environment"
    fi
    
    # Activate and install dependencies
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install uvicorn[standard]  # Ensure uvicorn with reload
    
    echo "✅ API dependencies installed"
    cd ../dev
}

# Setup Frontend environment
setup_frontend() {
    echo "⚛️ Setting up Frontend development environment..."
    
    cd ../frontend
    
    # Install dependencies
    if [ ! -d "node_modules" ]; then
        npm install
        echo "✅ Frontend dependencies installed"
    else
        echo "📦 Frontend dependencies already installed"
    fi
    
    cd ../dev
}

# Setup infrastructure
setup_infrastructure() {
    echo "🐳 Setting up development infrastructure..."
    
    # Copy environment file
    if [ ! -f ".env.dev" ]; then
        cp .env.dev.example .env.dev
        echo "📝 Created .env.dev file - please update with your credentials"
    fi
    
    # Start infrastructure containers
    docker compose -f docker-compose.dev.yml up -d
    
    # Wait for services to be healthy
    echo "⏳ Waiting for infrastructure to be ready..."
    timeout 60 bash -c 'until docker compose -f docker-compose.dev.yml ps | grep "healthy"; do sleep 2; done'
    
    echo "✅ Infrastructure containers ready"
}

# Run database migrations
setup_database() {
    echo "🗄️ Setting up development database..."
    
    cd ../api
    source venv/bin/activate
    
    # Set environment for migration
    export $(grep -v '^#' ../dev/.env.dev | xargs)
    
    # Run migrations
    alembic upgrade head
    
    echo "✅ Database migrations completed"
    cd ../dev
}

# Main setup flow
main() {
    check_prerequisites
    setup_api
    setup_frontend
    setup_infrastructure
    setup_database
    
    echo ""
    echo "🎉 Development environment setup complete!"
    echo ""
    echo "🚀 Quick Start:"
    echo "   1. cd dev && ./start-dev.sh"
    echo "   2. Open http://localhost:3000 (Frontend)"
    echo "   3. Open http://localhost:8000/docs (API)"
    echo ""
    echo "📖 See docs/DEVELOPMENT_GUIDE.md for detailed usage"
}

main "$@"
```

### `dev/start-dev.sh`

```bash
#!/bin/bash
# Start development environment with hot reloading

set -e

echo "🚀 Starting Selextract Cloud development environment..."

# Start infrastructure if not running
if ! docker compose -f docker-compose.dev.yml ps | grep "Up" > /dev/null; then
    echo "🐳 Starting infrastructure containers..."
    docker compose -f docker-compose.dev.yml up -d
    sleep 5
fi

# Function to run API
start_api() {
    echo "🐍 Starting API with hot reload..."
    cd ../api
    source venv/bin/activate
    export $(grep -v '^#' ../dev/.env.dev | xargs)
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
}

# Function to run Frontend
start_frontend() {
    echo "⚛️ Starting Frontend with hot reload..."
    cd ../frontend
    export $(grep -v '^#' ../dev/.env.dev | xargs)
    npm run dev
}

# Check if user wants to run specific service
case "${1:-}" in
    "api")
        start_api
        ;;
    "frontend")
        start_frontend
        ;;
    *)
        echo "🔥 Choose development mode:"
        echo "   1. API only (recommended for backend development)"
        echo "   2. Frontend only (recommended for frontend development)"
        echo "   3. Both (requires separate terminals)"
        echo ""
        read -p "Enter choice (1/2/3): " choice
        
        case $choice in
            1)
                start_api
                ;;
            2)
                start_frontend
                ;;
            3)
                echo "🔄 Starting both services..."
                echo "📝 Run these commands in separate terminals:"
                echo "   Terminal 1: cd dev && ./start-dev.sh api"
                echo "   Terminal 2: cd dev && ./start-dev.sh frontend"
                echo ""
                echo "🎯 Or use your IDE's terminal/task runner for parallel execution"
                ;;
            *)
                echo "❌ Invalid choice"
                exit 1
                ;;
        esac
        ;;
esac
```

### `dev/stop-dev.sh`

```bash
#!/bin/bash
# Stop development environment

echo "🛑 Stopping Selextract Cloud development environment..."

# Stop infrastructure containers
docker compose -f docker-compose.dev.yml down

echo "✅ Development environment stopped"
echo "💡 API and Frontend processes may still be running - stop them manually if needed"
```

### `scripts/dev/db-migrate.sh`

```bash
#!/bin/bash
# Database migration utility for development

set -e

cd "$(dirname "$0")/../../api"

# Ensure API environment is activated
if [ ! -d "venv" ]; then
    echo "❌ API environment not set up. Run dev/setup-dev.sh first"
    exit 1
fi

source venv/bin/activate
export $(grep -v '^#' ../dev/.env.dev | xargs)

case "${1:-}" in
    "upgrade")
        echo "⬆️ Running database migrations..."
        alembic upgrade head
        echo "✅ Migrations completed"
        ;;
    "downgrade")
        echo "⬇️ Rolling back database migration..."
        alembic downgrade -1
        echo "✅ Rollback completed"
        ;;
    "reset")
        echo "🗑️ Resetting database..."
        read -p "This will destroy all data. Continue? (y/N): " confirm
        if [[ $confirm == [yY] ]]; then
            alembic downgrade base
            alembic upgrade head
            echo "✅ Database reset completed"
        fi
        ;;
    "status")
        echo "📊 Database migration status:"
        alembic current
        ;;
    *)
        echo "📋 Database Migration Utility"
        echo "Usage: $0 {upgrade|downgrade|reset|status}"
        echo ""
        echo "Commands:"
        echo "  upgrade   - Apply pending migrations"
        echo "  downgrade - Rollback last migration"
        echo "  reset     - Reset database (destructive)"
        echo "  status    - Show current migration status"
        ;;
esac
```

## 📖 Environment Variables Mapping

### Development vs Production

| Component | Development | Production |
|-----------|-------------|------------|
| **Database Host** | `localhost:5432` | `selextract-postgres:5432` |
| **Redis Host** | `localhost:6379` | `selextract-redis:6379` |
| **API URL** | `http://localhost:8000` | `https://api.selextract.com` |
| **Frontend URL** | `http://localhost:3000` | `https://app.selextract.com` |
| **Debug Mode** | `true` | `false` |
| **Log Level** | `DEBUG` | `INFO` |

## ⚡ Performance Benefits

### Before (Current Docker Setup)
```
Code Change → Docker Build → Container Start → Test
    ↓             ↓              ↓             ↓
  0.1s         30-45s         10-15s        1-3s
                    
Total: ~50 seconds per change
```

### After (Native Hot Reload)
```
Code Change → Hot Reload → Test
    ↓             ↓         ↓
  0.1s         0.5-2s     1-3s
                    
Total: ~3 seconds per change
```

**Productivity Gain: 94% reduction in development iteration time**

## 🔄 Development Workflow

### Daily Development Flow

1. **Start Development Environment**
   ```bash
   cd dev
   ./start-dev.sh
   ```

2. **Choose Development Mode**
   - **Backend Focus**: Run API only
   - **Frontend Focus**: Run Frontend only  
   - **Full Stack**: Run both in separate terminals

3. **Make Changes**
   - **API Changes**: Instant reload via uvicorn
   - **Frontend Changes**: Instant reload via Next.js
   - **Database Changes**: Use `scripts/dev/db-migrate.sh`

4. **Testing Integration**
   - Infrastructure always available at localhost ports
   - No container rebuilds needed
   - Real-time testing possible

### IDE Integration

#### VS Code Tasks (`.vscode/tasks.json`)
```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Start Development Environment",
            "type": "shell",
            "command": "cd dev && ./start-dev.sh",
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "panel": "new"
            }
        },
        {
            "label": "Start API Only",
            "type": "shell",
            "command": "cd dev && ./start-dev.sh api",
            "group": "build"
        },
        {
            "label": "Start Frontend Only",
            "type": "shell", 
            "command": "cd dev && ./start-dev.sh frontend",
            "group": "build"
        }
    ]
}
```

## 🛠️ Troubleshooting

### Common Issues

#### Port Conflicts
```bash
# Check what's using port 8000
lsof -i :8000

# Check what's using port 3000  
lsof -i :3000

# Kill process using port
kill -9 $(lsof -t -i:8000)
```

#### Database Connection Issues
```bash
# Check infrastructure status
docker compose -f dev/docker-compose.dev.yml ps

# Check database logs
docker compose -f dev/docker-compose.dev.yml logs selextract-postgres-dev

# Reset infrastructure
cd dev && ./stop-dev.sh && ./start-dev.sh
```

#### Environment Variable Issues
```bash
# Verify environment file
cat dev/.env.dev

# Test database connection
cd api && source venv/bin/activate
python -c "from database import engine; print('DB Connection:', engine.url)"
```

## 📋 Implementation Checklist

- [ ] Create `dev/` directory structure
- [ ] Create `docker-compose.dev.yml` for infrastructure-only containers
- [ ] Create development environment variables (`.env.dev`)
- [ ] Create setup script (`dev/setup-dev.sh`)
- [ ] Create start/stop scripts (`dev/start-dev.sh`, `dev/stop-dev.sh`)
- [ ] Create database migration utilities (`scripts/dev/db-migrate.sh`)
- [ ] Update API to use development database URLs
- [ ] Update Frontend to use development API URLs
- [ ] Create comprehensive development documentation
- [ ] Test complete workflow
- [ ] Create VS Code tasks/launch configurations
- [ ] Add troubleshooting documentation

## 🎯 Success Metrics

1. **Development Speed**: Reduce iteration time from ~50s to ~3s
2. **Setup Time**: One-command environment setup in under 2 minutes
3. **Resource Usage**: 70% reduction in development resource consumption
4. **Developer Experience**: Hot reloading for both API and Frontend
5. **Reliability**: Stable development environment with proper error handling

## 🔮 Future Enhancements

1. **Multi-Mode Support**: Add hybrid and full-docker development modes
2. **Database Seeding**: Add sample data generation for development
3. **Test Integration**: Hot reloading for tests
4. **Performance Monitoring**: Development performance metrics
5. **Remote Development**: Support for development in containers/codespaces

---

**Implementation Priority**: Start with pure native mode for immediate productivity gains, then expand to additional modes based on team needs.