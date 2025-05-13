import streamlit as st
import re
import requests
import time
from streamlit_extras.stylable_container import stylable_container
from frontend.styles import purple_button_style

API_ENDPOINT = "http://localhost:5000/contact"

def is_valid_email(email):
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, email) is not None

@st.dialog("📬 Contact Us")
def show_contact_form():
    st.markdown("### We'd love to hear from you!")

    first_name = st.text_input("First Name")
    last_name = st.text_input("Last Name")
    email = st.text_input("Email")
    message = st.text_area("Message (minimum 50 characters)")
    with stylable_container("upload_button", css_styles=purple_button_style):
        if st.button("Submit"):
            if not first_name or not last_name or not email or not message:
                st.warning("Please fill in all fields.")
            elif not is_valid_email(email):
                st.warning("Please enter a valid email address.")
            elif len(message.strip()) < 50:
                st.warning("Your message must be at least 50 characters long.")
            else:
                payload = {
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "message": message
                }

                try:
                    response = requests.post(API_ENDPOINT, json=payload)
                    result = response.json()
                    if result.get("status") == "success":
                        st.success("✅ Thank you! Your message has been sent successfully.")
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.error(f"❌ Failed: {result.get('message')}")
                except Exception as e:
                    st.error(f"❌ An error occurred while sending your message: {e}")

def show_contact():
    if "token" not in st.session_state or not st.session_state["token"]:
        st.error("🔒 Please log in to access this page.")
        st.stop()
    if not st.session_state.get("backend_available", False):
        st.warning("⚠️ Contact form requires connection to the backend server, which is currently unavailable.")
        if st.button("Retry Connection"):
            try:
                requests.get("http://localhost:5000/", timeout=0.5)
                st.session_state.backend_available = True
                st.rerun()
            except:
                st.error("Still unable to connect to backend server")
        return


    col1,col2,col3 = st.columns([0.25,0.5,0.25])
    with col2:
        st.markdown("<h1 style='text-align: center;'>Contact</h1>", unsafe_allow_html=True)

        st.markdown("""
        <p style='text-align: center; font-size: 18px;'>
        We appreciate your feedback — it helps us improve and make TownSense better for everyone. <br>
        Do not hesitate to reach out if you have any questions, suggestions, or concerns. <br>
        Press the button below to send us a message.
        </p>
        """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([0.45,0.1,0.45])
    with col2:
        with stylable_container(key="contact_button", css_styles=purple_button_style):
            if st.button("Contact Us", use_container_width=True):
                show_contact_form()