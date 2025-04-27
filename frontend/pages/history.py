import streamlit as st
import requests
from datetime import datetime
import pytz
from streamlit_extras.add_vertical_space import add_vertical_space
from streamlit_extras.stylable_container import stylable_container
from frontend.styles import purple_button_style

# --- API Endpoints ---
API_URL = "http://localhost:5000/get_reports"
CLEAR_URL = "http://localhost:5000/clear_reports"

# --- Fetching Functions ---
@st.cache_data(ttl=60)
def fetch_user_reports(username):
    try:
        res = requests.post(API_URL, json={"username": username}, timeout=5)
        return res.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

def clear_user_history(username):
    try:
        res = requests.post(CLEAR_URL, json={"username": username}, timeout=5)
        return res.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- Helpers ---
def format_timestamp_to_ro(timestamp):
    try:
        utc_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        ro_time = utc_time.astimezone(pytz.timezone("Europe/Bucharest"))
        return ro_time.strftime("%Y.%m.%d   %H:%M:%S")
    except Exception:
        return "Invalid time"

# --- Page ---
def show_history():
    if "token" not in st.session_state or not st.session_state["token"]:
        st.error("🔒 Please log in to access this page.")
        st.stop()

    st.title("📖 Your Report History")

    add_vertical_space(2)

    # --- Buttons First ---
    col1, col2, col3 = st.columns([1,3,1])
    with col1:
        with stylable_container("refresh_btn", css_styles=purple_button_style):
            if st.button("🔄 Refresh"):
                st.cache_data.clear()
                st.session_state["refresh_reports"] = True
                st.rerun()
    with col3:
        with stylable_container("clear_btn", css_styles=purple_button_style):
            if st.button("Clear History"):
                result = clear_user_history(st.session_state["username"])
                if result.get("status") == "success":
                    with col2:
                        st.success(f"✅ Cleared {result.get('deleted', 0)} report(s).")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"❌ Failed to clear history: {result.get('message')}")
                    st.stop()

    # --- Fetch Reports (only after buttons) ---
    data = fetch_user_reports(st.session_state["username"])

    if data.get("status") != "success":
        st.error(f"Error: {data.get('message')}")
        return

    reports = data.get("reports", [])

    if not isinstance(reports, list):
        st.error("⚠️ Unexpected data format — 'reports' should be a list but got something else.")
        st.write("Actual value of reports:", reports)
        return

    if not reports:
        st.info("No reports yet. Start detecting urban problems!")
        return

    # --- Render Reports ---
    for r in reports:
        image_b64 = r["image"]
        location = r["location"]
        details = r["details"]
        timestamp = format_timestamp_to_ro(r["timestamp"])

        st.markdown(f"""
        <div style="
            background-color: #ffffff;
            border: 1px solid #ccc;
            border-radius: 10px;
            padding: 16px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        ">
            <img src="data:image/png;base64,{image_b64}" style="width: 100%; border-radius: 8px;" />
            <div style="margin-top: 12px;">
                <strong>📍 Location:</strong> {location}<br>
                <strong>📝 Details:</strong> {details}<br>
                <strong>🕒 Time:</strong> {timestamp}
            </div>
        </div>
        """, unsafe_allow_html=True)