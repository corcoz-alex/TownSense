import streamlit as st
import requests
from PIL import Image
from streamlit_extras.add_vertical_space import add_vertical_space
from streamlit_extras.stylable_container import stylable_container

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

    if st.button("📤 Submit Report"):
        if not location.strip() or len(details.strip()) < 20:
            st.warning("Please fill all fields correctly.")
            return

        result = send_report_to_backend(location, details, uploaded_file)

        if result.get("status") == "success":
            st.success("✅ Report submitted successfully!")
        else:
            st.error(f"❌ Error: {result.get('message')}")

# Add a white-colored box for the title
with st.container():
    st.markdown(
        """
        <style>
        .title-box {
            background-color: white;
            padding: 2spx;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            text-align: center;
        }
        </style>
        <div class="title-box">
        <h1>🔍 AI Detection Tool</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

add_vertical_space(5)

# Add a white-colored box for the form
with st.container():
    st.markdown(
        """
        <style>
        .white-box {
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        </style>
        <div class="white-box">
        <h3>Welcome to the AI Detection Tool</h3>
        <p>Upload an image to analyze it using our AI-powered detection system. The results will show detected objects along with their confidence levels and bounding boxes.</p>
        """,
        unsafe_allow_html=True,
    )

add_vertical_space(2)
status = False

with st.form("upload_form", clear_on_submit=True):
    uploaded_file = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])
    with stylable_container(
            key="modified_button",
            css_styles="""
                button {
                    background-color: #262730;
                    color: white;
                }
                button:focus {
                    outline: none;
                    box-shadow: 0 0 0 2px white;
                }
                """,
    ):
        submitted = st.form_submit_button("Analyze")

    if submitted:
        if uploaded_file:
            st.session_state['uploaded_file'] = uploaded_file  # 🟢 Save uploaded file in session
            st.text("Original Image:")
            st.image(Image.open(uploaded_file), use_container_width=True)

            with st.spinner("Processing your image..."):
                try:
                    files = {
                        "image": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
                    }
                    response = requests.post("http://localhost:5000/upload", files=files, timeout=10)
                    response.raise_for_status()

                    data = response.json()
                    model_results = data.get("detected_objects", {})
                    # Display annotated image from backend
                    if "image" in data and any(model_results.values()):
                        st.text("Image with detected objects:")
                        st.image(
                            f"data:image/png;base64,{data['image']}",
                            use_container_width=True
                        )

                    if any(model_results.values()):
                        st.session_state['show_report_button'] = True  # 🟢 Flag to show report button
                        st.success("Objects detected:")
                        for model_name, objects in model_results.items():
                            if objects:
                                with st.expander(f"{model_name.title()} ({len(objects)} detected)", expanded=False):
                                    for obj in objects:
                                        st.write(
                                            f"• **{obj['name']}** ({obj['confidence'] * 100:.1f}%) — BBox: `{obj['bbox']}`")
                            else:
                                st.info(f"No {model_name} detected")
                    else:
                        st.warning("No objects detected in any category.")
                        st.session_state['show_report_button'] = False

                except requests.exceptions.ConnectionError:
                    st.error("Failed to connect to the backend. Please ensure the server is running.")
                except requests.exceptions.Timeout:
                    st.error("The request timed out. Please try again later.")
                except requests.exceptions.RequestException as e:
                    st.error(f"Request failed: {e}")
        else:
            st.warning("Please upload an image.")

css = """
<style>
    [data-testid="stForm"] {
        background: white;
    }
</style>
"""
st.write(css, unsafe_allow_html=True)

if st.session_state.get('show_report_button') and st.session_state.get('uploaded_file'):
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        with stylable_container(
            key="report_button",
            css_styles="""
                button {
                background-color: #FF7878;
                color: black;
                }
            """,
        ):
            if st.button("Send Report"):
                display_report_form(st.session_state['uploaded_file'])