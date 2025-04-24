import streamlit as st
import requests
import base64
import os
from streamlit_extras.stylable_container import stylable_container
from streamlit_cookies_manager import EncryptedCookieManager
from frontend.styles import purple_button_style, hover_text_purple

API_BASE = "http://localhost:5000"

svg_path = os.path.join(os.path.dirname(__file__), "..", "assets", "checkmark.svg")

with open(svg_path, "rb") as f:
    encoded_svg = base64.b64encode(f.read()).decode("utf-8")

remember_checkbox_style = f"""
/* Checkbox outer wrapper */
div[data-testid="stCheckbox"] {{
    background-color: white;
    padding: 6px 12px;
    border-radius: 2px;
}}

/* Visual box span - overrides Streamlit's checkmark with custom */
div[data-testid="stCheckbox"] .st-du {{
    background-image: url("data:image/svg+xml;base64,{encoded_svg}") !important;
    background-position: center center !important;
    background-repeat: no-repeat !important;
    background-size: contain !important;
    border: 1px solid black !important;
    border-radius: 2px !important;
    background-color: white !important;
}}
"""

cookies = EncryptedCookieManager(prefix="townsense", password=os.getenv("COOKIE_SECRET", "changeme"))
if not cookies.ready():
    st.stop()

def api_url(path):
    return f"{API_BASE}/{path}"

def post_api(path, payload):
    if not st.session_state.get("backend_available", False):
        st.warning("⚠️ Cannot connect to backend server")
        return {"status": "error", "message": "Backend server not available"}
    try:
        res = requests.post(api_url(path), json=payload, timeout=5)
        return res.json()
    except requests.exceptions.Timeout:
        st.error("⚠️ Request to backend timed out")
        return {"status": "error", "message": "Request timed out"}
    except Exception as e:
        st.error("⚠️ Failed to connect to the backend.")
        return {"status": "error", "message": str(e)}

def handle_password_reset():
    if st.session_state.reset_step == 1:
        email = st.text_input("Enter your email to receive a reset code")
        with stylable_container("send_reset_button", css_styles=purple_button_style):
            if st.button("Send Reset Code"):
                data = post_api("request-reset-code", {"email": email})
                if data.get("status") == "success":
                    st.session_state.reset_email = email
                    st.session_state.reset_step = 2
                    st.rerun()
                else:
                    st.error(data.get("message"))

    elif st.session_state.reset_step == 2:
        st.success("✅ Reset code sent. Please check your email.")
        code = st.text_input("Enter the 6-digit reset code")
        new_password = st.text_input("New password", type="password")
        confirm_password = st.text_input("Confirm new password", type="password")

        with stylable_container("reset_password_button", css_styles=purple_button_style):
            if st.button("Reset Password"):
                if new_password != confirm_password:
                    st.warning("Passwords do not match")
                    return
                payload = {
                    "email": st.session_state.reset_email,
                    "code": code,
                    "new_password": new_password
                }
                data = post_api("reset-password", payload)
                if data.get("status") == "success":
                    st.success("✅ Password reset successfully. Please log in.")
                    st.session_state.auth_mode = "login"
                    st.session_state.reset_step = 1
                    st.rerun()
                else:
                    st.error(data.get("message"))

        with stylable_container("cancel_reset_button", css_styles=purple_button_style):
            if st.button("Cancel Reset"):
                st.session_state.reset_step = 1
                st.rerun()

# --- Main UI ---
def show_account():
    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "login"
    if "token" not in st.session_state:
        # Auto-login from cookie
        if cookies.get("token"):
            st.session_state.token = cookies["token"]
            st.session_state.username = cookies.get("username", "User")
            st.session_state.remember_me = True
        else:
            st.session_state.token = None
    if "reset_step" not in st.session_state:
        st.session_state.reset_step = 1
    if "backend_available" not in st.session_state:
        st.session_state.backend_available = True

    # Logged in look
    if st.session_state.token:
        st.title(f"👤 Welcome, {st.session_state.get('username', 'User')}!")
        st.markdown("---")
        st.markdown("### ✏️ Account Customization")
        st.text_input("Change display name", value=st.session_state.get("username", ""))
        st.text_area("Bio")
        st.file_uploader("Profile picture", type=["jpg", "jpeg", "png"])
        with stylable_container("save_changes_button", css_styles=purple_button_style):
            st.button("Save Changes")
        st.info("This section is for demo only. Profile updates not yet implemented.")

        st.markdown("---")
        col1, col2, col3 = st.columns([2, 1, 2])
        with col1:
            with stylable_container("logout_button", css_styles=purple_button_style):
                if st.button("Logout"):
                    cookies["token"] = ""
                    cookies["username"] = ""
                    cookies.save()
                    st.session_state.clear()
                    st.rerun()

    else:
        if st.session_state.auth_mode == "login":
            st.title("🔐 Login")
            with stylable_container("switch_to_register", css_styles=purple_button_style):
                if st.button("Don't have an account? Register here"):
                    st.session_state.auth_mode = "register"
                    st.rerun()
        else:
            st.title("📝 Register")
            with stylable_container("switch_to_login", css_styles=purple_button_style):
                if st.button("Already have an account? Log in here"):
                    st.session_state.auth_mode = "login"
                    st.rerun()

        if st.session_state.auth_mode == "login":
            with st.form("login_form"):
                username_or_email = st.text_input("Username or Email")
                password = st.text_input("Password", type="password")
                with stylable_container("remember_checkbox", css_styles=remember_checkbox_style):
                    remember = st.checkbox("Remember Me?", value=False)

                with stylable_container("login_button", css_styles=purple_button_style):
                    submitted = st.form_submit_button("Login")

                if submitted:
                    data = post_api("login", {
                        "username_or_email": username_or_email,
                        "password": password
                    })
                    if data.get("status") == "success":
                        st.session_state.token = data["token"]
                        st.session_state.username = data["username"]
                        st.success("✅ Logged in successfully")

                        if remember:
                            cookies["token"] = data["token"]
                            cookies["username"] = data["username"]
                            cookies.save()

                        st.rerun()
                    else:
                        st.error(data.get("message"))
            with stylable_container("reset_pass", css_styles=hover_text_purple):
                with st.expander("Reset your password"):
                    handle_password_reset()

        elif st.session_state.auth_mode == "register":
            with st.form("register_form"):
                email = st.text_input("Email")
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")
                with stylable_container("register_button", css_styles=purple_button_style):
                    submitted = st.form_submit_button("Register")

                if submitted:
                    if password != confirm_password:
                        st.warning("Passwords do not match")
                    else:
                        data = post_api("register", {
                            "email": email,
                            "username": username,
                            "password": password
                        })
                        if data.get("status") == "success":
                            st.success("✅ Registered successfully. Please log in.")
                            st.session_state.auth_mode = "login"
                            st.rerun()
                        else:
                            st.error(data.get("message"))
