import streamlit as st
import requests
import time
from PIL import Image
from streamlit_extras.add_vertical_space import add_vertical_space
from streamlit_extras.stylable_container import stylable_container
from frontend.styles import purple_button_style, radio_button_style, hover_text_purple
from streamlit_folium import st_folium
import folium
from geopy.geocoders import Nominatim


# --- Helpers ---
def send_report_to_backend(location, details, uploaded_file, max_retries=3):
    retry_delay = 2  # Start with a 2-second delay
    attempt = 0

    while attempt < max_retries:
        try:
            files = {
                "image": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
            }
            data = {
                "location": location,
                "details": details,
                "username": st.session_state.get("username", "anonymous")
            }
            response = requests.post("http://localhost:5000/send_email", data=data, files=files, timeout=10)

            # Check for successful response
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"❌ Report submission failed: {response.text}")

        except Exception as e:
            st.error(f"❌ An error occurred: {e}")

        # Retry logic
        attempt += 1
        if attempt < max_retries:
            st.warning(f"⚠️ Attempt {attempt} failed. Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff

    return {"status": "error", "message": "Failed to send report after multiple attempts."}


def load_lottie_url(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()


def get_address_from_coordinates(lat, lon):
    try:
        geolocator = Nominatim(user_agent="TownSense")
        location = geolocator.reverse((lat, lon), language='en')
        return location.address
    except Exception:
        return None


def send_to_evaluation(detections, base64_image=None):
    try:
        payload = {"detections": detections}
        if base64_image:
            payload["image"] = base64_image

        response = requests.post("http://localhost:5000/evaluate", json=payload, timeout=45)  # Increased timeout
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        return {
            "status": "error",
            "message": "AI evaluation timed out. The server is processing your request but it's taking longer than expected."
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@st.dialog("Report form")
def display_report_form(uploaded_file):
    st.markdown("### 📝 Report a problem to the authorities")

    # Initialize dialog state
    st.session_state.setdefault("selected_location", None)
    st.session_state.setdefault("details", "")
    # Ensure dialog doesn't affect main UI display
    st.session_state.setdefault("dialog_open", True)

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
                    # Clear report dialog state but keep detection state
                    for key in [
                        'show_report_dialog', 'selected_location', 'address', 'details', 'dialog_open'
                    ]:
                        st.session_state.pop(key, None)

                    st.session_state['report_submitted'] = True

                    # Add a delay before clearing everything
                    time.sleep(2)

                    st.rerun()
                else:
                    st.error(f"❌ Error: {result.get('message')}")


# CSS for the loading effect during AI analysis
ai_analysis_overlay_css = """
.ai-analysis-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    z-index: 1000;
    background-color: rgba(0, 0, 0, 0.5);
}

.rotating-screw {
    width: 100px;
    height: 100px;
    animation: rotate 2s linear infinite;
}

@keyframes rotate {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

.ai-text {
    color: white;
    font-size: 24px;
    margin-top: 20px;
    text-shadow: 0px 0px 10px rgba(119, 92, 255, 1);
}
"""


# --- Page ---
def show_detection():
    if "token" not in st.session_state or not st.session_state["token"]:
        st.error("🔒 Please log in to access this page.")
        st.stop()

    st.markdown(f"<style>{ai_analysis_overlay_css}</style>", unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align: center;">
        <h1 style="margin-bottom: 0;">AI Urban Problem Detector</h1>
        <p style="font-size: 1.2rem; color: gray;">Analyze street images and automatically detect urban issues.</p>
    </div>
    """, unsafe_allow_html=True)

    add_vertical_space(3)

    # Check if we need to clear state due to successful report submission
    if st.session_state.get('report_submitted'):
        # Clear relevant detection state after successful submission
        for key in [
            'report_submitted', 'show_report_button',
            'uploaded_file', 'original_image_bytes', 'annotated_image_b64',
            'model_results', 'evaluation_result', 'feedback_correct', 'feedback_comments'
        ]:
            st.session_state.pop(key, None)

    # File upload form - always show this
    with st.container():
        st.markdown("### Upload an Image")
        st.markdown("Select a photo showing a street, road, or urban area to start detection.")

        with st.form("upload_form", clear_on_submit=True):
            with stylable_container("upload_button", css_styles=purple_button_style):
                uploaded_file = st.file_uploader("Choose a file", type=["jpg", "jpeg", "png"])
            add_vertical_space(1)
            with stylable_container("analyze_button", css_styles=purple_button_style):
                submitted = st.form_submit_button("Analyze")

        if submitted and uploaded_file:
            st.success("✅ Image uploaded successfully.")
            # Store uploaded file in session state for persistence
            st.session_state['uploaded_file'] = uploaded_file

            # Process the image
            results_container = st.container()
            
            # Create the overlay container for the loading effect
            overlay_placeholder = st.empty()

            # Show loading overlay
            with overlay_placeholder:
                st.markdown("""
                <div class="ai-analysis-overlay">
                    <div class="rotating-screw">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white">
                            <path d="M12,1L8,5H11V14H13V5H16M18,23H6V19H18V23M15,15H9L6,18H18L15,15Z" />
                        </svg>
                    </div>
                    <div class="ai-text">AI is analyzing your image...</div>
                </div>
                """, unsafe_allow_html=True)

            with st.spinner("Analyzing image with AI models..."):
                try:
                    # Reset file pointer to beginning
                    uploaded_file.seek(0)

                    files = {
                        "image": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
                    }
                    response = requests.post("http://localhost:5000/upload", files=files, timeout=30)
                    response.raise_for_status()
                    data = response.json()
                    model_results = data.get("detected_objects", {})

                    st.session_state['model_results'] = model_results
                    eval_result = send_to_evaluation(model_results, data.get('image'))
                    overlay_placeholder.empty()

                    # Store evaluation results in session state
                    st.session_state['evaluation_result'] = eval_result
                    # Enable showing the report button
                    st.session_state['show_report_button'] = True

                except requests.exceptions.RequestException as e:
                    # Clear the overlay on error
                    overlay_placeholder.empty()
                    st.error(f"❌ Detection failed: {e}")

        elif submitted:
            st.warning("⚠️ Please upload an image to proceed.")

    # Always display the image and AI evaluation if they exist in session state
    # even if dialog is open
    if st.session_state.get('uploaded_file'):
        # Display the image that was uploaded
        img = Image.open(st.session_state['uploaded_file'])
        col1, col2, col3 = st.columns([1, 3, 1])
        with col2:
            st.image(img, use_container_width=True)

        # Display AI evaluation if it exists
        if st.session_state.get('evaluation_result'):
            eval_result = st.session_state['evaluation_result']
            st.header("AI Evaluation")
            if eval_result.get("status") != "error" and "evaluation" in eval_result:
                with st.container(height=400, border=True):
                    st.markdown(eval_result["evaluation"], unsafe_allow_html=True)

                if "note" in eval_result:
                    st.info(eval_result["note"])
            else:
                st.warning(f"⚠️ Could not get AI evaluation: {eval_result.get('message', 'Unknown error')}")

    add_vertical_space(3)

    # Show report button if needed
    if st.session_state.get('show_report_button') and st.session_state.get('uploaded_file'):
        col1, col2, col3 = st.columns([0.45, 0.1, 0.45])
        with col2:
            with stylable_container(key="report_button", css_styles=purple_button_style):
                if st.button("Send Report", use_container_width=True):
                    # Set dialog_open flag to preserve state during dialog
                    st.session_state['dialog_open'] = True
                    display_report_form(st.session_state['uploaded_file'])

    # Feedback form
    col1,col2,col3 = st.columns([0.25,0.5,0.25])
    with col2:
        if st.session_state.get('uploaded_file') and st.session_state.get('model_results'):
            st.markdown("### 📝 Feedback on AI Detection")
            st.markdown("Help us improve by providing feedback on the AI's performance.")
            with stylable_container(key="hover_feedback",css_styles=hover_text_purple)
                with st.expander("What does your feedback help with?", expanded=False):
                    st.markdown("""
                    Your feedback directly helps our AI models learn and improve:
                    - We use it to adjust detection sensitivity for different urban problems
                    - Comments about missed issues help us create better training data
                    - Regular feedback helps us measure model performance over time
                    """)

            with stylable_container(key="feedback_radio_btn",css_styles=radio_button_style):
                feedback_correct = st.radio(
                    "Did the AI detect the issues correctly?",
                    options=["Yes", "No"],
                    key="feedback_correct"
                )

            feedback_comments = st.text_area(
                "What was wrong or could be improved? (Optional)",
                key="feedback_comments"
            )

        with stylable_container("feedback_button", css_styles=purple_button_style):
            submit_feedback = st.button("Submit Feedback")

        if submit_feedback:
            with st.spinner("Submitting feedback..."):
                feedback_data = {
                    "correct": feedback_correct,
                    "comments": feedback_comments,
                    "detections": st.session_state.get('model_results'),
                    "username": st.session_state.get("username", "anonymous")
                }
                try:
                    response = requests.post(
                        "http://localhost:5000/submit_feedback",
                        json=feedback_data,
                        timeout=10
                    )
                    if response.status_code == 200:
                        st.success("✅ Feedback submitted successfully. Thank you!")
                        st.balloons()
                        # Clear the form
                        st.session_state.feedback_comments = ""
                    else:
                        st.error(f"❌ Failed to submit feedback: {response.text}")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

#viespa

