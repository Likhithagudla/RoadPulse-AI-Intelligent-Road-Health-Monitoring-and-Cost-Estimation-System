# 🚀 RoadPulse AI – Production Deployment Guide

This guide covers deployment procedures for **RoadPulse AI** across local workstations, cloud virtual machines (Ubuntu / Debian / RHEL), and containerized Docker environments.

---

## 1. System Requirements

### Hardware
* **CPU:** Minimum 2 cores (4+ cores recommended for video batch processing)
* **RAM:** Minimum 4 GB (8 GB recommended for YOLOv8 model loading & OpenCV frames)
* **Disk:** 5 GB free storage (SSD recommended for model checkpoints and video buffers)
* **GPU (Optional):** NVIDIA GPU with CUDA 11.8+ / 12.1+ for accelerated batch inference

### Operating Systems
* **Linux:** Ubuntu 22.04 LTS / 24.04 LTS, Debian 12, RHEL 9
* **Windows:** Windows 10 / 11 (64-bit), Windows Server 2022
* **macOS:** Apple Silicon (M1/M2/M3) or Intel with macOS 13+

---

## 2. Environment Configuration

1. Clone the repository and navigate into the project directory:
   ```bash
   git clone <repository_url>
   cd Road_AI_Project_Final
   ```

2. Copy the template configuration file:
   ```bash
   cp .env.example .env
   ```

3. Configure security credentials in `.env`:
   ```ini
   # Generate a 64-character secret with: openssl rand -hex 32
   SECRET_KEY=your_generated_cryptographic_secret_key_here
   ENVIRONMENT=production
   DEBUG=false
   DATABASE_URL=sqlite:///./road_ai.db
   # Or for PostgreSQL:
   # DATABASE_URL=postgresql://road_user:road_password@postgres_host:5432/roadpulse_db
   ```

> [!WARNING]
> Never commit `.env` or hardcode secrets into the codebase. Ensure `.env` is listed in `.gitignore`.

---

## 3. Deployment Method A: Docker Compose (Recommended)

Docker Compose provisions the complete stack (FastAPI backend, static web dashboard, and optional PostgreSQL) inside an isolated container with health monitoring.

### Step 1: Build and Launch
```bash
docker compose up -d --build
```

### Step 2: Verify Health Status
```bash
# Check container status
docker compose ps

# Probe standard health check endpoint
curl -f http://localhost:8000/health
```
Expected output:
```json
{
  "status": "healthy",
  "service": "RoadPulse AI",
  "version": "2.0.0",
  "environment": "production"
}
```

### Step 3: View Application Logs
```bash
docker compose logs -f api
```

### Step 4: Access Web Services
* **Interactive Dashboard:** `http://localhost:8000/dashboard/`
* **Swagger API Docs:** `http://localhost:8000/docs`
* **Health Endpoint:** `http://localhost:8000/health`

---

## 4. Deployment Method B: Native Linux / Ubuntu Deployment

### Step 1: Install System Dependencies
```bash
sudo apt-get update && sudo apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    libgl1 \
    libglib2.0-0 \
    curl \
    git
```

### Step 2: Create Python Virtual Environment
```bash
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Run Database Migrations & Initial Seeding
```bash
cd backend
alembic upgrade head
python seed_user.py
cd ..
```

### Step 4: Configure Systemd Service
Create `/etc/systemd/system/roadpulse.service`:
```ini
[Unit]
Description=RoadPulse AI FastAPI Service
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/roadpulse/backend
EnvironmentFile=/opt/roadpulse/.env
ExecStart=/opt/roadpulse/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now roadpulse
```

---

## 5. Nginx Reverse Proxy Configuration (HTTPS / SSL)

Create `/etc/nginx/sites-available/roadpulse`:
```nginx
server {
    listen 80;
    server_name roadpulse.yourdomain.com;
    client_max_body_size 100M;  # Allow video uploads

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
Link and reload:
```bash
sudo ln -s /etc/nginx/sites-available/roadpulse /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```
Obtain SSL certificates via Certbot:
```bash
sudo certbot --nginx -d roadpulse.yourdomain.com
```

---

## 6. Verification Checklist
- [ ] `GET /health` returns HTTP 200 with `status: "healthy"`.
- [ ] `GET /api/status` confirms YOLOv8 model weights loaded and geometry calibrated.
- [ ] `POST /api/auth/login` issues signed JWT tokens for seeded admin account.
- [ ] Rate limiter throttles consecutive failed login attempts (5 attempts / 60 seconds).
- [ ] Background uploads directory `/uploads` has write permissions.
