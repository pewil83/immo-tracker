# 🏠 Immobilien-Tracker - Hetzner Production Setup

Kompletes System zur automatisierten Überwachung von Immobilienmärkten auf willhaben.at mit Remote-Dashboard.

---

## 📦 Dateien in diesem Paket

### 📋 Setup & Dokumentation

| Datei | Zweck |
|-------|-------|
| **01_HETZNER_SETUP_GUIDE.md** | 🎯 **HAUPTANLEITUNG** - Step-by-Step Hetzner Setup (LIES ZUERST!) |
| **PRODUCTION_HARDWARE_GUIDE.md** | Detaillierte Hardware-Optionen & Deployment-Strategien |
| **README.md** | Diese Datei |

### 🔧 Code-Dateien

| Datei | Zweck | Funktion |
|-------|-------|---------|
| **02_requirements.txt** | Python Dependencies | Alle benötigten Pakete |
| **03_immobilien_scraper.py** | Scraper | Scrape willhaben.at, speichere in DB |
| **04_backend.py** | Flask API | REST-API für Dashboard |
| **05_immobilien_dashboard.jsx** | React UI | Dashboard WebApp (Remote Access) |
| **06_.env.example** | Konfiguration | Kopieren zu `.env` und anpassen |

### 🐳 Optional: Docker

| Datei | Zweck |
|-------|-------|
| **07_docker-compose.yml** | Docker-Orchestration (optional, für später) |
| **08_deploy.sh** | Automatisches Deployment (optional, für später) |

---

## 🚀 Quick Start

### Option A: Manueller Setup (Empfohlen für Anfänger)

1. **Öffne Hetzner Cloud Console**: https://www.hetzner.com/cloud
2. **Erstelle einen CX11 Server** (Ubuntu 24.04 LTS) - €5,89/Monat
3. **Folge der Schritt-für-Schritt Anleitung**: `01_HETZNER_SETUP_GUIDE.md`
4. **Lade Dateien hoch** (03, 04, 05, 06)
5. **Starte Services**: `systemctl start immobilien-api.service`
6. **Öffne Dashboard**: `https://deine-domain.at`

### Option B: Automatisiertes Deployment (Fortgeschritten)

```bash
# SSH zu Hetzner Server
ssh root@your-vps-ip

# Download Deploy-Script
wget https://raw.githubusercontent.com/.../ deploy.sh

# Ausführen
sudo bash deploy.sh
```

---

## 📁 Datei-Struktur auf dem Server

Nach Setup sieht die Struktur so aus:

```
/home/immobilien/
├── immobilien-tracker/
│   ├── venv/                    # Python Virtual Environment
│   ├── app/
│   │   ├── immobilien_scraper.py
│   │   ├── backend.py
│   │   ├── immobilien.db        # SQLite Datenbank
│   │   └── .env                 # Konfiguration (NICHT commiten!)
│   └── backups/                 # Tägliche Backups
├── backup.sh                    # Backup-Script

/etc/systemd/system/
├── immobilien-api.service       # API Service
├── immobilien-scraper.service   # Scraper Service
└── immobilien-scraper.timer     # Timer (täglich 3:00 Uhr)

/etc/nginx/sites-available/
└── immobilien-tracker           # Nginx Reverse Proxy + SSL

```

---

## 🔄 Wie das System funktioniert

```
┌─────────────────────────────────────────┐
│  Browser (dein Computer/Handy)          │
│  https://immobilien-tracker.at          │
└────────────────────┬────────────────────┘
                     │ (HTTPS)
                     ↓
┌─────────────────────────────────────────┐
│  Hetzner VPS (Ubuntu 24.04)             │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │  Nginx Reverse Proxy            │   │
│  │  (SSL/TLS, Port 443)            │   │
│  └────────────────┬────────────────┘   │
│                   │                     │
│  ┌────────────────↓──────────────────┐ │
│  │  Flask API (backend.py)          │ │
│  │  localhost:5000                  │ │
│  │  ┌──────────────────────────────┐│ │
│  │  │ SQLite Datenbank             ││ │
│  │  │ immobilien.db (~ 50MB)       ││ │
│  │  └──────────────────────────────┘│ │
│  └────────────────────────────────────┘ │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │  Cron Job (täglich 03:00 Uhr)   │   │
│  │  → Scraper (immobilien_scraper) │   │
│  │  → Duplikat-Erkennung          │   │
│  │  → Datenbank aktualisiert      │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │  Backup (täglich 02:00 Uhr)     │   │
│  │  → SQL Dump komprimiert         │   │
│  │  → 30 Tage aufbewahrt           │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

---

## 🛠️ Betrieb & Wartung

### Logs anschauen

```bash
# API Logs (live)
journalctl -u immobilien-api.service -f

# Scraper Logs
journalctl -u immobilien-scraper.timer -f

# Alle Logs
journalctl -f
```

### Services neu starten

```bash
sudo systemctl restart immobilien-api.service
sudo systemctl restart immobilien-scraper.timer
```

### Manuelle Scraper-Ausführung

```bash
ssh immobilien@your-vps
cd ~/immobilien-tracker/app
source ../venv/bin/activate
python immobilien_scraper.py --once
```

### Datenbank überprüfen

```bash
sqlite3 ~/immobilien-tracker/app/immobilien.db
> SELECT COUNT(*) FROM immobilien;
> .schema
> .quit
```

---

## 🔍 CSS-Selektoren Update (Falls willhaben.at sich ändert)

willhaben.at ändert manchmal die HTML-Struktur. Dann muss der Scraper angepasst werden:

```python
# In immobilien_scraper.py, Methode _parse_listing()

# Alt:
listings = soup.find_all('div', class_='listing-item')

# Neu (anpassen nach tatsächlichem HTML):
listings = soup.find_all('div', class_='search-result-item')
```

Um die Selektoren zu finden:
1. Gehe zu willhaben.at
2. F12 (Entwickler-Tools)
3. Inspector-Tool (Ctrl+Shift+C)
4. Klick auf ein Listing
5. Kopiere die tatsächliche CSS-Klasse

---

## 🆘 Troubleshooting

### Problem: "Connection refused" auf https://immobilien-tracker.at

**Lösung:**
```bash
# 1. Prüfe ob API läuft
systemctl status immobilien-api.service

# 2. Starte neu
systemctl restart immobilien-api.service

# 3. Check Logs
journalctl -u immobilien-api.service -n 50
```

### Problem: "SSL certificate not found"

**Lösung:**
```bash
# Erneuere Zertifikat
sudo certbot renew --force-renewal

# Starte Nginx
sudo systemctl restart nginx
```

### Problem: Datenbank "database is locked"

**Lösung:**
```bash
# Gehe auf Server
ssh immobilien@server

# Optimiere Datenbank
sqlite3 ~/immobilien-tracker/app/immobilien.db "PRAGMA optimize; VACUUM;"

# Starte API neu
sudo systemctl restart immobilien-api.service
```

### Problem: Scraper lädt 0 Immobilien

**Lösung:**
1. CSS-Selektoren prüfen (siehe oben)
2. willhaben.at manuell besuchen → schauen ob Seite lädt
3. Logs prüfen: `journalctl -u immobilien-scraper.timer -f`

---

## 📊 Performance & Monitoring

### System-Resources prüfen

```bash
# CPU/Memory/Disk
htop
df -h
free -h

# Top Prozesse
ps aux --sort=-%cpu | head -5
```

### API Response Time

```bash
curl -w "@curl-format.txt" -o /dev/null -s https://immobilien-tracker.at/api/stats
```

### Uptime überprüfen

```bash
# Hetzner Cloud Console → Server → Metrics
# ODER lokal:
systemctl status immobilien-api.service
```

---

## 🔐 Sicherheit

### SSH Key-basiert authentifizieren (nicht Passwort!)

✅ Setup nutzt SSH Keys
✅ Firewall nur nötige Ports offen (22, 80, 443)
✅ Fail2ban schützt vor Brute-Force
✅ HTTPS/TLS erzwingt verschlüsselte Verbindung
✅ Keine Secrets in Code (nutze `.env`)

### Recommended: Zusätzlich absichern

```bash
# SSH Passwort-Login deaktivieren
sudo nano /etc/ssh/sshd_config
# Suche: PasswordAuthentication yes
# Ändere zu: PasswordAuthentication no
# Speichern & reload
sudo systemctl reload sshd
```

---

## 💰 Kosten

| Posten | Kosten | Anmerkung |
|--------|--------|----------|
| Hetzner CX11 | €5,89/Monat | Included: 25GB SSD, 2 vCPU, 1GB RAM |
| Domain (optional) | €10/Jahr | z.B. .at Domain |
| SSL (Let's Encrypt) | €0 | Kostenlos, auto-renew |
| **GESAMT** | **€6/Monat** | **€72/Jahr** |

---

## 📞 Support

Falls etwas nicht funktioniert:

1. **Logs überprüfen**: `journalctl -u immobilien-api.service`
2. **Server-Health**: `curl https://deine-domain.at/health`
3. **API-Test**: `curl https://deine-domain.at/api/stats`
4. **Firewall**: `ufw status`

---

## 📝 Lizenz

Dieses Projekt ist für persönliche Nutzung vorgesehen.

---

**Viel Erfolg beim Setup! 🚀**
