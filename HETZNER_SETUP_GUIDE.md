# 🚀 Hetzner VPS Setup - Schritt-für-Schritt Anleitung

## Phase 1: Hetzner Cloud Vorbereitung (10 Minuten)

### Schritt 1: Konto erstellen

1. Gehe zu https://www.hetzner.com/cloud
2. Klick **"Sign up"**
3. Registriere mit E-Mail & Passwort
4. Bestätige E-Mail
5. Zahlungsart hinzufügen (Kreditkarte oder SEPA)

### Schritt 2: Server erstellen

1. Gehe in **Cloud Console**
2. Klick **"Create Server"** (Button oben)
3. Wähle folgende Einstellungen:

**Location:** 
- ✅ **Falkenstein** (kostenlos, EU-Standard)

**Image:**
- ✅ **Ubuntu 24.04 LTS**

**Type:**
- ✅ **Shared CPU** (nicht Dedicated)
- ✅ **CX11** (2 vCPU, 1GB RAM, 25GB NVMe)
- Kosten: €5,89/Monat

**SSH Key** (WICHTIG!):
- Klick **"Add SSH Key"**
- Öffne Terminal auf DEINEM Computer:
  ```bash
  ssh-keygen -t ed25519 -f ~/.ssh/hetzner_immobilien -C "immobilien@hetzner"
  # Drücke 2x Enter (kein Passwort)
  ```
- Kopiere Output von:
  ```bash
  cat ~/.ssh/hetzner_immobilien.pub
  ```
- Füge in Hetzner ein und klick **"Add SSH Key"**
- Bestätige mit Namen z.B. "immobilien-tracker"

**Naming:**
- Name: `immobilien-tracker`

**Klick "Create & Buy now"** → Server wird in 1 Minute erstellt

### Schritt 3: IP-Adresse notieren

Nach dem Server-Start siehst du:
- **IPv4:** z.B. `1.2.3.4` ← WICHTIG NOTIEREN!
- **Hostname:** z.B. `immobilien-tracker`

---

## Phase 2: Server-Konfiguration (5 Minuten)

Öffne Terminal auf DEINEM Computer:

### Schritt 4: Erste SSH-Verbindung

```bash
# Verbinde mit Server
ssh -i ~/.ssh/hetzner_immobilien root@1.2.3.4
# (ersetze 1.2.3.4 mit deiner echten IP)

# Solltest du sehen:
# Welcome to Ubuntu 24.04 LTS

# Bestätige: yes
# Fertig!
```

### Schritt 5: System-Update (läuft im Hintergrund, ca. 2-3 Min)

```bash
# Du bist jetzt ON dem Server!

apt update && apt upgrade -y
apt install -y git curl wget htop tmux ufw fail2ban

echo "✅ System aktualisiert"
```

### Schritt 6: Firewall konfigurieren

```bash
ufw default deny incoming
ufw default allow outgoing

ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS

ufw enable
ufw status
# Sollte zeigen: Status: active

echo "✅ Firewall aktiviert"
```

### Schritt 7: Swap einrichten (für 1GB RAM Sicherheit)

```bash
fallocate -l 1G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

free -h
# Sollte Swap zeigen

echo "✅ Swap konfiguriert"
```

---

## Phase 3: Applikation deployen (10 Minuten)

### Schritt 8: App-Benutzer erstellen

```bash
# Neue User erstellen
useradd -m -s /bin/bash immobilien
usermod -aG sudo immobilien

# Wechsel zu neuem User
su - immobilien
pwd
# Sollte zeigen: /home/immobilien

echo "✅ App-Benutzer erstellt"
```

### Schritt 9: Python-Umgebung

```bash
# Du bist jetzt als 'immobilien' angemeldet!

# Python venv
python3 -m venv ~/immobilien-tracker/venv
source ~/immobilien-tracker/venv/bin/activate

# Dependencies installieren
pip install --upgrade pip
pip install requests beautifulsoup4 flask flask-cors apscheduler python-dotenv

echo "✅ Python venv bereit"
```

### Schritt 10: Code von deinem Computer hochladen

**NEUES TERMINAL öffnen** (nicht auf Server, auf DEINEM Computer):

```bash
# Du bist wieder lokal!

# Gehe zu deinem Projekt-Verzeichnis
cd ~/dein-projekt-pfad

# Erstelle TAR-Archiv mit allen Dateien
tar -czf immobilien-tracker.tar.gz \
  immobilien_scraper.py \
  backend.py \
  immobilien_dashboard.jsx \
  requirements.txt \
  .env

# Upload zu Server
scp -i ~/.ssh/hetzner_immobilien \
    immobilien-tracker.tar.gz \
    immobilien@1.2.3.4:~/

echo "✅ Code hochgeladen"
```

### Schritt 11: Code auf Server entpacken

**ZURÜCK zum Server-Terminal**:

```bash
# Du bist immobilien@hetzner

cd ~
tar -xzf immobilien-tracker.tar.gz

ls -la
# Sollte zeigen: immobilien_scraper.py, backend.py, etc.

# Dateien in richtige Verzeichnis-Struktur verschieben
mkdir -p ~/immobilien-tracker/app
mv immobilien_scraper.py ~/immobilien-tracker/app/
mv backend.py ~/immobilien-tracker/app/
mv immobilien_dashboard.jsx ~/immobilien-tracker/app/
mv .env ~/immobilien-tracker/app/

cd ~/immobilien-tracker/app

# .env konfigurieren (für Production)
cat .env
# WICHTIG: Falls deine Domain nicht drin ist, editieren:
nano .env
# DOMAIN=immobilien-tracker.at (oder deine Domain)
# Speichern: Ctrl+X → Y → Enter

echo "✅ Code entpackt"
```

---

## Phase 4: Systemd Services (3 Minuten)

### Schritt 12: API Service einrichten

**Noch als immobilien@hetzner, aber brauchen sudo:**

```bash
# Wechsel zu root
sudo su

# Scraper Service
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

# Scraper Timer (täglich 3:00 Uhr)
cat > /etc/systemd/system/immobilien-scraper.timer << 'EOF'
[Unit]
Description=Run Immobilien Scraper Daily at 3 AM
Requires=immobilien-scraper.service

[Timer]
OnCalendar=daily
OnCalendar=*-*-* 03:00:00

[Install]
WantedBy=timers.target
EOF

# API Service
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

# Aktiviere & starte Services
systemctl daemon-reload
systemctl enable immobilien-scraper.timer immobilien-api.service
systemctl start immobilien-api.service
systemctl start immobilien-scraper.timer

# Prüfe Status
systemctl status immobilien-api.service
systemctl status immobilien-scraper.timer

echo "✅ Services konfiguriert"
```

### Schritt 13: Test der API

```bash
# Als root noch:
curl -s http://localhost:5000/api/stats | python3 -m json.tool
# Sollte JSON zeigen mit Stats

echo "✅ API läuft!"
```

---

## Phase 5: HTTPS + Reverse Proxy (5 Minuten)

### Schritt 14: Domain vorbereiten

**In deinem Domain-Registrar** (nicht Hetzner):

Erstelle **A-Record**:
```
Name:   immobilien-tracker
Type:   A
Value:  1.2.3.4  (deine Hetzner IP)
TTL:    3600
```

Warte 5-15 Minuten bis DNS propagiert.

**Test ob Domain funktioniert:**
```bash
# Lokal auf DEINEM Computer:
ping immobilien-tracker.at
# Sollte deine Hetzner IP zeigen
```

### Schritt 15: Nginx + SSL Setup

```bash
# Noch als root auf Server:

apt install -y nginx certbot python3-certbot-nginx

# Nginx Config erstellen
cat > /etc/nginx/sites-available/immobilien-tracker << 'EOF'
server {
    listen 80;
    server_name immobilien-tracker.at www.immobilien-tracker.at;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name immobilien-tracker.at www.immobilien-tracker.at;

    ssl_certificate /etc/letsencrypt/live/immobilien-tracker.at/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/immobilien-tracker.at/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        
        # WebSocket Support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Aktiviere Nginx Config
ln -s /etc/nginx/sites-available/immobilien-tracker /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx

echo "✅ Nginx konfiguriert (HTTP läuft)"
```

### Schritt 16: SSL-Zertifikat mit Let's Encrypt

```bash
# Noch als root:

certbot certonly --nginx -d immobilien-tracker.at -d www.immobilien-tracker.at

# Antworte auf Fragen:
# Email: deine@email.com
# Agree terms: Y
# Subscribe: N (optional)

# Test:
certbot renew --dry-run

# Auto-Renewal aktivieren
systemctl enable certbot.timer

# Nginx neustarten
systemctl restart nginx

echo "✅ HTTPS aktiv!"
```

---

## Phase 6: Backup-Automation (2 Minuten)

### Schritt 17: Tägliche Backups einrichten

```bash
# Noch als root:

# Backup-Script
cat > /home/immobilien/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/immobilien/backups"
DB_FILE="/home/immobilien/immobilien-tracker/app/immobilien.db"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Datenbank-Dump
sqlite3 $DB_FILE ".dump" | gzip > $BACKUP_DIR/immobilien_${DATE}.sql.gz

# Behalte nur letzte 30 Tage
find $BACKUP_DIR -mtime +30 -delete

echo "[$(date)] Backup erstellt: immobilien_${DATE}.sql.gz"
EOF

chmod +x /home/immobilien/backup.sh
chown immobilien:immobilien /home/immobilien/backup.sh

# Cron Job
echo "0 2 * * * /home/immobilien/backup.sh >> /tmp/backup.log 2>&1" | \
  crontab -u immobilien -

echo "✅ Backups konfiguriert (täglich 2 Uhr)"
```

---

## Phase 7: Überprüfung (5 Minuten)

### Schritt 18: Tests durchführen

```bash
# Auf deinem lokalen Computer:

# 1. Teste HTTP → HTTPS Redirect
curl -I http://immobilien-tracker.at
# Sollte 301 zeigen

# 2. Teste HTTPS
curl -s https://immobilien-tracker.at/api/stats | python3 -m json.tool
# Sollte JSON zeigen

# 3. Öffne im Browser
# https://immobilien-tracker.at
# Sollte Dashboard anzeigen

echo "✅ System läuft!"
```

### Schritt 19: Logs überprüfen

```bash
# SSH zu Server
ssh -i ~/.ssh/hetzner_immobilien immobilien@1.2.3.4

# API Logs
journalctl -u immobilien-api.service -n 50 -f

# Scraper Logs
journalctl -u immobilien-scraper.timer -n 50

# System
htop
# Schaue nach CPU/RAM
```

---

## Phase 8: Ongoing Maintenance

### Monitoring einrichten

```bash
# Log-Rotationscripte einrichten (falls nötig)
# und regelmäßig Backups prüfen

# Wöchentlicher Check (optional, in Crontab)
# 0 9 * * 0 curl -s https://immobilien-tracker.at/api/stats
```

### CSS-Selektoren updaten

Falls willhaben.at die Seite ändert:

```bash
# SSH auf Server
ssh -i ~/.ssh/hetzner_immobilien immobilien@1.2.3.4

# Scraper Code editieren
cd ~/immobilien-tracker/app
nano immobilien_scraper.py
# Update CSS-Selektoren
# Ctrl+X → Y → Enter

# Manueller Test
python immobilien_scraper.py --once
```

---

## 🎉 Fertig!

Dein System läuft jetzt:

| Komponente | Status | URL |
|-----------|--------|-----|
| Dashboard | ✅ Online | https://immobilien-tracker.at |
| API | ✅ Online | https://immobilien-tracker.at/api |
| Scraper | ✅ Geplant | Täglich 03:00 Uhr |
| Datenbank | ✅ Läuft | SQLite (lokal) |
| Backups | ✅ Automatisch | Täglich 02:00 Uhr |

---

## 📞 Falls etwas nicht funktioniert:

### SSH-Fehler "Permission denied"
```bash
# Rechte prüfen
ls -la ~/.ssh/hetzner_immobilien
chmod 600 ~/.ssh/hetzner_immobilien

# Oder neue Key generieren
ssh-keygen -t ed25519 -f ~/.ssh/hetzner_immobilien
# Dann Key in Hetzner Console hinzufügen
```

### API läuft nicht
```bash
ssh -i ~/.ssh/hetzner_immobilien immobilien@1.2.3.4
sudo systemctl restart immobilien-api.service
sudo journalctl -u immobilien-api.service -n 100
```

### HTTPS funktioniert nicht
```bash
sudo certbot renew --force-renewal
sudo systemctl restart nginx
```

### Datenbank leer
```bash
cd ~/immobilien-tracker/app
python immobilien_scraper.py --once
# Schau in /tmp/immobilien.log
```

---

**Viel Erfolg! 🚀**
