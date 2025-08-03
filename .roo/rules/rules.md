# Selextract Cloud - Development Rules

**This constitution is mandatory for all development. Violations = automatic rejection.**
**Agents start with no memory. These strict guideliness are enforced for unified development system, even when tasks does not explicitly ask for it**
## 1. Non-Negotiable Core
**- UPHOLD THE RULES **

**1.1. Follow the Rules**
- Seriously, no deviations allowed

**1.2. Zero Placeholders**
- BANNED: `# ...`, `// TODO`, `/* implement */`, stubs, empty methods
- BANNED: Fake paths, imports, dependencies
- All code must be complete and executable

**1.3. Ready-to-Run**
- Scripts, configs, docs must work without modification
- Commands must be copy-paste executable

**1.4. Single Server Only**
- Production: runs via primary `docker-compose.yml` - do not break
- Development: FE and API runs uncontainerized, (./dev/start-api.sh, ./dev/start-frontend.sh) -> You are here!
## 2. Architecture Rules

**2.1. API-Only Communication**
- All services communicate through `/api/v1/`
- BANNED: Direct DB access from frontend
- REQUIRED: `Frontend → Nginx → Backend API → DB/Redis/Celery`

**2.2. Tech Stack**
- Backend: FastAPI, PostgreSQL, Redis, Celery
- Frontend: Next.js, TypeScript
- Infrastructure: Docker Compose, Nginx
- Monitoring: Prometheus, Grafana

## 3. Service-Specific Rules

### 3.1. API (FastAPI)

**Routing**
- Use `/api/v1/` prefix for all endpoints
- Define routes in `api/main.py`

**Auth**
- Use OAuth2 from `api/auth.py`
- JWTs only for sessions

**Data**
- Use Pydantic models from `api/schemas.py`
- Validate all external input

### 3.2. Frontend (Next.js)

**API Client**
- Use `frontend/lib/api.ts`
- Sync types with backend schemas

**Auth**
- Use `AuthContext` from `frontend/lib/auth.tsx`
- Call backend `/api/v1/auth/` endpoints only

**TypeScript**
- BANNED: `any` type
- Enable `"strict": true` in `tsconfig.json`

### 3.3. Worker (Celery)

**Resources**
- Use `try...finally` for browser contexts
- Define timeouts for all tasks

**Proxies**
- Use `ProxyManager` from `worker/proxies.py`
- No custom proxy logic

**Retries**
```python
@app.task(bind=True, max_retries=3)
def scrape_task(self, ...):
    try:
        # logic
    except RetriableError as e:
        raise self.retry(exc=e, countdown=2**self.request.retries * 60)
```

## 4. Database & Infrastructure

### 4.1. Database

**Migrations**
- Use Alembic only (`api/alembic/versions/`)
- BANNED: Direct `ALTER TABLE`
- Use `scripts/db-migrate.sh`

```bash
# Generate
./scripts/db-migrate.sh generate "description"
# Apply
./scripts/db-migrate.sh migrate development
```

**Queries**
- Use SQLAlchemy ORM
- BANNED: Raw SQL with string formatting - unless ORM capabilities deem unqualified.

### 4.2. Containers

**Resource Limits**
```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: '4G'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**Security**
```dockerfile
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser
```

**Secrets**
- BANNED: Real credentials in any file
- Use examples only in `.env.example`

## 5. Quality & Testing

**5.1. Static Analysis**
- Python: `mypy --strict`, `black`, `isort`, `flake8`
- TypeScript: `prettier`, `eslint`

**5.2. Testing**
- ≥90% coverage for business logic
- Integration tests for critical flows
- Include tests in same PR

**5.3. PR Compliance**
```markdown
**Compliance Verification**
- [x] Verified against `rules.md`
- [x] No placeholders
- [x] Tests included and passing
```

## 6 Commands (Development)

**6.1 Use rules**
- Commands should run from project root
- BANNED: `cd`, `cwd` - do not bypass
- ALLOWED PARTIALLY: `psql` -> NO SCHEMA CHANGES
- # Database Configuration (Native API connects to localhost)
**6.2 Development Credentials**
- SELEXTRACT_DB_HOST=localhost
- SELEXTRACT_DB_PORT=5432
- SELEXTRACT_DB_NAME=selextract_dev
- SELEXTRACT_DB_USER=selextract
- SELEXTRACT_DB_PASSWORD=devpassword
- DEV_DB_NAME=selextract_dev
- DEV_DB_USER=selextract
- DEV_DB_PASSWORD=devpassword

# Redis Configuration (Native API connects to localhost)
- SELEXTRACT_REDIS_HOST=localhost
- SELEXTRACT_REDIS_PORT=6379
- SELEXTRACT_REDIS_PASSWORD=devpassword
- DEV_REDIS_PASSWORD=devpassword
