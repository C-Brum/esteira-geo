"""Flask Web - Esteira Geo com suporte a múltiplos casos de uso"""
from flask import Flask, render_template, jsonify, request
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import os
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

DB_CONFIG = {
    'host': os.getenv('RDS_HOST', 'postgis'),
    'port': int(os.getenv('RDS_PORT', 5432)),
    'database': os.getenv('RDS_NAME', 'esteira_geo'),
    'user': os.getenv('RDS_USER', 'esteira_user'),
    'password': os.getenv('RDS_PASSWORD', 'esteira_local_2025')
}

DEFAULT_USE_CASE = os.getenv('USE_CASE', 'enchentes_poa')


def get_db_connection():
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        logger.error(f"Conexão falhou: {e}")
        return None


def tbl(use_case, base):
    """Retorna nome da tabela prefixada pelo caso de uso: enchentes_poa_citizens"""
    return f"{use_case}_{base}"


def list_use_cases(conn):
    """Lista casos de uso disponíveis detectando tabelas *_citizens no banco"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name LIKE '%_citizens'
        ORDER BY table_name
    """)
    rows = cursor.fetchall()
    cursor.close()
    return [r[0].replace('_citizens', '') for r in rows]


@app.route('/')
def index():
    conn = get_db_connection()
    if not conn:
        return render_template('index.html', error="Banco offline"), 500
    try:
        use_cases = list_use_cases(conn)
        # Usar use_case da query string, ou o default, ou o primeiro disponível
        requested = request.args.get('use_case', DEFAULT_USE_CASE)
        use_case = requested if requested in use_cases else (use_cases[0] if use_cases else None)
        if not use_case:
            conn.close()
            return render_template('index.html', error="Nenhum dado disponível no banco.",
                                   use_cases=[], use_case=None), 200
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(f"""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN affected_by_flooding THEN 1 END) as affected,
                COUNT(CASE WHEN NOT affected_by_flooding THEN 1 END) as unaffected
            FROM {tbl(use_case, 'citizens')}
        """)
        stats = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template('index.html',
                               stats=stats,
                               use_case=use_case,
                               use_cases=use_cases,
                               last_update=datetime.now().isoformat())
    except Exception as e:
        conn.close()
        return render_template('index.html', error=str(e), use_case=None), 500


@app.route('/map')
def map_view():
    use_case = request.args.get('use_case', DEFAULT_USE_CASE)
    return render_template('map.html', use_case=use_case)


@app.route('/api/geojson')
def api_geojson():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database offline'}), 500
    try:
        use_cases = list_use_cases(conn)
        requested = request.args.get('use_case', DEFAULT_USE_CASE)
        use_case = requested if requested in use_cases else (use_cases[0] if use_cases else None)
        if not use_case:
            conn.close()
            return jsonify({'type': 'FeatureCollection', 'features': []})
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        features = []
        cursor.execute(f"""
            SELECT citizen_id, name, address, phone,
                   ST_AsGeoJSON(geometry) as geometry, affected_by_flooding
            FROM {tbl(use_case, 'citizens')} ORDER BY citizen_id
        """)
        for c in cursor.fetchall():
            if c['geometry']:
                features.append({
                    'type': 'Feature',
                    'properties': {
                        'id': c['citizen_id'], 'name': c['name'],
                        'address': c['address'], 'phone': c['phone'],
                        'affected': c['affected_by_flooding'], 'type': 'citizen'
                    },
                    'geometry': json.loads(c['geometry'])
                })

        cursor.execute(f"""
            SELECT area_id, area_name, flood_date, severity,
                   ST_AsGeoJSON(geometry) as geometry
            FROM {tbl(use_case, 'flooding_areas')}
        """)
        for a in cursor.fetchall():
            if a['geometry']:
                features.append({
                    'type': 'Feature',
                    'properties': {
                        'id': a['area_id'], 'name': a['area_name'],
                        'date': a['flood_date'].isoformat() if a['flood_date'] else None,
                        'severity': a['severity'], 'type': 'flood_area'
                    },
                    'geometry': json.loads(a['geometry'])
                })

        cursor.close()
        conn.close()
        return jsonify({'type': 'FeatureCollection', 'features': features})
    except Exception as e:
        cursor.close()
        conn.close()
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats')
def api_stats():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database offline'}), 500
    try:
        use_cases = list_use_cases(conn)
        requested = request.args.get('use_case', DEFAULT_USE_CASE)
        use_case = requested if requested in use_cases else (use_cases[0] if use_cases else None)
        if not use_case:
            conn.close()
            return jsonify({'total_citizens': 0, 'affected': 0, 'unaffected': 0,
                            'affected_pct': 0, 'use_case': None})
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(f"""
            SELECT
                COUNT(*) as total_citizens,
                COUNT(CASE WHEN affected_by_flooding THEN 1 END) as affected,
                COUNT(CASE WHEN NOT affected_by_flooding THEN 1 END) as unaffected,
                ROUND(100.0 * COUNT(CASE WHEN affected_by_flooding THEN 1 END) / NULLIF(COUNT(*), 0), 2) as affected_pct
            FROM {tbl(use_case, 'citizens')}
        """)
        stats = dict(cursor.fetchone())
        stats['use_case'] = use_case
        cursor.close()
        conn.close()
        return jsonify(stats)
    except Exception as e:
        cursor.close()
        conn.close()
        return jsonify({'error': str(e)}), 500


@app.route('/api/use_cases')
def api_use_cases():
    """Lista todos os casos de uso disponíveis no banco"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database offline'}), 500
    try:
        use_cases = list_use_cases(conn)
        conn.close()
        return jsonify({'use_cases': use_cases})
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500


@app.route('/health')
def health():
    conn = get_db_connection()
    if conn:
        conn.close()
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'offline'}), 503


if __name__ == '__main__':
    logger.info("Iniciando Flask - Esteira Geo")
    app.run(host='0.0.0.0', port=5000, debug=False)
