#!/bin/bash
# Immobilien-Tracker: Hetzner Deployment Script
# Verwendung: bash deploy.sh

set -e

echo "=================================================="
echo "🚀 Immobilien-Tracker Hetzner Deployment"
echo "=================================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Checks
if [ "$EUID" -ne 0 ]; then 
   echo -e "${RED}❌ Dieses Script muss als root ausgeführt werden${NC}"
   echo "Verwende: sudo bash deploy.sh"
   exit 1
fi

# 1. System Update
echo -e "${YELLOW}1️⃣ Aktualisiere System...${NC}"
apt update && apt upgrade -y
apt install -y git curl wget htop tmux ufw fail2ban sqlite3
echo -e "${GREEN}✅ System aktualisiert${NC}"

# 2. Firewall
echo -e "${YELLOW}2️⃣ Konfiguriere Firewall...${NC}"
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
ufw status
echo -e "${GREEN}✅ Firewall konfiguriert${NC}"

# 3. Swap
echo -e "${YELLOW}3️⃣ Richte Swap ein...${NC}"
fallocate -l 1G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
echo -e "${GREEN}✅ Swap eingerichtet${NC}"

# 4. App User
echo -e "${YELLOW}4️⃣ Erstelle App-Benutzer...${NC}"
useradd -m -s /bin/bash immobilien || echo "User existiert bereits"
echo -e "${GREEN}✅ App-Benutzer bereit${NC}"

# 5. Python Environment
echo -e "${YELLOW}5️⃣ Richte Python-Umgebung ein...${NC}"
su - immobilien -c '
  mkdir -p ~/immobilien-tracker/app
  cd ~/immobilien-tracker
  python3 -m venv venv
  source venv/bin/activate
  pip install --upgrade pip
  pip install requests beautifulsoup4 flask flask-cors apscheduler python-dotenv
'
echo -e "${GREEN}✅ Python venv bereit${NC}"

# 6. Code Upload (benutzer muss selbst hochladen via scp)
echo -e "${YELLOW}6️⃣ Code Upload${NC}"
echo "ℹ️  Bitte lade die Dateien selbst hoch:"
echo "   scp -i your-key immobilien_scraper.py immobilien@server:~/immobilien-tracker/app/"
echo "   scp -i your-key backend.py immobilien@server:~/immobilien-tracker/app/"
echo "   scp -i your-key .env immobilien@server:~/immobilien-tracker/app/"
read -p "Drücke Enter wenn Upload komplett..."

# 7. Systemd Services
echo -e "${YELLOW}7️⃣ Installiere Systemd Services...${NC}"

cat > /etc/systemd/system/immobilien-scraper.service << 'EOF'
[Unit]
Description=Immobilien Tracker Scraper
After=network.target
Wants=immobilien-scraper.timer

[Service]
Type=simple
User=immobilien
WorkingDirectory=/home/immobilien/immobilien-tracker/app
ExecStart=/home/immobilien/immobilien-tracker/venv/bin/python immobilien_scraper.py --once
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/immobilien-scraper.timer << 'EOF'
[Unit]
Description=Run Immobilien Scraper Daily
Requires=immobilien-scraper.service

[Timer]
OnCalendar=*-*-* 03:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

cat > /etc/systemd/system/immobilien-api.service << 'EOF'
[Unit]
Description=Immobilien Tracker API
After=network.target

[Service]
Type=simple
User=immobilien
WorkingDirectory=/home/immobilien/immobilien-tracker/app
ExecStart=/home/immobilien/immobilien-tracker/venv/bin/python backend.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment="FLASK_ENV=production"

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable immobilien-scraper.timer immobilien-api.service
systemctl start immobilien-api.service
systemctl start immobilien-scraper.timer

echo -e "${GREEN}✅ Services installiert${NC}"

# 8. Nginx + SSL
echo -e "${YELLOW}8️⃣ Konfiguriere Nginx...${NC}"

apt install -y nginx certbot python3-certbot-nginx

read -p "Gib deine Domain ein (z.B. immobilien-tracker.at): " DOMAIN

cat > /etc/nginx/sites-available/immobilien-tracker << EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN www.$DOMAIN;

    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

ln -sf /etc/nginx/sites-available/immobilien-tracker /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx

# SSL Cert
certbot certonly --nginx -d $DOMAIN -d www.$DOMAIN --agree-tos --non-interactive --email admin@example.com
systemctl restart nginx

echo -e "${GREEN}✅ Nginx konfiguriert${NC}"

# 9. Backup Script
echo -e "${YELLOW}9️⃣ Richte Backups ein...${NC}"

cat > /home/immobilien/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/immobilien/backups"
DB_FILE="/home/immobilien/immobilien-tracker/app/immobilien.db"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
sqlite3 $DB_FILE ".dump" | gzip > $BACKUP_DIR/immobilien_${DATE}.sql.gz
find $BACKUP_DIR -mtime +30 -delete
echo "[$(date)] Backup erstellt"
EOF

chmod +x /home/immobilien/backup.sh
chown immobilien:immobilien /home/immobilien/backup.sh

echo "0 2 * * * /home/immobilien/backup.sh >> /tmp/backup.log 2>&1" | crontab -u immobilien -

echo -e "${GREEN}✅ Backups eingerichtet${NC}"

# Final
echo ""
echo -e "${GREEN}=================================================="
echo "✅ DEPLOYMENT KOMPLETT!"
echo "=================================================="
echo ""
echo "🎉 Dein System läuft jetzt:"
echo "   Dashboard: https://$DOMAIN"
echo "   API: https://$DOMAIN/api/stats"
echo ""
echo "📋 Nächste Schritte:"
echo "   1. Öffne https://$DOMAIN im Browser"
echo "   2. Überprüfe: journalctl -u immobilien-api.service -f"
echo "   3. Warte auf nächsten Scrape (morgen 03:00 Uhr)"
echo ""
echo "❓ Hilfe:"
echo "   - API Status: curl https://$DOMAIN/api/stats"
echo "   - API Logs: journalctl -u immobilien-api.service"
echo "   - Scraper Logs: journalctl -u immobilien-scraper.timer"
echo ""
