"""
Start all microservices + main app for My Garden Care.

Usage:
    python start_services.py

This will start everything in one terminal:
    - IoT Sync Service on port 8001
    - Vacation Report Service on port 8002
    - Main Gradio App on port 7860
"""

import os
import sys
import threading
import time

def run_iot_service():
    """Run IoT Sync microservice."""
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    from microservices.iot_service.main import app
    print("[Thread] Starting IoT Sync Service on :8001")
    app.run(host='0.0.0.0', port=8001, debug=False, use_reloader=False)


def run_vacation_service():
    """Run Vacation Report microservice."""
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    from microservices.vacation_service.main import app
    print("[Thread] Starting Vacation Service on :8002")
    app.run(host='0.0.0.0', port=8002, debug=False, use_reloader=False)


def run_main_app():
    """Run main Gradio application."""
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Small delay to let microservices start first
    time.sleep(2)
    
    print("[Thread] Starting Main App on :7860")
    import main  # This runs the Gradio app


def start_all():
    """Start all services in separate threads."""
    print("=" * 60)
    print("🚀 My Garden Care - Full Stack Launcher")
    print("=" * 60)
    print("")
    print("Starting services...")
    print("")
    
    # Create threads for each service
    threads = [
        threading.Thread(target=run_iot_service, name="IoT-Service", daemon=True),
        threading.Thread(target=run_vacation_service, name="Vacation-Service", daemon=True),
        threading.Thread(target=run_main_app, name="Main-App", daemon=True),
    ]
    
    # Start all threads
    for t in threads:
        t.start()
        time.sleep(0.5)  # Stagger starts slightly
    
    print("")
    print("=" * 60)
    print("✅ All services starting!")
    print("")
    print("📡 Service URLs:")
    print("   🌡️  IoT Service:      http://localhost:8001")
    print("   🏖️  Vacation Service: http://localhost:8002")
    print("   🌿  Main App:         http://localhost:7860")
    print("")
    print("Press Ctrl+C to stop all services")
    print("=" * 60)
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Shutting down...")
        print("Done!")
        sys.exit(0)


if __name__ == "__main__":
    start_all()
