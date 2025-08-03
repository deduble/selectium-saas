# Selextract Cloud - Local Development Quick Start

This guide provides the fastest way to get the Selextract Cloud environment running on your local machine for development.

## 🔥 NEW: Hot Reload Development (Recommended)

For the fastest development experience with instant hot reloading, use our new hybrid setup:

**⚡ 5-Minute Setup:**
```bash
cd dev && ./quick-start.sh
```

**🚀 Launch Commands:**
```bash
# Terminal 1: API (2-second hot reload)
./start-api.sh

# Terminal 2: Frontend (0.5-second hot reload)
./start-frontend.sh
```

**📈 Performance Benefits:**
- **94% faster development cycles**
- **No Docker rebuilds** during development
- **Native IDE debugging** support

**📖 Full Guide:** See [`QUICK_START_HOT_RELOAD.md`](QUICK_START_HOT_RELOAD.md) for complete setup instructions.

---

## Traditional Docker Setup (Production Testing)

Use this setup when you need to test the full production environment locally.

## Prerequisites

- **Docker Desktop:** Latest version with Compose V2 enabled.
- **Git:** For cloning the repository.
- **A terminal or command prompt.**

## 1. Clone the Repository

Open your terminal, navigate to the directory where you want to store the project, and run the following command:

```bash
git clone https://github.com/your-username/selextract-cloud.git
cd selextract-cloud
```

## 2. Configure Your Environment

Create a local environment file by copying the example file. This file will store your local configuration and secrets.

```bash
cp .env.example .env
```

The default values in `.env.example` are pre-configured for local development and are designed to work out-of-the-box. You do not need to change any variables to get started.

**Important:** The `.env` file includes all required environment variables including `DATABASE_URL`, `REDIS_URL`, `NEXT_PUBLIC_API_URL`, and service connection details that are automatically configured for the Docker Compose setup.

## 3. Start the Development Environment

Run the following command to build and start all the services in the background:

```bash
docker-compose up -d
```

This command will:
- Build the Docker images for the `api`, `frontend`, and `worker` services.
- Start all services defined in `docker-compose.yml` and `docker-compose.override.yml`.
- Mount your local source code into the running containers, enabling hot-reloading for the API and frontend.
- **Automatically initialize the database** - no manual database setup required!

## 4. Verify System Status

Check that all services are healthy and running:

```bash
# Check container status
docker-compose ps

# Test API health
curl http://localhost:8000/health

# Test frontend health
curl http://localhost:3000/api/health
```

**Expected responses:**
- API Health: `{"status":"healthy",...}` or `{"status":"degraded",...}` (degraded is normal during startup)
- Frontend Health: `{"status":"ok",...}`

## 5. Verify Worker System (✅ Fully Operational)

The Celery worker system is now fully operational. You can verify it's working:

```bash
# Check worker status
docker-compose ps worker

# Verify worker logs show successful startup
docker-compose logs worker | grep -E "(RUNNING|Database is ready|Redis is ready)"

# Test task processing capability
docker-compose exec worker celery -A main inspect active
```

**Expected output indicators:**
- ✅ `celery-worker entered RUNNING state`
- ✅ `celery-beat entered RUNNING state`
- ✅ `Database is ready!`
- ✅ `Redis is ready!`
- ✅ `supervisord started with pid 1`

## 6. Accessing Services

Your local development environment is now ready. You can access the different services at the following URLs:

- **Frontend Application:** [http://localhost:3000](http://localhost:3000)
- **Backend API:** [http://localhost:8000](http://localhost:8000)
- **API Documentation (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **PostgreSQL Database:** `localhost:5432`
- **Redis:** `localhost:6379`
- **Worker Task Queue:** ✅ Operational (4 Celery services running)

## Development Features

Your local setup is configured with the following features to enhance the development experience:

- **Hot Reloading:** Changes made to the source code in the `./api` and `./frontend` directories will automatically trigger a reload of the respective service, so you can see your changes instantly without restarting the containers.
- **Direct Service Access:** All key services are mapped to `localhost` ports for easy access with your preferred tools.
- **Pre-configured Environment:** The default `.env` file provides all necessary configurations for the services to work together locally.

## Stopping the Environment

To stop the local development environment, run:

```bash
docker-compose down
```

This will stop and remove the containers, but your database data will be preserved in a Docker volume. To remove the data volume as well, run `docker-compose down -v`.
