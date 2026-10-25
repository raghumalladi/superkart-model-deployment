#!/usr/bin/env bash
# Build and run the SuperKart backend (Flask) and frontend (Streamlit) as two Docker
# containers on a shared Docker network - the set-up described in the course's
# "Containerized Model Deployment using GitHub Codespaces" hands-on.
#
#   bash run.sh            # build + (re)start both containers
#   bash run.sh logs       # tail the container logs
#   bash run.sh down       # stop and remove both containers
set -euo pipefail
cd "$(dirname "$0")"

NET=superkart-net
case "${1:-up}" in
  down)
    docker rm -f superkart-backend superkart-frontend >/dev/null 2>&1 || true
    echo "containers removed"; exit 0 ;;
  logs)
    docker logs --tail 50 superkart-backend; echo "-----"; docker logs --tail 50 superkart-frontend; exit 0 ;;
esac

docker network inspect "$NET" >/dev/null 2>&1 || docker network create "$NET"
docker rm -f superkart-backend superkart-frontend >/dev/null 2>&1 || true

echo "==> building backend image"
docker build -t superkart-backend ./backend_files
echo "==> building frontend image"
docker build -t superkart-frontend ./frontend_files

echo "==> starting containers"
docker run -d --name superkart-backend  --network "$NET" --network-alias backend -p 7860:7860 superkart-backend
# The frontend reaches the backend through the Docker network name, never through a hard-coded URL
docker run -d --name superkart-frontend --network "$NET" -p 8501:7860 -e BACKEND_URL=http://backend:7860 superkart-frontend

sleep 5
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo
if [ -n "${CODESPACE_NAME:-}" ]; then
  DOMAIN="${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}"
  echo "Backend : https://${CODESPACE_NAME}-7860.${DOMAIN}"
  echo "Frontend: https://${CODESPACE_NAME}-8501.${DOMAIN}"
  if gh codespace ports visibility 7860:public 8501:public -c "$CODESPACE_NAME" 2>/dev/null; then
    echo "Ports 7860 and 8501 set to PUBLIC."
  else
    echo "Open the PORTS tab, right-click ports 7860 and 8501 -> Port Visibility -> Public."
  fi
else
  echo "Backend : http://localhost:7860"
  echo "Frontend: http://localhost:8501"
fi
