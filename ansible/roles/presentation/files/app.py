import os
from flask import Flask, jsonify, render_template, request
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Database configuration
DB_CONFIG = {
    'host': os.getenv('RDS_HOST'),
    'port': int(os.getenv('RDS_PORT', 5432)),
    'database': os.getenv('RDS_DATABASE'),
    'user': os.getenv('RDS_USER'),
    'password': os.getenv('RDS_PASSWORD'),
}

def get_db_connection():
    """Create a database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.Error as e:
        print(f"Database connection error: {e}")
        return None

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'service': 'esteira-geo-presentation',
        'version': '1.0.0'
    }), 200

@app.route('/api/db-status')
def db_status():
    """Check database connectivity"""
    conn = get_db_connection()
    if conn:
        conn.close()
        return jsonify({'status': 'connected', 'database': DB_CONFIG['database']}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Database connection failed'}), 500

@app.route('/api/buckets')
def buckets_info():
    """Return information about data buckets"""
    return jsonify({
        'gold_bucket': os.getenv('AWS_S3_GOLD_BUCKET'),
        'silver_bucket': os.getenv('AWS_S3_SILVER_BUCKET'),
        'architecture': 'Medallion (Bronze -> Silver -> Gold)'
    }), 200

@app.route('/api/geometries')
def get_geometries():
    """Fetch geometries from PostGIS"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Query example: read from geometry table (adjust table name as needed)
            cur.execute("""
                SELECT id, ST_AsGeoJSON(geometry) as geometry, properties
                FROM geometries
                LIMIT 100;
            """)
            rows = cur.fetchall()
        conn.close()
        
        return jsonify({
            'count': len(rows),
            'features': rows
        }), 200
    except psycopg2.Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def get_stats():
    """Get statistics from gold bucket data"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Example query for statistics
            cur.execute("""
                SELECT 
                    COUNT(*) as total_features,
                    ST_AsText(ST_Extent(geometry)) as bbox
                FROM geometries;
            """)
            stats = cur.fetchone()
        conn.close()
        
        return jsonify(stats), 200
    except psycopg2.Error as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found', 'status': 404}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Internal server error', 'status': 500}), 500

if __name__ == '__main__':
    app.run(debug=False, host='127.0.0.1', port=int(os.getenv('FLASK_PORT', 5000)))
