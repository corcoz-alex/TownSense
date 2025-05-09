import streamlit as st
import requests
from PIL import Image
from streamlit_extras.add_vertical_space import add_vertical_space
from streamlit_extras.stylable_container import stylable_container
from frontend.styles import purple_button_style, hover_text_purple
import io

# --- Helpers ---
def send_report_to_backend(location, details, uploaded_file):
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
        return response.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

def load_lottie_url(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

def send_to_evaluation(detections, base64_image=None):
    """Send detection results to the evaluation endpoint for AI analysis"""
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
    location = st.text_input("📍 Location")
    details = st.text_area("🧾 Problem Details (minimum 20 characters)")

    with stylable_container("submit_report", css_styles=purple_button_style):
        if st.button("📤 Submit Report"):
            if not location.strip() or len(details.strip()) < 20:
                st.warning("Please fill all fields correctly.")
                return

            with st.spinner("🚀 Submitting your report..."):
                try:
                    result = send_report_to_backend(location, details, uploaded_file)
                    if result.get("status") == "success":
                        st.success("✅ Report submitted successfully!")
                        st.balloons()
                    else:
                        st.error(f"❌ Error: {result.get('message')}")
                except requests.exceptions.ConnectionError as e:
                    if "10054" in str(e):
                        st.success("✅ Report was submitted! (Connection closed early)")
                        st.balloons()
                    else:
                        st.error(f"❌ Connection error: {str(e)}")
                except Exception as e:
                    st.error(f"❌ Unexpected error: {str(e)}")

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

    # Inject custom CSS for overlay effect
    st.markdown(f"<style>{ai_analysis_overlay_css}</style>", unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align: center;">
        <h1 style="margin-bottom: 0;">AI Urban Problem Detector</h1>
        <p style="font-size: 1.2rem; color: gray;">Analyze street images and automatically detect urban issues.</p>
    </div>
    """, unsafe_allow_html=True)

    add_vertical_space(3)

    with st.container():
        st.markdown("### Upload an Image")
        st.markdown("Select a photo showing a street, road, or urban area to start detection.")
        st.info("💡 Large images will be automatically resized for optimal processing.")

        with st.form("upload_form", clear_on_submit=True):
            with stylable_container("upload_button", css_styles=purple_button_style):
                uploaded_file = st.file_uploader("Choose a file", type=["jpg", "jpeg", "png"])
            add_vertical_space(1)
            with stylable_container("analyze_button", css_styles=purple_button_style):
                submitted = st.form_submit_button("Analyze")

        if submitted and uploaded_file:
            st.success("✅ Image uploaded successfully.")
            
            # Display image with reasonable size limits
            img = Image.open(uploaded_file)
            img_width, img_height = img.size
            
            # Show image dimensions for debugging
            st.caption(f"Image dimensions: {img_width} × {img_height} pixels")
            
            # Create columns to make image narrower
            col1, col2, col3 = st.columns([1, 3, 1])
            
            with col2:
                # Display original image with smaller width
                st.image(img, use_container_width=True, caption="Original uploaded image")
            
            # Create a container for the results that will be blurred during AI analysis
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

                    # Always send to evaluation, regardless of whether local models detected anything
                    eval_result = send_to_evaluation(model_results, data.get('image'))
                    
                    # Clear the overlay once processing is complete
                    overlay_placeholder.empty()
                    
                    with results_container:

                        
                        if eval_result.get("status") != "error" and "evaluation" in eval_result:
                            with stylable_container(
                                key="ai_evaluation_container",
                                css_styles="""
                                div {
                                    background-color: #f8f9fa;
                                    border-left: 4px solid #775cff;
                                    padding: 20px;
                                    border-radius: 4px;
                                    margin: 20px 0;
                                }
                                """
                            ):
                                ai_provider = "GitHub GPT-4.1" if "note" not in eval_result else "Local AI"
                                st.markdown(f"### 🤖 AI Evaluation ({ai_provider})")
                                st.markdown(eval_result["evaluation"])

                                # Display a note if using fallback analysis
                                if "note" in eval_result:
                                    st.info(eval_result["note"])
                            
                            # Note: Removed expanders for marked images as requested

                            # Always enable report button after analysis
                            st.session_state['show_report_button'] = True
                        else:
                            st.warning(f"⚠️ Could not get AI evaluation: {eval_result.get('message', 'Unknown error')}")
                            st.info("The system will still allow you to submit a report based on the detected issues.")
                            st.session_state['show_report_button'] = True

                    # Save the uploaded file AFTER successful analysis
                    st.session_state['uploaded_file'] = uploaded_file

                except requests.exceptions.RequestException as e:
                    # Clear the overlay on error
                    overlay_placeholder.empty()
                    st.error(f"❌ Detection failed: {e}")

        elif submitted:
            st.warning("⚠️ Please upload an image to proceed.")

    add_vertical_space(3)

    if st.session_state.get('show_report_button') and st.session_state.get('uploaded_file'):
        col1, col2, col3 = st.columns([1.316,1,1])
        with col2:
            with stylable_container(
                key="report_button",
                css_styles="""
                button {
                    background-color: #fb0231;
                    color: white;
                    font-weight: bold;
                    font-size: 1.1rem;
                    border-radius: 8px;
                    padding: 12px 24px;
                    box-shadow: 0px 4px 10px rgba(0,0,0,0.15);
                    transition: background-color 0.3s ease-in-out, transform 0.3s ease;
                }
                button:hover {
                    background-color: #c90227;
                    transform: scale(1.05);
                }
                """,
            ):
                if st.button("Send Report"):
                    display_report_form(st.session_state['uploaded_file'])
