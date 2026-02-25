"""Flask Web - Esteira Geo com Mapa Interativo"""
from flask import Flask, render_template, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import os
from datetime import datetime
import logging

try:
    import folium
    from folium import plugins
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

def get_db_connection():
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        logger.error(f"Conexão falhou: {e}")
        return None

@app.route('/')
def index():
    conn = get_db_connection()
    if not conn:
        return render_template('index.html', error="Banco offline"), 500
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN affected_by_flooding THEN 1 END) as affected,
                COUNT(CASE WHEN NOT affected_by_flooding THEN 1 END) as unaffected
            FROM citizens
        """)
        stats = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template('index.html', stats=stats, last_update=datetime.now().isoformat())
    except Exception as e:
        cursor.close()
        conn.close()
        return render_template('index.html', error=str(e)), 500

@app.route('/map')
def map_view():
    """Retorna um mapa interativo com Folium"""
    if not HAS_FOLIUM:
        return "Folium não instalado. Instale com: pip install folium", 501
    
    conn = get_db_connection()
    if not conn:
        return "Banco de dados offline", 500
    
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Buscar cidadãos com coordenadas
        cursor.execute("""
            SELECT 
                citizen_id, name, address, phone,
                ST_Y(geometry) as lat, ST_X(geometry) as lon,
                affected_by_flooding
            FROM citizens
            ORDER BY citizen_id
        """)
        citizens = cursor.fetchall()
        
        # Buscar áreas de enchente (centroide para popup)
        cursor.execute("""
            SELECT 
                area_id, area_name, flood_date, severity,
                ST_Y(ST_Centroid(geometry)) as lat,
                ST_X(ST_Centroid(geometry)) as lon,
                ST_AsGeoJSON(geometry) as geometry
            FROM flooding_areas
            ORDER BY area_id
        """)
        flood_areas = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Centro do mapa (Porto Alegre)
        center_lat = -30.0277
        center_lon = -51.2287
        
        # Criar mapa base
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=12,
            tiles='OpenStreetMap'
        )
        
        # Grupo de cidadãos afetados
        affected_group = folium.FeatureGroup(name='Cidadãos Afetados (Vermelho)', show=True)
        unaffected_group = folium.FeatureGroup(name='Cidadãos Não Afetados (Azul)', show=True)
        flood_group = folium.FeatureGroup(name='Áreas de Enchente (Verde)', show=True)
        
        # Adicionar cidadãos ao mapa
        for citizen in citizens:
            if citizen['lat'] and citizen['lon']:
                color = 'red' if citizen['affected_by_flooding'] else 'blue'
                icon = 'exclamation-triangle' if citizen['affected_by_flooding'] else 'info-sign'
                
                popup_text = f"""
                <b>{citizen['name']}</b><br>
                ID: {citizen['citizen_id']}<br>
                Endereço: {citizen['address']}<br>
                Telefone: {citizen['phone']}<br>
                Status: {'🔴 AFETADO' if citizen['affected_by_flooding'] else '🟢 SEGURO'}
                """
                
                marker = folium.Marker(
                    location=[citizen['lat'], citizen['lon']],
                    popup=folium.Popup(popup_text, max_width=300),
                    icon=folium.Icon(color=color, icon=icon, prefix='glyphicon')
                )
                
                if citizen['affected_by_flooding']:
                    affected_group.add_child(marker)
                else:
                    unaffected_group.add_child(marker)
        
        # Adicionar áreas de enchente ao mapa
        for area in flood_areas:
            if area['geometry']:
                geom = json.loads(area['geometry'])
                
                popup_text = f"""
                <b>{area['area_name']}</b><br>
                Data: {area['flood_date']}<br>
                Severidade: {area['severity']}
                """
                
                # Adicionar polígono
                folium.GeoJson(
                    geom,
                    style_function=lambda x: {
                        'fillColor': 'green',
                        'color': 'darkgreen',
                        'weight': 2,
                        'opacity': 0.7,
                        'fillOpacity': 0.3
                    },
                    popup=folium.Popup(popup_text, max_width=300)
                ).add_to(flood_group)
        
        # Adicionar grupos ao mapa
        m.add_child(affected_group)
        m.add_child(unaffected_group)
        m.add_child(flood_group)
        
        # Adicionar layer control
        folium.LayerControl().add_to(m)
        
        # Retornar HTML do mapa
        return m._repr_html_()
        
    except Exception as e:
        logger.error(f"Erro ao gerar mapa: {e}")
        cursor.close()
        conn.close()
        return f"Erro: {str(e)}", 500

@app.route('/api/geojson')
def api_geojson():
    """Retorna todos os dados em formato GeoJSON"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database offline'}), 500
    
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Cidadãos
        cursor.execute("""
            SELECT 
                citizen_id, name, address, phone,
                ST_AsGeoJSON(geometry) as geometry,
                affected_by_flooding
            FROM citizens
            ORDER BY citizen_id
        """)
        
        citizens = cursor.fetchall()
        features = []
        
        for citizen in citizens:
            if citizen['geometry']:
                geom = json.loads(citizen['geometry'])
                features.append({
                    'type': 'Feature',
                    'properties': {
                        'id': citizen['citizen_id'],
                        'name': citizen['name'],
                        'address': citizen['address'],
                        'phone': citizen['phone'],
                        'affected': citizen['affected_by_flooding'],
                        'type': 'citizen'
                    },
                    'geometry': geom
                })
        
        # Áreas de enchente
        cursor.execute("""
            SELECT 
                area_id, area_name, flood_date, severity,
                ST_AsGeoJSON(geometry) as geometry
            FROM flooding_areas
        """)
        
        areas = cursor.fetchall()
        
        for area in areas:
            if area['geometry']:
                geom = json.loads(area['geometry'])
                features.append({
                    'type': 'Feature',
                    'properties': {
                        'id': area['area_id'],
                        'name': area['area_name'],
                        'date': area['flood_date'].isoformat() if area['flood_date'] else None,
                        'severity': area['severity'],
                        'type': 'flood_area'
                    },
                    'geometry': geom
                })
        
        cursor.close()
        conn.close()
        
        geojson = {
            'type': 'FeatureCollection',
            'features': features
        }
        
        return jsonify(geojson)
    
    except Exception as e:
        logger.error(f"Erro na API GeoJSON: {e}")
        cursor.close()
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def api_stats():
    """API: retorna estatísticas em JSON"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database offline'}), 500
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            SELECT 
                COUNT(*) as total_citizens,
                COUNT(CASE WHEN affected_by_flooding THEN 1 END) as affected,
                COUNT(CASE WHEN NOT affected_by_flooding THEN 1 END) as unaffected,
                ROUND(100.0 * COUNT(CASE WHEN affected_by_flooding THEN 1 END) / NULLIF(COUNT(*), 0), 2) as affected_pct
            FROM citizens
        """)
        stats = cursor.fetchone()
        cursor.close()
        conn.close()
        return jsonify(stats)
    except Exception as e:
        cursor.close()
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    """Health check"""
    conn = get_db_connection()
    if conn:
        conn.close()
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'offline'}), 503

if __name__ == '__main__':
    logger.info("Iniciando Flask - Esteira Geo")
    app.run(host='0.0.0.0', port=5000, debug=False)
