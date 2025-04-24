import streamlit as st
import requests
from datetime import datetime
import pytz
from streamlit_extras.stylable_container import stylable_container
from frontend.styles import purple_button_style

API_URL = "http://localhost:5000/get_reports"


@st.cache_data(ttl=60)
def fetch_user_reports(username):
    try:
        res = requests.post(API_URL, json={"username": username}, timeout=5)
        return res.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

def format_timestamp_to_ro(timestamp):
    try:
        utc_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        ro_time = utc_time.astimezone(pytz.timezone("Europe/Bucharest"))
        return ro_time.strftime("%Y.%m.%d   %H:%M:%S")
    except Exception:
        return "Invalid time"

def clear_user_history(username):
    try:
        res = requests.post("http://localhost:5000/clear_reports", json={"username": username}, timeout=5)
        return res.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}


def show_history():
    if "token" not in st.session_state or not st.session_state["token"]:
        st.error("🔒 Please log in to access this page.")
        st.stop()

    st.title("📖 Your Report History")

    # --- Refresh Logic ---
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        with stylable_container("refresh_btn", css_styles=purple_button_style):
            if st.button("Refresh"):
                st.session_state.refresh_reports = True
                st.cache_data.clear()

    if st.session_state.get("refresh_reports"):
        with st.spinner("Refreshing reports..."):
            data = fetch_user_reports(st.session_state["username"])
        st.session_state.refresh_reports = False
    else:
        data = fetch_user_reports(st.session_state["username"])

    # --- Render reports ---
    if data.get("status") != "success":
        st.error(f"Error: {data.get('message')}")
        return

    reports = data.get("reports", [])
    if not reports:
        st.info("You haven't submitted any reports yet.")
        return
    if not isinstance(reports, list):
        st.error("⚠️ Unexpected data format — 'reports' is not a list.")
        st.write("Actual value of reports:", reports)
        return
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

    st.markdown("---")
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        with stylable_container("clear_btn", css_styles=purple_button_style):
            if st.button("🗑️ Clear All History"):
                result = clear_user_history(st.session_state["username"])
                if result.get("status") == "success":
                    st.success(f"✅ Cleared {result.get('deleted', 0)} report(s).")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"❌ Failed to clear history: {result.get('message')}")
