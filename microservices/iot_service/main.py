# -*- coding: utf-8 -*-
"""
IoT Data Sync Microservice
Flask API for syncing sensor data from external IoT server to Firestore.

Run: python main.py
Endpoints: http://localhost:8001
"""

import os
import sys
from datetime import datetime, timezone
from flask import Flask, jsonify, request
from flask_cors import CORS

# Add parent directory to path for shared config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import get_db

app = Flask(__name__)
CORS(app)

# Firestore collection
SENSORS_COL = "sensors"

# External IoT Server URLs (from original data_manager.py)
IOT_BASE_URL = "https://shark-iot-server.onrender.com"
TEMP_FEED = f"{IOT_BASE_URL}/temperature"
HUMIDITY_FEED = f"{IOT_BASE_URL}/humidity"
SOIL_FEED = f"{IOT_BASE_URL}/soil"


# ===========================================
# HELPER FUNCTIONS (extracted from data_manager.py)
# ===========================================

def add_sensor_reading(plant_id: str, temp=None, humidity=None, soil=None, light=None, extra: dict = None):
    """Store a sensor reading in Firestore."""
    db = get_db()
    doc = {
        "plant_id": plant_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temp": temp,
        "humidity": humidity,
        "soil": soil,
        "light": light,
    }
    if extra:
        doc.update(extra)
    ref = db.collection(SENSORS_COL).add(doc)
    return ref[1].id


def get_sensor_history(plant_id: str, limit: int = 50):
    """Get sensor reading history for a plant."""
    db = get_db()
    query = (
        db.collection(SENSORS_COL)
        .where("plant_id", "==", plant_id)
        .order_by("timestamp", direction="DESCENDING")
        .limit(limit)
    )
    return [doc.to_dict() for doc in query.stream()]


def get_latest_reading(plant_id: str):
    """Get the most recent sensor reading."""
    history = get_sensor_history(plant_id, limit=1)
    return history[0] if history else None


def sync_iot_data(plant_id: str):
    """
    Fetch latest sensor data from external IoT server and store in Firestore.
    Uses parallel requests for faster fetching.
    """
    import requests
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    print(f"--- Syncing IoT data for plant: {plant_id} ---")
    
    def fetch_feed(url, name):
        try:
            resp = requests.get(url, timeout=10)
            if resp.ok:
                data = resp.json()
                value = data.get("value")
                print(f"[IOT] Fetched {name}: {value}")
                return name, value
        except Exception as e:
            print(f"[IOT] Error fetching {name}: {e}")
        return name, None
    
    feeds = [
        (TEMP_FEED, "temperature"),
        (HUMIDITY_FEED, "humidity"),
        (SOIL_FEED, "soil"),
    ]
    
    results = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(fetch_feed, url, name): name for url, name in feeds}
        for future in as_completed(futures):
            name, value = future.result()
            results[name] = value
    
    temp = results.get("temperature")
    humidity = results.get("humidity")
    soil = results.get("soil")
    
    if temp is None and humidity is None and soil is None:
        return {"success": False, "error": "No data received from IoT server"}
    
    doc_id = add_sensor_reading(plant_id, temp=temp, humidity=humidity, soil=soil)
    print(f"[IOT] Data synced to Firestore. ID: {doc_id}")
    
    return {
        "success": True,
        "doc_id": doc_id,
        "data": {"temp": temp, "humidity": humidity, "soil": soil}
    }


# ===========================================
# API ENDPOINTS
# ===========================================

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "iot-sync"})


@app.route('/sync/<plant_id>', methods=['POST'])
def sync_plant(plant_id):
    """Trigger IoT sync for a specific plant."""
    result = sync_iot_data(plant_id)
    if result.get("success"):
        return jsonify(result), 200
    return jsonify(result), 500


@app.route('/sync/batch', methods=['POST'])
def sync_batch():
    """Sync multiple plants at once."""
    data = request.get_json() or {}
    plant_ids = data.get("plant_ids", [])
    
    if not plant_ids:
        return jsonify({"error": "No plant_ids provided"}), 400
    
    results = []
    for pid in plant_ids:
        result = sync_iot_data(pid)
        results.append({"plant_id": pid, **result})
    
    return jsonify({"results": results})


@app.route('/readings/<plant_id>', methods=['GET'])
def get_readings(plant_id):
    """Get sensor history for a plant."""
    limit = request.args.get('limit', 50, type=int)
    history = get_sensor_history(plant_id, limit=limit)
    return jsonify({"plant_id": plant_id, "readings": history, "count": len(history)})


@app.route('/readings/<plant_id>/latest', methods=['GET'])
def get_latest(plant_id):
    """Get the latest sensor reading for a plant."""
    reading = get_latest_reading(plant_id)
    if reading:
        return jsonify({"plant_id": plant_id, "reading": reading})
    return jsonify({"plant_id": plant_id, "reading": None, "message": "No readings found"}), 404


# ===========================================
# MAIN
# ===========================================

if __name__ == '__main__':
    print("=" * 50)
    print("🌡️  IoT Data Sync Microservice")
    print("=" * 50)
    print("Endpoints:")
    print("  POST /sync/<plant_id>     - Sync IoT data for plant")
    print("  POST /sync/batch          - Sync multiple plants")
    print("  GET  /readings/<plant_id> - Get sensor history")
    print("  GET  /readings/<plant_id>/latest - Get latest reading")
    print("=" * 50)
    app.run(host='0.0.0.0', port=8001, debug=True)
