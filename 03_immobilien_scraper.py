#!/usr/bin/env python3
"""
Immobilien-Tracker Scraper für Hetzner Production
Scraper für willhaben.at mit Duplikat-Erkennung und Datenbankpersistenz
"""

import sqlite3
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import logging
import sys
from typing import List, Dict, Tuple
import re

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/immobilien.log')
    ]
)
logger = logging.getLogger(__name__)

class ImmobilienScraper:
    def __init__(self, db_path: str = "immobilien.db"):
        self.db_path = db_path
        self.base_url = "https://www.willhaben.at"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'de-AT,de;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
        }
        self.session = requests.Session()
        self.init_database()
    
    def init_database(self):
        """Initialisiere SQLite Datenbank"""
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA cache_size=-64000")
        conn.execute("PRAGMA synchronous=NORMAL")
        
        c = conn.cursor()
        
        # Haupttabelle
        c.execute('''
            CREATE TABLE IF NOT EXISTS immobilien (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                willhaben_id TEXT UNIQUE,
                titel TEXT,
                preis REAL,
                adresse TEXT,
                bezirk TEXT,
                flaeche REAL,
                zimmer REAL,
                objekttyp TEXT,
                url TEXT,
                bilder_count INTEGER,
                makler_name TEXT,
                erstellt_am TIMESTAMP,
                aktualisiert_am TIMESTAMP,
                gescraped_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'aktiv'
            )
        ''')
        
        # Duplikat-Tracking
        c.execute('''
            CREATE TABLE IF NOT EXISTS duplikate (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                haupt_id INTEGER,
                duplikat_id INTEGER,
                aehnlichkeitsgrad REAL,
                erkannt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                gruende TEXT,
                FOREIGN KEY (haupt_id) REFERENCES immobilien(id),
                FOREIGN KEY (duplikat_id) REFERENCES immobilien(id),
                UNIQUE(haupt_id, duplikat_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ Datenbank initialisiert")
    
    def scrape_willhaben(self, region: str = "wien", max_preis: float = 25000000) -> List[Dict]:
        """Scrape willhaben.at für Immobilien"""
        logger.info(f"🕷️ Starte Scraping: {region}, max €{max_preis:,.0f}")
        
        immobilien = []
        
        try:
            # Willhaben URL mit Filtern
            url = f"{self.base_url}/immobilien/{region}/wohnung"
            params = {
                'pr': f'0,{int(max_preis)}',
                'ob': '6'  # Wien
            }
            
            response = self.session.get(
                url,
                params=params,
                headers=self.headers,
                timeout=15
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # CSS-Selektoren (müssen ggf. bei willhaben.at-Updates angepasst werden)
            listings = soup.find_all('div', class_='ng-scope')
            
            logger.info(f"Gefundene Listings: {len(listings)}")
            
            for listing in listings:
                try:
                    immobilie = self._parse_listing(listing)
                    if immobilie:
                        immobilien.append(immobilie)
                except Exception as e:
                    logger.debug(f"Fehler beim Parsing: {e}")
                    continue
            
            logger.info(f"✅ {len(immobilien)} Immobilien erfolgreich gescraped")
            return immobilien
        
        except Exception as e:
            logger.error(f"❌ Scraping-Fehler: {e}")
            return []
    
    def _parse_listing(self, listing) -> Dict:
        """Parse ein einzelnes Listing"""
        try:
            # Willhaben-spezifische Selektoren (anpassen bei Änderungen!)
            willhaben_id = listing.get('ng-click', '').split("'")[1] if listing.get('ng-click') else None
            
            titel_elem = listing.find('h2', class_='title')
            titel = titel_elem.text.strip() if titel_elem else ''
            
            preis_elem = listing.find('span', class_='price')
            preis_text = preis_elem.text.strip() if preis_elem else '0'
            preis = self._parse_price(preis_text)
            
            adresse_elem = listing.find('div', class_='location')
            adresse = adresse_elem.text.strip() if adresse_elem else ''
            
            link_elem = listing.find('a', class_='ng-binding')
            url = f"{self.base_url}{link_elem['href']}" if link_elem and 'href' in link_elem.attrs else ''
            
            if not willhaben_id or not preis:
                return None
            
            # Extrahiere Zimmer und Größe aus Titel/Details
            zimmer = self._extract_number(titel, r'(\d+)(?:\s*-\s*Zimmer|\s+Zimmer)')
            flaeche = self._extract_number(titel, r'(\d+)\s*m²')
            
            return {
                'willhaben_id': willhaben_id,
                'titel': titel[:200],
                'preis': preis,
                'adresse': adresse[:150],
                'zimmer': zimmer,
                'flaeche': flaeche,
                'url': url,
                'gescraped_am': datetime.now().isoformat()
            }
        except Exception as e:
            logger.debug(f"Parse-Fehler: {e}")
            return None
    
    def _parse_price(self, price_text: str) -> float:
        """Konvertiere Preistext zu Float"""
        try:
            price_text = price_text.replace('€', '').replace('.', '').replace(',', '.').strip()
            return float(price_text) if price_text else 0
        except:
            return 0
    
    def _extract_number(self, text: str, pattern: str) -> float:
        """Extrahiere Zahl aus Text mit Regex"""
        try:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1))
        except:
            pass
        return None
    
    def save_immobilien(self, immobilien: List[Dict]) -> Tuple[int, int]:
        """Speichere Immobilien in Datenbank"""
        conn = sqlite3.connect(self.db_path, timeout=10)
        c = conn.cursor()
        
        new_count = 0
        updated_count = 0
        
        for immobilie in immobilien:
            try:
                c.execute(
                    'SELECT id FROM immobilien WHERE willhaben_id = ?',
                    (immobilie['willhaben_id'],)
                )
                existing = c.fetchone()
                
                if existing:
                    c.execute('''
                        UPDATE immobilien
                        SET titel=?, preis=?, adresse=?, url=?, zimmer=?, flaeche=?, 
                            aktualisiert_am=CURRENT_TIMESTAMP
                        WHERE willhaben_id=?
                    ''', (
                        immobilie['titel'], immobilie['preis'], immobilie['adresse'],
                        immobilie['url'], immobilie['zimmer'], immobilie['flaeche'],
                        immobilie['willhaben_id']
                    ))
                    updated_count += 1
                else:
                    c.execute('''
                        INSERT INTO immobilien
                        (willhaben_id, titel, preis, adresse, zimmer, flaeche, url, gescraped_am)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        immobilie['willhaben_id'], immobilie['titel'], immobilie['preis'],
                        immobilie['adresse'], immobilie['zimmer'], immobilie['flaeche'],
                        immobilie['url'], immobilie['gescraped_am']
                    ))
                    new_count += 1
            except sqlite3.IntegrityError:
                pass
            except Exception as e:
                logger.error(f"Fehler beim Speichern: {e}")
        
        conn.commit()
        conn.close()
        
        logger.info(f"💾 Gespeichert: {new_count} neu, {updated_count} aktualisiert")
        return new_count, updated_count
    
    def find_duplicates(self) -> List[Dict]:
        """Erkenne Duplikate"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        logger.info("🔍 Suche nach Duplikaten...")
        
        c.execute('''
            SELECT id, titel, preis, adresse FROM immobilien
            WHERE status='aktiv' AND adresse IS NOT NULL
            ORDER BY adresse
        ''')
        
        all_immobilien = c.fetchall()
        duplicates_found = []
        
        for i, immo1 in enumerate(all_immobilien):
            for immo2 in all_immobilien[i+1:]:
                similarity = self._calculate_similarity(immo1, immo2)
                
                if similarity >= 0.85:
                    # Check ob bereits erfasst
                    c.execute('''
                        SELECT id FROM duplikate
                        WHERE (haupt_id=? AND duplikat_id=?) OR (haupt_id=? AND duplikat_id=?)
                    ''', (immo1[0], immo2[0], immo2[0], immo1[0]))
                    
                    if not c.fetchone():
                        try:
                            c.execute('''
                                INSERT INTO duplikate (haupt_id, duplikat_id, aehnlichkeitsgrad, gruende)
                                VALUES (?, ?, ?, ?)
                            ''', (immo1[0], immo2[0], similarity, 'Ähnliche Preis/Lage'))
                            duplicates_found.append({
                                'haupt_id': immo1[0],
                                'duplikat_id': immo2[0],
                                'similarity': similarity
                            })
                        except sqlite3.IntegrityError:
                            pass
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ {len(duplicates_found)} Duplikate gefunden/aktualisiert")
        return duplicates_found
    
    def _calculate_similarity(self, immo1: Tuple, immo2: Tuple) -> float:
        """Berechne Ähnlichkeit zweier Immobilien"""
        from difflib import SequenceMatcher
        
        id1, titel1, preis1, adresse1 = immo1
        id2, titel2, preis2, adresse2 = immo2
        
        similarities = []
        
        # Titel-Ähnlichkeit (30%)
        if titel1 and titel2:
            title_sim = SequenceMatcher(None, titel1.lower(), titel2.lower()).ratio()
            similarities.append(title_sim * 0.3)
        
        # Preis-Ähnlichkeit (40%)
        if preis1 and preis2:
            price_diff = abs(preis1 - preis2) / max(preis1, preis2)
            price_sim = max(0, 1 - price_diff)
            similarities.append(price_sim * 0.4)
        
        # Adress-Ähnlichkeit (30%)
        if adresse1 and adresse2:
            addr_sim = SequenceMatcher(None, adresse1.lower(), adresse2.lower()).ratio()
            similarities.append(addr_sim * 0.3)
        
        return sum(similarities) if similarities else 0
    
    def get_stats(self) -> Dict:
        """Hole Dashboard-Statistiken"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('SELECT COUNT(*) FROM immobilien WHERE status=?', ('aktiv',))
        total = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM immobilien WHERE date(gescraped_am) = date("now")')
        new_today = c.fetchone()[0]
        
        c.execute('SELECT AVG(preis) FROM immobilien WHERE status=?', ('aktiv',))
        avg_price = c.fetchone()[0] or 0
        
        c.execute('SELECT COUNT(*) FROM duplikate')
        duplicates = c.fetchone()[0]
        
        c.execute('''
            SELECT id, titel, preis, adresse, aktualisiert_am
            FROM immobilien
            WHERE status='aktiv'
            ORDER BY aktualisiert_am DESC
            LIMIT 20
        ''')
        recent = [
            {
                'id': r[0],
                'titel': r[1],
                'preis': r[2],
                'adresse': r[3],
                'aktualisiert_am': r[4]
            }
            for r in c.fetchall()
        ]
        
        conn.close()
        
        return {
            'statistiken': {
                'total': total,
                'neu_heute': new_today,
                'durchschnittspreis': avg_price,
                'duplikate': duplicates
            },
            'recent_updates': recent,
            'last_scrape': datetime.now().isoformat()
        }
    
    def get_immobilien(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Hole Immobilien für Dashboard"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        c.execute('''
            SELECT id, titel, preis, adresse, zimmer, flaeche, url, aktualisiert_am
            FROM immobilien
            WHERE status='aktiv'
            ORDER BY aktualisiert_am DESC
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        
        rows = c.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_duplicates(self, limit: int = 50) -> List[Dict]:
        """Hole Duplikate für Dashboard"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            SELECT d.haupt_id, d.duplikat_id, d.aehnlichkeitsgrad,
                   i1.titel, i1.preis, i1.adresse,
                   i2.titel, i2.preis, i2.adresse
            FROM duplikate d
            JOIN immobilien i1 ON d.haupt_id = i1.id
            JOIN immobilien i2 ON d.duplikat_id = i2.id
            ORDER BY d.aehnlichkeitsgrad DESC
            LIMIT ?
        ''', (limit,))
        
        rows = c.fetchall()
        conn.close()
        
        return [
            {
                'haupt_id': r[0],
                'duplikat_id': r[1],
                'similarity': r[2],
                'immo1': {'titel': r[3], 'preis': r[4], 'adresse': r[5]},
                'immo2': {'titel': r[6], 'preis': r[7], 'adresse': r[8]}
            }
            for r in rows
        ]


def main():
    """Hauptprogramm"""
    scraper = ImmobilienScraper()
    
    # Scrape
    logger.info("="*60)
    logger.info("🚀 IMMOBILIEN-TRACKER SCRAPING-ZYKLUS")
    logger.info("="*60)
    
    immobilien = scraper.scrape_willhaben(region="wien", max_preis=25000000)
    
    if immobilien:
        new, updated = scraper.save_immobilien(immobilien)
        duplicates = scraper.find_duplicates()
        stats = scraper.get_stats()
        
        logger.info("="*60)
        logger.info("📊 ERGEBNIS")
        logger.info("="*60)
        logger.info(f"Neue: {new}, Aktualisiert: {updated}")
        logger.info(f"Gesamt: {stats['statistiken']['total']}, Duplikate: {stats['statistiken']['duplikate']}")
        logger.info(f"Ø Preis: €{stats['statistiken']['durchschnittspreis']:,.0f}")
        logger.info("="*60)
    else:
        logger.error("❌ Keine Immobilien gescraped!")
        sys.exit(1)


if __name__ == '__main__':
    main()
