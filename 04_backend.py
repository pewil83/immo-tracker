#!/usr/bin/env python3
"""
Flask Backend API für Immobilien-Tracker
Production-ready REST API mit CORS und Error Handling
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import logging
from datetime import datetime
import os
from functools import wraps

app = Flask(__name__)
CORS(app)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
DB_PATH = os.getenv('DB_PATH', 'immobilien.db')
FLASK_ENV = os.getenv('FLASK_ENV', 'development')

# Error Handler Decorator
def handle_errors(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except sqlite3.DatabaseError as e:
            logger.error(f"Database error: {e}")
            return jsonify({'error': 'Datenbankfehler'}), 500
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return jsonify({'error': 'Interner Fehler'}), 500
    return decorated_function

# Database Helper
def get_db():
    """Hole Datenbankverbindung"""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

# Health Check
@app.route('/health', methods=['GET'])
def health():
    """Health Check Endpoint"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT 1')
        conn.close()
        return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

# Stats Endpoint
@app.route('/api/stats', methods=['GET'])
@handle_errors
def get_stats():
    """Hole Dashboard-Statistiken"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) FROM immobilien WHERE status=?', ('aktiv',))
    total = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM immobilien WHERE date(gescraped_am) = date("now")')
    new_today = c.fetchone()[0]
    
    c.execute('SELECT AVG(preis) FROM immobilien WHERE status=?', ('aktiv',))
    avg_price = c.fetchone()[0] or 0
    
    c.execute('SELECT COUNT(*) FROM duplikate')
    duplicates = c.fetchone()[0]
    
    c.execute('SELECT MAX(gescraped_am) FROM immobilien')
    last_scrape = c.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'statistiken': {
            'total': total,
            'neu_heute': new_today,
            'durchschnittspreis': round(avg_price, 2),
            'duplikate': duplicates
        },
        'last_scrape': last_scrape,
        'timestamp': datetime.now().isoformat()
    }), 200

# Immobilien List Endpoint
@app.route('/api/immobilien', methods=['GET'])
@handle_errors
def get_immobilien():
    """Hole Liste der Immobilien mit Pagination und Filtering"""
    conn = get_db()
    c = conn.cursor()
    
    # Parameter
    limit = min(int(request.args.get('limit', 100)), 500)  # Max 500
    offset = int(request.args.get('offset', 0))
    search = request.args.get('search', '')
    
    # Query mit optionalem Search
    if search:
        query = '''
            SELECT id, titel, preis, adresse, zimmer, flaeche, url, aktualisiert_am
            FROM immobilien
            WHERE status='aktiv' AND (titel LIKE ? OR adresse LIKE ?)
            ORDER BY aktualisiert_am DESC
            LIMIT ? OFFSET ?
        '''
        c.execute(query, (f'%{search}%', f'%{search}%', limit, offset))
    else:
        query = '''
            SELECT id, titel, preis, adresse, zimmer, flaeche, url, aktualisiert_am
            FROM immobilien
            WHERE status='aktiv'
            ORDER BY aktualisiert_am DESC
            LIMIT ? OFFSET ?
        '''
        c.execute(query, (limit, offset))
    
    rows = c.fetchall()
    
    # Total Count
    if search:
        c.execute('SELECT COUNT(*) FROM immobilien WHERE status=? AND (titel LIKE ? OR adresse LIKE ?)',
                  ('aktiv', f'%{search}%', f'%{search}%'))
    else:
        c.execute('SELECT COUNT(*) FROM immobilien WHERE status=?', ('aktiv',))
    
    total = c.fetchone()[0]
    conn.close()
    
    return jsonify({
        'immobilien': [dict(row) for row in rows],
        'pagination': {
            'total': total,
            'limit': limit,
            'offset': offset,
            'has_more': offset + limit < total
        }
    }), 200

# Single Immobilie Detail
@app.route('/api/immobilien/<int:immo_id>', methods=['GET'])
@handle_errors
def get_immobilie(immo_id):
    """Hole Details einer einzelnen Immobilie"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute('SELECT * FROM immobilien WHERE id=?', (immo_id,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        return jsonify({'error': 'Nicht gefunden'}), 404
    
    immobilie = dict(row)
    
    # Hole verwandte Duplikate
    c.execute('''
        SELECT d.duplikat_id, i.titel, i.preis, i.adresse, d.aehnlichkeitsgrad
        FROM duplikate d
        JOIN immobilien i ON d.duplikat_id = i.id
        WHERE d.haupt_id = ?
        ORDER BY d.aehnlichkeitsgrad DESC
    ''', (immo_id,))
    
    duplicates = [dict(row) for row in c.fetchall()]
    immobilie['duplicates'] = duplicates
    
    conn.close()
    return jsonify(immobilie), 200

# Duplikate Endpoint
@app.route('/api/duplicates', methods=['GET'])
@handle_errors
def get_duplicates():
    """Hole alle Duplikate"""
    conn = get_db()
    c = conn.cursor()
    
    limit = min(int(request.args.get('limit', 50)), 500)
    offset = int(request.args.get('offset', 0))
    
    c.execute('''
        SELECT d.id, d.haupt_id, d.duplikat_id, d.aehnlichkeitsgrad, d.erkannt_am,
               i1.titel as titel1, i1.preis as preis1, i1.adresse as adresse1,
               i2.titel as titel2, i2.preis as preis2, i2.adresse as adresse2
        FROM duplikate d
        JOIN immobilien i1 ON d.haupt_id = i1.id
        JOIN immobilien i2 ON d.duplikat_id = i2.id
        ORDER BY d.aehnlichkeitsgrad DESC
        LIMIT ? OFFSET ?
    ''', (limit, offset))
    
    rows = c.fetchall()
    
    c.execute('SELECT COUNT(*) FROM duplikate')
    total = c.fetchone()[0]
    
    conn.close()
    
    duplicates = []
    for row in rows:
        duplicates.append({
            'id': row['id'],
            'haupt_id': row['haupt_id'],
            'duplikat_id': row['duplikat_id'],
            'similarity': round(row['aehnlichkeitsgrad'] * 100, 1),
            'erkannt_am': row['erkannt_am'],
            'immo1': {
                'id': row['haupt_id'],
                'titel': row['titel1'],
                'preis': row['preis1'],
                'adresse': row['adresse1']
            },
            'immo2': {
                'id': row['duplikat_id'],
                'titel': row['titel2'],
                'preis': row['preis2'],
                'adresse': row['adresse2']
            }
        })
    
    return jsonify({
        'duplicates': duplicates,
        'pagination': {
            'total': total,
            'limit': limit,
            'offset': offset,
            'has_more': offset + limit < total
        }
    }), 200

# Filter Endpoint
@app.route('/api/filter', methods=['GET'])
@handle_errors
def filter_immobilien():
    """Hole gefilterte Immobilien"""
    conn = get_db()
    c = conn.cursor()
    
    min_price = float(request.args.get('min_price', 0))
    max_price = float(request.args.get('max_price', 999999999))
    min_rooms = int(request.args.get('min_rooms', 0))
    min_size = float(request.args.get('min_size', 0))
    bezirk = request.args.get('bezirk', '')
    
    query = '''
        SELECT id, titel, preis, adresse, zimmer, flaeche, url, aktualisiert_am
        FROM immobilien
        WHERE status='aktiv'
        AND preis >= ? AND preis <= ?
        AND (zimmer IS NULL OR zimmer >= ?)
        AND (flaeche IS NULL OR flaeche >= ?)
    '''
    params = [min_price, max_price, min_rooms, min_size]
    
    if bezirk:
        query += ' AND adresse LIKE ?'
        params.append(f'%{bezirk}%')
    
    query += ' ORDER BY preis ASC LIMIT 200'
    
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    
    return jsonify({
        'immobilien': [dict(row) for row in rows],
        'count': len(rows)
    }), 200

# Recent Updates Endpoint
@app.route('/api/recent', methods=['GET'])
@handle_errors
def get_recent():
    """Hole die neuesten Updates"""
    conn = get_db()
    c = conn.cursor()
    
    hours = int(request.args.get('hours', 24))
    
    c.execute('''
        SELECT id, titel, preis, adresse, zimmer, flaeche, url, aktualisiert_am
        FROM immobilien
        WHERE status='aktiv' 
        AND datetime(aktualisiert_am) > datetime('now', '-' || ? || ' hours')
        ORDER BY aktualisiert_am DESC
    ''', (hours,))
    
    rows = c.fetchall()
    conn.close()
    
    return jsonify({
        'recent': [dict(row) for row in rows],
        'count': len(rows),
        'hours': hours
    }), 200

# Stats by Bezirk
@app.route('/api/stats/bezirk', methods=['GET'])
@handle_errors
def stats_by_bezirk():
    """Statistiken nach Bezirk"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        SELECT 
            bezirk,
            COUNT(*) as count,
            AVG(preis) as avg_price,
            MIN(preis) as min_price,
            MAX(preis) as max_price
        FROM immobilien
        WHERE status='aktiv' AND bezirk IS NOT NULL
        GROUP BY bezirk
        ORDER BY count DESC
        LIMIT 20
    ''')
    
    rows = c.fetchall()
    conn.close()
    
    stats = []
    for row in rows:
        stats.append({
            'bezirk': row['bezirk'],
            'count': row['count'],
            'avg_price': round(row['avg_price'], 2) if row['avg_price'] else 0,
            'min_price': row['min_price'],
            'max_price': row['max_price']
        })
    
    return jsonify({'bezirke': stats}), 200

# Fehlerbehandlung
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint nicht gefunden'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Interner Serverfehler'}), 500

# Info Endpoint
@app.route('/api/info', methods=['GET'])
def info():
    """System Info"""
    return jsonify({
        'name': 'Immobilien-Tracker API',
        'version': '1.0.0',
        'status': 'online',
        'environment': FLASK_ENV,
        'timestamp': datetime.now().isoformat()
    }), 200

# CORS Preflight
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = jsonify({'status': 'ok'})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        response.headers.add("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        return response, 200

if __name__ == '__main__':
    logger.info(f"🚀 Starting Flask API server (ENV={FLASK_ENV})")
    logger.info(f"Database: {DB_PATH}")
    
    # Production: use production server
    if FLASK_ENV == 'production':
        # Für Production: Gunicorn verwenden
        # Command: gunicorn -w 4 -b 0.0.0.0:5000 backend:app
        app.run(host='0.0.0.0', port=5000, debug=False)
    else:
        app.run(host='localhost', port=5000, debug=True)
