import subprocess
import time
import requests
import sys
import streamlit.web.cli as stcli
import os

BACKEND_URL = "http://localhost:5000/"
BACKEND_SCRIPT = os.path.join("backend", "app.py")
FRONTEND_SCRIPT = os.path.join("frontend", "ui.py")

def wait_for_backend(timeout=15):
    print("⏳ Waiting for backend to start...")
    for _ in range(timeout * 10):
        try:
            res = requests.get(BACKEND_URL, timeout=1)
            if res.status_code == 200:
                print("✅ Backend is live!")
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(0.1)
    print("❌ Backend failed to start in time.")
    return False

if __name__ == "__main__":
    print("🚀 Starting backend...")
    backend_process = subprocess.Popen([sys.executable, BACKEND_SCRIPT])

    try:
        if wait_for_backend():
            print("🌐 Launching Streamlit frontend...")
            sys.argv = ["streamlit", "run", FRONTEND_SCRIPT]
            sys.exit(stcli.main())
        else:
            backend_process.terminate()
            print("❌ Could not start frontend because backend isn't reachable.")
    except KeyboardInterrupt:
        print("🛑 Shutting down...")
        backend_process.terminate()
