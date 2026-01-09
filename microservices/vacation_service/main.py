# -*- coding: utf-8 -*-
"""
Vacation Report Generator Microservice
Flask API for generating AI-powered plant survival predictions.

Run: python main.py
Endpoints: http://localhost:8002
"""

import os
import sys
import json
from datetime import datetime, timezone
from flask import Flask, jsonify, request
from flask_cors import CORS

# Add parent directory to path for shared config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import get_db

# Gemini AI setup
try:
    import google.generativeai as genai
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        GEMINI_AVAILABLE = True
        print("[VacationService] Gemini AI configured")
    else:
        GEMINI_AVAILABLE = False
        print("[VacationService] Warning: No GOOGLE_API_KEY - AI features disabled")
except ImportError:
    GEMINI_AVAILABLE = False
    print("[VacationService] google.generativeai not installed")

app = Flask(__name__)
CORS(app)

# Firestore collections
SENSORS_COL = "sensors"
USERS_COL = "users"
PLANTS_COL = "plants"

# Gemini models to try
GEMINI_MODELS = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-pro']


# ===========================================
# HELPER FUNCTIONS
# ===========================================

def get_latest_reading(plant_id: str):
    """Get the most recent sensor reading for a plant."""
    db = get_db()
    query = (
        db.collection(SENSORS_COL)
        .where("plant_id", "==", plant_id)
        .order_by("timestamp", direction="DESCENDING")
        .limit(1)
    )
    readings = [doc.to_dict() for doc in query.stream()]
    return readings[0] if readings else None


def list_plants(username: str):
    """Get all plants for a user."""
    db = get_db()
    plants_ref = db.collection(USERS_COL).document(username).collection(PLANTS_COL)
    return [doc.to_dict() for doc in plants_ref.stream()]


def get_vacation_advice_ai(plant_name, current_soil, min_threshold, current_temp, days_away):
    """
    Get AI-powered vacation advice for a plant.
    Returns dict with status, message, recommendation.
    """
    if not GEMINI_AVAILABLE:
        return None
    
    prompt = f"""
You are a plant care expert. Analyze this plant's vacation survival chances:

Plant: {plant_name}
Current Soil Moisture: {current_soil}%
Minimum Threshold: {min_threshold}%
Current Temperature: {current_temp}°C
Days Away: {days_away}

Respond in this exact JSON format only:
{{
    "status": "SAFE" or "NEEDS WATER" or "CRITICAL",
    "message": "Brief explanation (1 sentence)",
    "recommendation": "Actionable advice (1 sentence)"
}}
"""
    
    for model_name in GEMINI_MODELS:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            if response and response.text:
                # Parse JSON from response
                text = response.text.strip()
                # Handle markdown code blocks
                if text.startswith("```"):
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                return json.loads(text.strip())
        except Exception as e:
            print(f"[VacationService] Model {model_name} failed: {e}")
            continue
    
    return None


def generate_vacation_report(username: str, days_away: int):
    """
    Generate a survival report for all user's plants.
    """
    GLOBAL_MAX_DAYS = 21
    
    user_plants = list_plants(username)
    if not user_plants:
        return {"error": "No plants found", "report": []}
    
    report = []
    
    for plant in user_plants:
        plant_id = plant.get("plant_id")
        plant_name = plant.get("name", "Unknown Plant")
        plant_threshold = plant.get('min_soil', 30)
        
        # Fetch sensor data
        latest_data = get_latest_reading(plant_id)
        current_soil = float(latest_data.get("soil", 0)) if latest_data else 0
        current_temp = float(latest_data.get("temp", 25)) if latest_data else 25
        
        try:
            days = int(days_away)
        except (ValueError, TypeError):
            days = 0
        
        status = ""
        msg = ""
        
        # Try AI-powered analysis
        ai_result = get_vacation_advice_ai(
            plant_name=plant_name,
            current_soil=current_soil,
            min_threshold=plant_threshold,
            current_temp=current_temp,
            days_away=days
        )
        
        if ai_result:
            status = ai_result.get("status", "UNKNOWN")
            msg = f"{ai_result.get('message')} -> {ai_result.get('recommendation')}"
            
            # Add visual indicators
            if status == "CRITICAL":
                status += " 💀"
            elif status == "NEEDS WATER":
                status += " 💧"
            elif status == "SAFE":
                status += " ✅"
        else:
            # Fallback logic (no AI)
            print(f"[Fallback] Using math logic for {plant_name}")
            
            drying_rate = 10.0 if plant_threshold > 20 else 2.0
            predicted_soil = current_soil - (days * drying_rate)
            
            if days > GLOBAL_MAX_DAYS:
                status = "CRITICAL 💀"
                msg = "Vacation too long. System limit exceeded."
            elif predicted_soil < plant_threshold:
                days_left = max(0, int((current_soil - plant_threshold) / drying_rate))
                status = "NEEDS WATER 💧"
                msg = f"Will dry in {days_left} days. Water or add irrigation."
            else:
                status = "SAFE ✅"
                msg = f"Predicted soil: {int(predicted_soil)}%. Have fun!"
        
        report.append({
            "plant_name": plant_name,
            "current_soil": f"{current_soil}%",
            "status": status,
            "message": msg
        })
    
    return {
        "username": username,
        "days_away": days_away,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "plant_count": len(report),
        "report": report
    }


# ===========================================
# API ENDPOINTS
# ===========================================

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "vacation-report",
        "gemini_available": GEMINI_AVAILABLE
    })


@app.route('/report/generate', methods=['POST'])
def generate_report():
    """Generate vacation survival report."""
    data = request.get_json() or {}
    username = data.get("username")
    days_away = data.get("days_away", 7)
    
    if not username:
        return jsonify({"error": "username is required"}), 400
    
    result = generate_vacation_report(username, days_away)
    
    if "error" in result and not result.get("report"):
        return jsonify(result), 404
    
    return jsonify(result)


@app.route('/report/plant/<plant_id>', methods=['POST'])
def analyze_single_plant(plant_id):
    """Analyze a single plant for vacation."""
    data = request.get_json() or {}
    days_away = data.get("days_away", 7)
    plant_name = data.get("plant_name", "Plant")
    min_threshold = data.get("min_threshold", 30)
    
    # Get sensor data
    latest = get_latest_reading(plant_id)
    current_soil = float(latest.get("soil", 0)) if latest else 0
    current_temp = float(latest.get("temp", 25)) if latest else 25
    
    # Get AI advice
    result = get_vacation_advice_ai(plant_name, current_soil, min_threshold, current_temp, days_away)
    
    if result:
        return jsonify({
            "plant_id": plant_id,
            "plant_name": plant_name,
            "current_soil": current_soil,
            "current_temp": current_temp,
            "days_away": days_away,
            "analysis": result
        })
    
    return jsonify({"error": "AI analysis failed", "fallback_needed": True}), 500


# ===========================================
# MAIN
# ===========================================

if __name__ == '__main__':
    print("=" * 50)
    print("🏖️  Vacation Report Generator Microservice")
    print("=" * 50)
    print("Endpoints:")
    print("  POST /report/generate        - Generate full vacation report")
    print("  POST /report/plant/<id>      - Analyze single plant")
    print("  GET  /health                 - Service health check")
    print("=" * 50)
    print(f"Gemini AI: {'✅ Available' if GEMINI_AVAILABLE else '❌ Disabled'}")
    print("=" * 50)
    app.run(host='0.0.0.0', port=8002, debug=True)
