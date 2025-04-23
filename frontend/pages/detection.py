import streamlit as st
import requests
from PIL import Image
from streamlit_extras.add_vertical_space import add_vertical_space
from streamlit_extras.stylable_container import stylable_container

purple_button_style = """
    button {
        background-color: #775cff;
        color: white;
        border-radius: 6px;
        padding: 8px 16px;
        transition: background-color 0.5s ease-in-out, color 0.5s ease-in-out;
    }
    button:hover {
        background-color: #4f2ef3;
        color: white;
    }
"""

# --- Helpers ---
def send_report_to_backend(location, details, uploaded_file):
    try:
        files = {
            "image": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
        }
        data = {
            "location": location,
            "details": details
        }
        response = requests.post("http://localhost:5000/send_email", data=data, files=files, timeout=10)
        return response.json()
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
            result = send_report_to_backend(location, details, uploaded_file)
            if result.get("status") == "success":
                st.success("✅ Report submitted successfully!")
            else:
                st.error(f"❌ Error: {result.get('message')}")

# --- Page ---
def show_detection():
    st.markdown("""
    <style>
        .title-box {
            background-color: white;
            padding: 2spx;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            text-align: center;
        }
        .white-box {
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        [data-testid="stForm"] {
            background: white;
        }
    </style>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown("""
        <div class="title-box">
        <h1>🔍 AI Detection Tool</h1>
        </div>
        """, unsafe_allow_html=True)

    add_vertical_space(5)

    with st.container():
        st.markdown("""
        <div class="white-box">
        <h3>Welcome to the AI Detection Tool</h3>
        <p>Upload an image to analyze it using our AI-powered detection system. The results will show detected objects along with their confidence levels and bounding boxes.</p>
        </div>
        """, unsafe_allow_html=True)

    add_vertical_space(2)

    with st.form("upload_form", clear_on_submit=True):
        with stylable_container("upload_button", css_styles=purple_button_style):
            uploaded_file = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])
        with stylable_container("analyze_button", css_styles=purple_button_style):
            submitted = st.form_submit_button("Analyze")

        if submitted and uploaded_file:
            st.session_state['uploaded_file'] = uploaded_file
            st.text("Original Image:")
            st.image(Image.open(uploaded_file), use_container_width=True)
            with st.spinner("Analyzing..."):
                try:
                    files = {
                        "image": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
                    }
                    response = requests.post("http://localhost:5000/upload", files=files, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    model_results = data.get("detected_objects", {})
                    if "image" in data and any(model_results.values()):
                        st.text("Image with detected objects:")
                        st.image(f"data:image/png;base64,{data['image']}", use_container_width=True)
                    if any(model_results.values()):
                        st.session_state['show_report_button'] = True
                        st.success("Objects detected:")
                        for model_name, objects in model_results.items():
                            if objects:
                                with st.expander(f"{model_name.title()} ({len(objects)} detected)", expanded=False):
                                    for obj in objects:
                                        st.write(
                                            f"• **{obj['name']}** ({obj['confidence'] * 100:.1f}%) — BBox: `{obj['bbox']}`"
                                        )
                            else:
                                st.info(f"No {model_name} detected")
                    else:
                        st.warning("No objects detected in any category.")
                        st.session_state['show_report_button'] = False

                except requests.exceptions.RequestException as e:
                    st.error(f"Request failed: {e}")
        elif submitted:
            st.warning("Please upload an image.")

    if st.session_state.get('show_report_button') and st.session_state.get('uploaded_file'):
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            with stylable_container(
                key="report_button",
                css_styles="""
                button {
                    background-color: #fb0231;
                    color: white;
                    font-weight: bold;
                    border-radius: 6px;
                    padding: 8px 16px;
                    transition: background-color 0.5s ease-in-out, color 0.5s ease-in-out;
                }
                button:hover {
                    background-color: #c90227;
                    color: white;
                }
                """,
            ):
                if st.button("Send Report"):
                    display_report_form(st.session_state['uploaded_file'])
