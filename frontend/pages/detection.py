import streamlit as st
import requests
from PIL import Image

st.title("🔍 AI Detection via Flask API")

with st.form("upload_form"):
    uploaded_file = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])
    submitted = st.form_submit_button("Analyze")

    if submitted:
        if uploaded_file:
            st.image(Image.open(uploaded_file), caption="Uploaded Image", use_container_width=True)

            with st.spinner("Sending to backend..."):
                try:
                    files = {
                        "image": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
                    }
                    response = requests.post("http://localhost:5000/upload", files=files)
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

                except requests.exceptions.RequestException as e:
                    st.error(f"Request failed: {e}")
        else:
            st.warning("Please upload an image.")
