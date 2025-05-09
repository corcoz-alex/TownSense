import streamlit as st
import requests
from PIL import Image
from io import BytesIO
from streamlit_extras.add_vertical_space import add_vertical_space
from streamlit_extras.stylable_container import stylable_container
from frontend.styles import purple_button_style, hover_text_purple
from streamlit_folium import st_folium
import folium
from geopy.geocoders import Nominatim


# --- Helpers ---
def send_report_to_backend(location, details, uploaded_file):
    try:
        files = {"image": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
        data = {"location": location, "details": details, "username": st.session_state.get("username", "anonymous")}
        response = requests.post("http://localhost:5000/send_email", data=data, files=files, timeout=10)
        return response.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_address_from_coordinates(lat, lon):
    try:
        geolocator = Nominatim(user_agent="TownSense")
        location = geolocator.reverse((lat, lon), language='en')
        return location.address
    except Exception:
        return None


@st.dialog("Report form")
def display_report_form(uploaded_file):
    st.markdown("### 📝 Report a problem to the authorities")

    # Initialize dialog state
    st.session_state.setdefault("selected_location", None)
    st.session_state.setdefault("details", "")

    # Map input
    st.markdown("#### 📍 Select a location on the map")
    m = folium.Map(location=[45.9432, 24.9668], zoom_start=6)
    m.add_child(folium.LatLngPopup())
    map_data = st_folium(m, width=700, height=500)
    if map_data and map_data.get('last_clicked'):
        lat, lon = map_data['last_clicked']['lat'], map_data['last_clicked']['lng']
        st.session_state.selected_location = (lat, lon)
        address = get_address_from_coordinates(lat, lon)
        if address:
            st.session_state.address = address
            st.success(f"Selected Address: {address}")
        else:
            st.warning("Unable to retrieve address.")

    # Details input
    st.markdown("#### 🧾 Problem Details (minimum 20 characters)")
    st.session_state.details = st.text_area("", value=st.session_state.details, key="details_input")

    # Submit
    with stylable_container("submit_report", css_styles=purple_button_style):
        if st.button("📤 Submit Report"):
            if not st.session_state.selected_location:
                st.warning("Please select a location on the map.")
                return
            if len(st.session_state.details.strip()) < 20:
                st.warning("Please provide at least 20 characters for the details.")
                return
            with st.spinner("🚀 Submitting your report..."):
                result = send_report_to_backend(st.session_state.address, st.session_state.details, uploaded_file)
                if result.get("status") == "success":
                    st.success("✅ Report submitted successfully!")
                    st.balloons()
                    # clear all detection and dialog state
                    for key in [
                        'show_report_dialog', 'show_report_button',
                        'uploaded_file', 'original_image_bytes', 'annotated_image_b64',
                        'model_results', 'selected_location', 'address', 'details'
                    ]:
                        st.session_state.pop(key, None)
                else:
                    st.error(f"❌ Error: {result.get('message')}")


# --- Analysis and Detection ---
def analyze_image(uploaded_file):
    # Only store images; do not display here
    with st.spinner("Analyzing image with AI models..."):
        files = {"image": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
        response = requests.post("http://localhost:5000/upload", files=files, timeout=10)
        response.raise_for_status()
        data = response.json()
        # Save state for rendering
        st.session_state['model_results'] = data.get('detected_objects', {})
        st.session_state['annotated_image_b64'] = data.get('image')
        st.session_state['original_image_bytes'] = uploaded_file.getvalue()
        st.session_state['show_report_button'] = bool(any(st.session_state['model_results'].values()))
        st.session_state['uploaded_file'] = uploaded_file


# --- Main UI ---
def show_detection():
    if not st.session_state.get("token"):
        st.error("🔒 Please log in to access this page.")
        return

    st.markdown("""
    <div style="text-align: center;">
        <h1 style="margin-bottom: 0;">AI Urban Problem Detector</h1>
        <p style="font-size: 1.2rem; color: gray;">Analyze street images and automatically detect urban issues.</p>
    </div>
    """, unsafe_allow_html=True)
    add_vertical_space(3)

    # Upload & Analyze
    with st.container():
        st.markdown("### Upload an Image")
        st.markdown("Select a photo showing a street, road, or urban area to start detection.")
        with st.form("upload_form"):
            with stylable_container("upload_button", css_styles=purple_button_style):
                file = st.file_uploader("Choose a file", type=["jpg", "jpeg", "png"])
            with stylable_container("analyze_button", css_styles=purple_button_style):
                submit = st.form_submit_button("Analyze")
            if submit and file:
                analyze_image(file)

    add_vertical_space(3)

    # Show results if available
    if st.session_state.get('original_image_bytes') and st.session_state.get('annotated_image_b64'):

        # Centered Original Image
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            orig = Image.open(BytesIO(st.session_state['original_image_bytes']))
            st.image(orig, use_container_width=True)

        # Spacing between images
        add_vertical_space(2)

        # Centered Annotated Image
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("### 🖼️ Detection Results")
            st.image(f"data:image/png;base64,{st.session_state['annotated_image_b64']}", use_container_width=True)

        # Object details
        if st.session_state['model_results']:
            st.success("✅ Objects detected:")
            for model_name, objs in st.session_state['model_results'].items():
                if objs:
                    with stylable_container(key=f"detection_expander_{model_name}", css_styles=hover_text_purple):
                        with st.expander(f"🔎 {model_name.title()} ({len(objs)} detected)"):
                            for obj in objs:
                                st.write(f"• **{obj['name']}** ({obj['confidence'] * 100:.1f}%) — BBox: {obj['bbox']}")
        else:
            st.warning("⚠️ No detectable issues found in the uploaded image.")

    # Send Report Button
        with col2:
            if st.session_state.get('show_report_button'):
                col1, col2, col3 = st.columns(3)
                with col2:
                    with stylable_container("report_button", css_styles=purple_button_style):
                        if st.button("Send Report"):
                            st.session_state.show_report_dialog = True

    # Report dialog
    if st.session_state.get('show_report_dialog'):
        display_report_form(st.session_state.get('uploaded_file'))