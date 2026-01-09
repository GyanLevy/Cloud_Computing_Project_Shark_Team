# -*- coding: utf-8 -*-
"""
service_client.py
Microservice Client for My Garden Care

Provides HTTP client functions to call microservices with fallback to local functions.
"""

import os
import requests
from typing import Optional, List, Dict, Any

# Service URLs (configurable via environment)
IOT_SERVICE_URL = os.getenv("IOT_SERVICE_URL", "http://localhost:8001")
VACATION_SERVICE_URL = os.getenv("VACATION_SERVICE_URL", "http://localhost:8002")

# Timeout for HTTP requests (seconds)
REQUEST_TIMEOUT = 30


def _check_service_health(base_url: str) -> bool:
    """Check if a microservice is available."""
    try:
        resp = requests.get(f"{base_url}/health", timeout=2)
        return resp.ok
    except Exception:
        return False


# ===========================================
# IOT SERVICE CLIENT
# ===========================================

def sync_iot_data_via_service(plant_id: str) -> dict:
    """
    Sync IoT data via microservice with fallback to local function.
    
    Returns:
        dict with sync result or error
    """
    try:
        resp = requests.post(
            f"{IOT_SERVICE_URL}/sync/{plant_id}",
            timeout=REQUEST_TIMEOUT
        )
        if resp.ok:
            print(f"[ServiceClient] IoT sync via microservice: {plant_id}")
            return resp.json()
    except requests.RequestException as e:
        print(f"[ServiceClient] IoT service unavailable: {e}")
    
    # Fallback to local function
    print(f"[ServiceClient] Falling back to local sync_iot_data()")
    from data_manager import sync_iot_data
    return sync_iot_data(plant_id)


def sync_iot_batch_via_service(plant_ids: List[str]) -> dict:
    """
    Sync multiple plants via microservice with fallback.
    """
    try:
        resp = requests.post(
            f"{IOT_SERVICE_URL}/sync/batch",
            json={"plant_ids": plant_ids},
            timeout=REQUEST_TIMEOUT * 2
        )
        if resp.ok:
            print(f"[ServiceClient] Batch IoT sync via microservice: {len(plant_ids)} plants")
            return resp.json()
    except requests.RequestException as e:
        print(f"[ServiceClient] IoT service unavailable: {e}")
    
    # Fallback to local
    print(f"[ServiceClient] Falling back to local batch sync")
    from data_manager import sync_iot_data
    results = []
    for pid in plant_ids:
        result = sync_iot_data(pid)
        results.append({"plant_id": pid, **result})
    return {"results": results}


def get_sensor_history_via_service(plant_id: str, limit: int = 50) -> List[dict]:
    """
    Get sensor history via microservice with fallback.
    """
    try:
        resp = requests.get(
            f"{IOT_SERVICE_URL}/readings/{plant_id}",
            params={"limit": limit},
            timeout=REQUEST_TIMEOUT
        )
        if resp.ok:
            return resp.json().get("readings", [])
    except requests.RequestException:
        pass
    
    # Fallback
    from data_manager import get_sensor_history
    return get_sensor_history(plant_id, limit)


def get_latest_reading_via_service(plant_id: str) -> Optional[dict]:
    """
    Get latest sensor reading via microservice with fallback.
    """
    try:
        resp = requests.get(
            f"{IOT_SERVICE_URL}/readings/{plant_id}/latest",
            timeout=REQUEST_TIMEOUT
        )
        if resp.ok:
            return resp.json().get("reading")
    except requests.RequestException:
        pass
    
    # Fallback
    from data_manager import get_latest_reading
    return get_latest_reading(plant_id)


# ===========================================
# VACATION SERVICE CLIENT
# ===========================================

def generate_vacation_report_via_service(username: str, days_away: int) -> dict:
    """
    Generate vacation report via microservice with fallback to local function.
    
    Returns:
        dict with report data
    """
    try:
        resp = requests.post(
            f"{VACATION_SERVICE_URL}/report/generate",
            json={"username": username, "days_away": days_away},
            timeout=REQUEST_TIMEOUT * 2  # Longer timeout for AI
        )
        if resp.ok:
            print(f"[ServiceClient] Vacation report via microservice: {username}")
            data = resp.json()
            # Convert to list format expected by UI
            report_list = []
            for item in data.get("report", []):
                report_list.append([
                    item.get("plant_name", ""),
                    item.get("current_soil", ""),
                    item.get("status", ""),
                    item.get("message", "")
                ])
            return report_list
    except requests.RequestException as e:
        print(f"[ServiceClient] Vacation service unavailable: {e}")
    
    # Fallback to local function
    print(f"[ServiceClient] Falling back to local generate_vacation_report()")
    from data_manager import generate_vacation_report
    return generate_vacation_report(username, days_away)


def analyze_plant_vacation_via_service(
    plant_id: str,
    plant_name: str,
    days_away: int,
    min_threshold: int = 30
) -> Optional[dict]:
    """
    Analyze single plant for vacation via microservice.
    """
    try:
        resp = requests.post(
            f"{VACATION_SERVICE_URL}/report/plant/{plant_id}",
            json={
                "days_away": days_away,
                "plant_name": plant_name,
                "min_threshold": min_threshold
            },
            timeout=REQUEST_TIMEOUT
        )
        if resp.ok:
            return resp.json().get("analysis")
    except requests.RequestException:
        pass
    
    # Fallback
    from plants_manager import get_vacation_advice_ai
    from data_manager import get_latest_reading
    
    latest = get_latest_reading(plant_id)
    current_soil = float(latest.get("soil", 0)) if latest else 0
    current_temp = float(latest.get("temp", 25)) if latest else 25
    
    return get_vacation_advice_ai(plant_name, current_soil, min_threshold, current_temp, days_away)


# ===========================================
# SERVICE STATUS CHECK
# ===========================================

def get_services_status() -> dict:
    """
    Check health status of all microservices.
    """
    return {
        "iot_service": {
            "url": IOT_SERVICE_URL,
            "healthy": _check_service_health(IOT_SERVICE_URL)
        },
        "vacation_service": {
            "url": VACATION_SERVICE_URL,
            "healthy": _check_service_health(VACATION_SERVICE_URL)
        }
    }
