import streamlit as st
import requests
from PIL import Image
from streamlit_extras.add_vertical_space import add_vertical_space
from streamlit_extras.stylable_container import stylable_container
from frontend.styles import purple_button_style, hover_text_purple

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

# --- Page ---
def show_detection():
    if "token" not in st.session_state or not st.session_state["token"]:
        st.error("🔒 Please log in to access this page.")
        st.stop()

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

        with st.form("upload_form", clear_on_submit=True):
            with stylable_container("upload_button", css_styles=purple_button_style):
                uploaded_file = st.file_uploader("Choose a file", type=["jpg", "jpeg", "png"])
            add_vertical_space(1)
            with stylable_container("analyze_button", css_styles=purple_button_style):
                submitted = st.form_submit_button("Analyze")

        if submitted and uploaded_file:
            st.success("✅ Image uploaded successfully.")
            st.image(Image.open(uploaded_file), use_container_width=True)

            with st.spinner("Analyzing image with AI models..."):
                try:
                    files = {
                        "image": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
                    }
                    response = requests.post("http://localhost:5000/upload", files=files, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    model_results = data.get("detected_objects", {})

                    if "image" in data:
                        st.markdown("### 🖼️ Detection Results")
                        st.image(f"data:image/png;base64,{data['image']}", use_container_width=True)

                    if any(model_results.values()):
                        st.success("✅ Objects detected:")
                        for model_name, objects in model_results.items():
                            if objects:
                                with stylable_container(key=f"detection_expander_{model_name}", css_styles=hover_text_purple):
                                    with st.expander(f"🔎 {model_name.title()} ({len(objects)} detected)", expanded=False):
                                        for obj in objects:
                                            st.write(
                                                f"• **{obj['name']}** ({obj['confidence']*100:.1f}%) — BBox: `{obj['bbox']}`"
                                            )
                        st.session_state['show_report_button'] = True
                    else:
                        st.warning("⚠️ No detectable issues found in the uploaded image.")
                        st.session_state['show_report_button'] = False

                    # ✅ Save the uploaded file AFTER successful analysis
                    st.session_state['uploaded_file'] = uploaded_file

                except requests.exceptions.RequestException as e:
                    st.error(f"❌ Detection failed: {e}")

        elif submitted:
            st.warning("⚠️ Please upload an image to proceed.")

    add_vertical_space(3)

    if st.session_state.get('show_report_button') and st.session_state.get('uploaded_file'):
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 1, 1])
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
