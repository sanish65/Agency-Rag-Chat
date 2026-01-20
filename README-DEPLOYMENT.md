# RAG Chat Application - Deployment Guide

This guide provides comprehensive instructions for deploying the RAG Chat application using Docker on any device.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Setup](#detailed-setup)
- [Running on Other Devices](#running-on-other-devices)
- [Environment Variables](#environment-variables)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software

1. **Docker** (version 20.10 or higher)
   - Linux: `sudo apt-get install docker.io docker-compose`
   - macOS: [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)
   - Windows: [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)

2. **Docker Compose** (usually included with Docker Desktop)
   - Verify: `docker-compose --version`

### Required Credentials

1. **Google API Key** (for Generative AI)
   - Get it from: [Google AI Studio](https://makersuite.google.com/app/apikey)
   
2. **Google Cloud Service Account** (for BigQuery access)
   - Follow the [Service Account Setup](#google-cloud-service-account-setup) section below

## Quick Start

```bash
# 1. Clone or navigate to the project directory
cd /path/to/rag-chat

# 2. Create credentials directory
mkdir -p credentials

# 3. Copy your Google Cloud service account JSON file
cp /path/to/your-service-account.json credentials/gcp-credentials.json

# 4. Create .env file from template
cp .env.example .env

# 5. Edit .env and add your Google API key
nano .env  # or use any text editor

# 6. Build and start the application
docker-compose up -d

# 7. Check logs
docker-compose logs -f

# 8. Access the application
# Open browser: http://localhost:5001
```

## Detailed Setup

### Google Cloud Service Account Setup

1. **Go to Google Cloud Console**
   - Visit: https://console.cloud.google.com/

2. **Select or Create a Project**
   - Use project: `expert-hackathon-2026` (or your project)

3. **Create Service Account**
   - Navigate to: IAM & Admin → Service Accounts
   - Click "Create Service Account"
   - Name: `rag-chat-service-account`
   - Description: "Service account for RAG chat application"

4. **Grant Permissions**
   - Add role: `BigQuery Data Viewer`
   - Add role: `BigQuery Job User`
   - Click "Continue" and "Done"

5. **Create and Download Key**
   - Click on the created service account
   - Go to "Keys" tab
   - Click "Add Key" → "Create new key"
   - Choose "JSON" format
   - Download the JSON file

6. **Place the Key File**
   ```bash
   mkdir -p credentials
   mv ~/Downloads/your-project-xxxxx.json credentials/gcp-credentials.json
   ```

### Environment Configuration

1. **Create .env file**
   ```bash
   cp .env.example .env
   ```

2. **Edit .env file**
   ```bash
   nano .env
   ```

3. **Add your credentials**
   ```env
   GOOGLE_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
   ```

### Building and Running

#### Option 1: Using Docker Compose (Recommended)

```bash
# Build and start in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the application
docker-compose down

# Rebuild after code changes
docker-compose up -d --build
```

#### Option 2: Using Docker CLI

```bash
# Build the image
docker build -t rag-chat:latest .

# Run the container
docker run -d \
  --name rag-chat-app \
  -p 5001:5001 \
  -e GOOGLE_API_KEY="your_api_key_here" \
  -e GOOGLE_CLOUD_PROJECT="expert-hackathon-2026" \
  -e GOOGLE_APPLICATION_CREDENTIALS="/app/credentials/gcp-credentials.json" \
  -v $(pwd)/credentials:/app/credentials:ro \
  -v $(pwd)/document_vectors:/app/document_vectors \
  -v $(pwd)/chroma_db:/app/chroma_db \
  -v $(pwd)/embeddings_store:/app/embeddings_store \
  rag-chat:latest

# View logs
docker logs -f rag-chat-app

# Stop and remove
docker stop rag-chat-app
docker rm rag-chat-app
```

## Running on Other Devices

### Method 1: Share Docker Image

1. **On your current device, save the image**
   ```bash
   docker save rag-chat:latest | gzip > rag-chat-image.tar.gz
   ```

2. **Transfer the file to another device**
   - Use USB drive, cloud storage, or network transfer
   - File size: ~1-2 GB (compressed)

3. **On the target device, load the image**
   ```bash
   docker load < rag-chat-image.tar.gz
   ```

4. **Copy project files**
   - Transfer the entire project directory OR
   - Just copy: `docker-compose.yml`, `.env`, and `credentials/` folder

5. **Run on the new device**
   ```bash
   docker-compose up -d
   ```

### Method 2: Use Docker Registry (Advanced)

1. **Push to Docker Hub**
   ```bash
   docker tag rag-chat:latest yourusername/rag-chat:latest
   docker push yourusername/rag-chat:latest
   ```

2. **On other devices, pull and run**
   ```bash
   docker pull yourusername/rag-chat:latest
   docker-compose up -d
   ```

### Method 3: Git Repository

1. **Commit Docker files to Git** (excluding .env and credentials)
   ```bash
   git add Dockerfile docker-compose.yml .dockerignore .env.example
   git commit -m "Add Docker configuration"
   git push
   ```

2. **On other devices**
   ```bash
   git clone <your-repo-url>
   cd rag-chat
   mkdir credentials
   # Copy your credentials file
   cp .env.example .env
   # Edit .env with your API key
   docker-compose up -d
   ```

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `GOOGLE_API_KEY` | Google Generative AI API key | Yes | - |
| `GOOGLE_CLOUD_PROJECT` | GCP Project ID | Yes | expert-hackathon-2026 |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON | Yes | /app/credentials/gcp-credentials.json |

## Accessing the Application

Once running, access the application at:
- **Local**: http://localhost:5001
- **Network**: http://YOUR_IP_ADDRESS:5001

To find your IP address:
```bash
# Linux/Mac
hostname -I | awk '{print $1}'

# Windows (PowerShell)
(Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -notlike "*Loopback*"}).IPAddress
```

## Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs

# Common issues:
# 1. Missing credentials file
ls -la credentials/gcp-credentials.json

# 2. Invalid .env file
cat .env

# 3. Port already in use
sudo lsof -i :5001
# or change port in docker-compose.yml
```

### BigQuery connection errors

```bash
# Verify credentials are mounted
docker-compose exec rag-chat ls -la /app/credentials/

# Check environment variables
docker-compose exec rag-chat env | grep GOOGLE

# Test BigQuery connection
docker-compose exec rag-chat python -c "from google.cloud import bigquery; client = bigquery.Client(); print('Connection successful')"
```

### Permission errors

```bash
# Fix volume permissions
sudo chown -R $USER:$USER document_vectors chroma_db embeddings_store

# Or run with proper user
docker-compose exec --user $(id -u):$(id -g) rag-chat bash
```

### Rebuilding after changes

```bash
# Stop and remove containers
docker-compose down

# Rebuild with no cache
docker-compose build --no-cache

# Start fresh
docker-compose up -d
```

### View application logs

```bash
# All logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100

# Specific service
docker-compose logs -f rag-chat
```

## Data Persistence

The following directories are mounted as volumes and persist data:
- `document_vectors/` - FAISS vector embeddings
- `chroma_db/` - ChromaDB database
- `embeddings_store/` - Additional embeddings

To reset data:
```bash
docker-compose down
rm -rf document_vectors chroma_db embeddings_store
docker-compose up -d
```

## Security Notes

⚠️ **Important Security Considerations:**

1. **Never commit `.env` or credentials to Git**
   - These files are in `.gitignore`
   - Always use `.env.example` as template

2. **Protect your service account key**
   - Store `credentials/gcp-credentials.json` securely
   - Use appropriate file permissions: `chmod 600 credentials/gcp-credentials.json`

3. **Use environment-specific credentials**
   - Different credentials for dev/staging/production
   - Rotate keys regularly

4. **Network security**
   - For production, use HTTPS/TLS
   - Consider using a reverse proxy (nginx, Traefik)
   - Implement proper authentication

## Production Deployment

For production environments, consider:

1. **Use a production WSGI server** (instead of Flask's dev server)
   - Modify Dockerfile CMD to use Gunicorn:
   ```dockerfile
   CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5001", "app:app"]
   ```

2. **Add health monitoring**
   - The docker-compose.yml includes a basic health check
   - Consider adding Prometheus/Grafana for metrics

3. **Use secrets management**
   - Docker Swarm secrets
   - Kubernetes secrets
   - HashiCorp Vault

4. **Set resource limits**
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '2'
         memory: 4G
   ```

## Support

For issues or questions:
1. Check the logs: `docker-compose logs -f`
2. Verify credentials and environment variables
3. Ensure all prerequisites are installed
4. Check Docker and Docker Compose versions

---

**Last Updated**: January 2026
