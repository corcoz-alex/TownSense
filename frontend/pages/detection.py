import streamlit as st
import requests
from PIL import Image
from streamlit_extras.add_vertical_space import add_vertical_space
from streamlit_extras.stylable_container import stylable_container

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

with st.form("upload_form"):
    uploaded_file = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])
    with stylable_container(
            key="modified_button",
            css_styles="""
                button {
                    background-color: #262730;
                    color: white;
                }
                button:focus {
                    outline: white;
                    box-shadow: 0 0 0 2px white;
                }
                """,
    ):
        submitted = st.form_submit_button("Analyze")

    if submitted:
        if uploaded_file:
            st.image(Image.open(uploaded_file), caption="Uploaded Image", use_container_width=True)

            with st.spinner("Processing your image..."):
                try:
                    files = {
                        "image": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
                    }
                    response = requests.post("http://localhost:5000/upload", files=files, timeout=10)
                    response.raise_for_status()

                    data = response.json()
                    model_results = data.get("detected_objects", {})

                    if any(model_results.values()):
                        st.success("Objects detected:")
                        for model_name, objects in model_results.items():
                            if objects:
                                with st.expander(f"{model_name.title()} ({len(objects)} detected)", expanded=True):
                                    for obj in objects:
                                        st.write(f"• **{obj['name']}** ({obj['confidence']*100:.1f}%) — BBox: `{obj['bbox']}`")
                            else:
                                st.info(f"No {model_name} detected")
                    else:
                        st.warning("No objects detected in any category.")

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

