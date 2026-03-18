"""Flask Web - Esteira Geo com suporte a múltiplos casos de uso"""
from flask import Flask, render_template, jsonify, request
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import os
from datetime import datetime
import logging

try:
    import folium
    HAS_FOLIUM = True
except ImportError:
    HAS_FOLIUM = False

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
    use_case = request.args.get('use_case', DEFAULT_USE_CASE)
    conn = get_db_connection()
    if not conn:
        return render_template('index.html', error="Banco offline"), 500
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute(f"""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN affected_by_flooding THEN 1 END) as affected,
                COUNT(CASE WHEN NOT affected_by_flooding THEN 1 END) as unaffected
            FROM {tbl(use_case, 'citizens')}
        """)
        stats = cursor.fetchone()
        use_cases = list_use_cases(conn)
        cursor.close()
        conn.close()
        return render_template('index.html',
                               stats=stats,
                               use_case=use_case,
                               use_cases=use_cases,
                               last_update=datetime.now().isoformat())
    except Exception as e:
        cursor.close()
        conn.close()
        return render_template('index.html', error=str(e), use_case=use_case), 500


@app.route('/map')
def map_view():
    if not HAS_FOLIUM:
        return "Folium não instalado.", 501
    use_case = request.args.get('use_case', DEFAULT_USE_CASE)
    conn = get_db_connection()
    if not conn:
        return "Banco de dados offline", 500
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute(f"""
            SELECT citizen_id, name, address, phone,
                   ST_Y(geometry) as lat, ST_X(geometry) as lon,
                   affected_by_flooding
            FROM {tbl(use_case, 'citizens')} ORDER BY citizen_id
        """)
        citizens = cursor.fetchall()

        cursor.execute(f"""
            SELECT area_id, area_name, flood_date, severity,
                   ST_Y(ST_Centroid(geometry)) as lat,
                   ST_X(ST_Centroid(geometry)) as lon,
                   ST_AsGeoJSON(geometry) as geometry
            FROM {tbl(use_case, 'flooding_areas')} ORDER BY area_id
        """)
        flood_areas = cursor.fetchall()
        cursor.close()
        conn.close()

        m = folium.Map(location=[-30.0277, -51.2287], zoom_start=12, tiles='OpenStreetMap')
        affected_group   = folium.FeatureGroup(name='Cidadãos Afetados (Vermelho)', show=True)
        unaffected_group = folium.FeatureGroup(name='Cidadãos Não Afetados (Azul)', show=True)
        flood_group      = folium.FeatureGroup(name='Áreas de Enchente (Verde)', show=True)

        for c in citizens:
            if c['lat'] and c['lon']:
                color  = 'red' if c['affected_by_flooding'] else 'blue'
                icon   = 'exclamation-triangle' if c['affected_by_flooding'] else 'info-sign'
                popup  = (f"<b>{c['name']}</b><br>ID: {c['citizen_id']}<br>"
                          f"Endereço: {c['address']}<br>Telefone: {c['phone']}<br>"
                          f"Status: {'🔴 AFETADO' if c['affected_by_flooding'] else '🟢 SEGURO'}")
                marker = folium.Marker(
                    location=[c['lat'], c['lon']],
                    popup=folium.Popup(popup, max_width=300),
                    icon=folium.Icon(color=color, icon=icon, prefix='glyphicon')
                )
                (affected_group if c['affected_by_flooding'] else unaffected_group).add_child(marker)

        for area in flood_areas:
            if area['geometry']:
                folium.GeoJson(
                    json.loads(area['geometry']),
                    style_function=lambda x: {
                        'fillColor': 'green', 'color': 'darkgreen',
                        'weight': 2, 'opacity': 0.7, 'fillOpacity': 0.3
                    },
                    popup=folium.Popup(
                        f"<b>{area['area_name']}</b><br>Data: {area['flood_date']}<br>Severidade: {area['severity']}",
                        max_width=300
                    )
                ).add_to(flood_group)

        m.add_child(affected_group)
        m.add_child(unaffected_group)
        m.add_child(flood_group)
        folium.LayerControl().add_to(m)
        return m._repr_html_()

    except Exception as e:
        logger.error(f"Erro ao gerar mapa: {e}")
        cursor.close()
        conn.close()
        return f"Erro: {str(e)}", 500


@app.route('/api/geojson')
def api_geojson():
    use_case = request.args.get('use_case', DEFAULT_USE_CASE)
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database offline'}), 500
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
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
    use_case = request.args.get('use_case', DEFAULT_USE_CASE)
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database offline'}), 500
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
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
