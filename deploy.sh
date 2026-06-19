#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Whenever need to deploy new code, simply run ./deploy.sh.
echo "🚀 Starting Deployment..."

# 0. Update the local index with the latest changes
git fetch origin main

# 1. Force the local files to match the remote version exactly (ignores local changes)
# It pulls code and builds the new image in the background. Nginx is still serving users on the old code.
echo "📦 Pulling latest code..."
git reset --hard origin/main

# It spins up the temporary migrations container, updates the database schema, and gracefully shuts down.
# 2 and 3 are done in the background while Nginx is still serving users on the old code.

# 2. Build the new Docker images (this downloads packages, updates code in the container)
# Database and Redis remain online, serving users via the old web container.
echo "🏗️ Building new images..."
docker compose build web migrations

# 3. Run Migrations & Collect Static safely
# The isolated migrations container spins up, safely updates the database, updates the static files, and self-destructs (--rm).
echo "🗄️ Running migrations..."
docker compose run --rm migrations

# 4. Before rolling out the new images/containers, download the plugin
# mkdir -p ~/.docker/cli-plugins
# curl -L -o ~/.docker/cli-plugins/docker-rollout https://raw.githubusercontent.com/wowu/docker-rollout/master/docker-rollout

# Make it executable
# chmod +x ~/.docker/cli-plugins/docker-rollout

# 4.1. Perform the Zero-Downtime Rolling Update
# docker-rollout spins up a new web container. It waits until the curl health check passes.
# Since it doesn't have to run migrations, Gunicorn turns on instantly.
echo "🔄 Rolling out new web containers..."
docker rollout -f docker-compose.prod.yml web

# 5. Clean up old dangling images to save disk space
# Once Nginx can see the new container is healthy, Docker gracefully terminates the old web container.
echo "🧹 Cleaning up old images..."
docker image prune -f

echo "✅ Deployment Successful!"
