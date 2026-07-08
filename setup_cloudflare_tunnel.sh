#!/bin/bash
set -e

# Colors for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🤖 Setting up Fault-Tolerant Local Hosting via Cloudflare Tunnel...${NC}"

# 1. Enable Docker on boot
echo -e "${YELLOW}🐳 Enabling Docker service to auto-start on system boot...${NC}"
sudo systemctl enable docker
sudo systemctl start docker

# 2. Check and install cloudflared
if ! command -v cloudflared &> /dev/null; then
    echo -e "${YELLOW}📦 cloudflared not found. Downloading and installing...${NC}"
    curl -L --output /tmp/cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
    sudo dpkg -i /tmp/cloudflared.deb
    rm /tmp/cloudflared.deb
fi
echo -e "${GREEN}✅ cloudflared is installed successfully!${NC}"

USER_HOME=$(eval echo ~${SUDO_USER:-$(logname)})
rm -f "$USER_HOME/.cloudflared/config.yml" || true

# 3. Cloudflare Authentication
if [ ! -f "$USER_HOME/.cloudflared/cert.pem" ]; then
    echo -e "${YELLOW}🔗 Authenticating cloudflared...${NC}"
    echo -e "${YELLOW}Please copy the URL that appears below, paste it into your browser, and authorize 'ocvrs.in'.${NC}"
    cloudflared tunnel login
else
    echo -e "${GREEN}✅ Already authenticated with Cloudflare!${NC}"
fi

# 4. Create the Tunnel
TUNNEL_NAME="arcare-tunnel"
echo -e "${YELLOW}🚇 Creating Cloudflare Tunnel: ${TUNNEL_NAME}...${NC}"
# Remove existing tunnel if name conflicts
cloudflared tunnel delete -f $TUNNEL_NAME &> /dev/null || true
TUNNEL_INFO=$(cloudflared tunnel create $TUNNEL_NAME)
echo "$TUNNEL_INFO"

# Extract Tunnel ID
TUNNEL_ID=$(echo "$TUNNEL_INFO" | grep -oE "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}" | head -n 1)
if [ -z "$TUNNEL_ID" ]; then
    TUNNEL_ID=$(cloudflared tunnel list | grep "$TUNNEL_NAME" | awk '{print $1}')
fi

if [ -z "$TUNNEL_ID" ]; then
    echo -e "${RED}❌ Failed to extract Tunnel ID. Please run 'cloudflared tunnel create arcare-tunnel' manually.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Tunnel created with ID: ${TUNNEL_ID}${NC}"

# 5. Create config.yml
CONFIG_DIR="$USER_HOME/.cloudflared"
mkdir -p "$CONFIG_DIR"
CONFIG_FILE="$CONFIG_DIR/config.yml"

echo -e "${YELLOW}📝 Writing configuration to ${CONFIG_FILE}...${NC}"
cat <<EOF > "$CONFIG_FILE"
tunnel: $TUNNEL_ID
credentials-file: $CONFIG_DIR/$TUNNEL_ID.json

ingress:
  - hostname: api.prabhash.site
    service: http://localhost:8000
  - service: http_status:404
EOF

# Ensure proper permissions
sudo chown -R ${SUDO_USER:-$(logname)}:${SUDO_USER:-$(logname)} "$CONFIG_DIR"

# 6. Route DNS in Cloudflare
echo -e "${YELLOW}🌐 Creating DNS CNAME record mapping 'api.prabhash.site' to your tunnel...${NC}"
cloudflared tunnel route dns $TUNNEL_NAME api.prabhash.site || echo -e "${YELLOW}⚠️ Could not automatically route DNS (it may already exist or the domain zone is managed elsewhere). Please ensure a CNAME record for 'api' points to '${TUNNEL_ID}.cfargotunnel.com' in your DNS manager.${NC}"


# 7. Install cloudflared as a systemd background service
echo -e "${YELLOW}⚙️ Installing cloudflared as a systemd daemon service...${NC}"
sudo cloudflared service uninstall &> /dev/null || true
sudo rm -f /etc/cloudflared/config.yml
sudo cloudflared --config "$CONFIG_FILE" service install

# Enable and start the systemd service
sudo systemctl daemon-reload
sudo systemctl enable cloudflared
sudo systemctl restart cloudflared

# 8. Run Docker Compose
echo -e "${GREEN}⚡ Starting your API docker containers...${NC}"
if ! docker ps >/dev/null 2>&1; then
    sg docker -c "docker compose up -d --build"
else
    docker compose up -d --build
fi

echo -e "${GREEN}🎉 SYSTEM IS NOW FULLY FAULT-TOLERANT!${NC}"
echo -e "• ${YELLOW}Docker Compose:${NC} set to restart:always; runs automatically on system boot."
echo -e "• ${YELLOW}Cloudflare Tunnel:${NC} installed as systemd service; runs automatically on boot and auto-heals on network dropouts."
echo -e "👉 Your backend is live securely at: ${GREEN}https://api.prabhash.site/docs${NC}"
