from time import sleep
import base64
import io
import os
import requests
from PIL import Image
import streamlit as st
from streamlit_avatar import avatar
from dotenv import load_dotenv
from streamlit_cookies_manager import EncryptedCookieManager
from streamlit_extras.add_vertical_space import add_vertical_space
from streamlit_extras.stylable_container import stylable_container
from frontend.styles import purple_button_style, hover_text_purple
from datetime import datetime, timedelta, timezone

# --- Load environment ---
load_dotenv()  # ✅ Load .env at start

# --- Check COOKIE_SECRET ---
cookie_secret = os.getenv("COOKIE_SECRET")
if not cookie_secret:
    st.error("🚨 COOKIE_SECRET missing in your .env! Please generate and set it.")
    st.stop()

# --- Setup cookies ---
cookies = EncryptedCookieManager(prefix="townsense", password=cookie_secret)
if not cookies.ready():
    st.stop()

API_BASE = "http://localhost:5000"

# --- Load custom checkbox SVG ---
svg_path = os.path.join(os.path.dirname(__file__), "..", "assets", "checkmark.svg")
with open(svg_path, "rb") as f:
    encoded_svg = base64.b64encode(f.read()).decode("utf-8")

remember_checkbox_style = f"""
div[data-testid="stCheckbox"] {{
    background-color: white;
    padding: 6px 12px;
    border-radius: 2px;
}}
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

# --- Helper API functions ---
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
        st.error("⚠️ Failed to connect to backend.")
        return {"status": "error", "message": str(e)}

# --- Password Reset ---
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

# --- Compress Uploaded Image ---
def compress_image(uploaded_file, max_width=300):
    img = Image.open(uploaded_file)
    if img.width > max_width:
        ratio = max_width / float(img.width)
        height = int(float(img.height) * ratio)
        img = img.resize((max_width, height))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()

# --- Main UI ---
def show_account():
    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "login"
    # --- Initialize Session State from Cookies ---
    if "token" not in st.session_state:
        # Check cookie for persistent login
        if cookies.get("token") and cookies.get("expiry"):
            expiry = datetime.fromisoformat(cookies.get("expiry"))
            if expiry > datetime.now(timezone.utc):
                st.session_state.token = cookies.get("token")
                st.session_state.username = cookies.get("username", "User")
                st.session_state.bio = cookies.get("bio", "")
                st.session_state.profile_picture = cookies.get("profile_picture", "")
                st.session_state.remember_me = True
            else:
                # Token expired, clear cookies
                cookies.pop("token", None)
                cookies.pop("username", None)
                cookies.pop("expiry", None)
                cookies.save()
                st.session_state.token = None
        else:
            st.session_state.token = None
    if "reset_step" not in st.session_state:
        st.session_state.reset_step = 1
    if "backend_available" not in st.session_state:
        st.session_state.backend_available = True

    if st.session_state.token:
        st.title("Account Settings")
        st.markdown("---")

        col1, col2 = st.columns(2, gap='large')
        with col2:
            st.header("Preview")
            add_vertical_space(4)
            avatar_items = []
            if st.session_state.get("profile_picture"):
                avatar_items.append({
                    "url": f"data:image/png;base64,{st.session_state['profile_picture']}",
                    "size": 200,
                    "title": st.session_state.get("username", "User"),
                    "caption": st.session_state.get("bio", "No bio yet"),
                    "key": "profile_avatar",
                })
            else:
                avatar_items.append({
                    "url": f"https://api.dicebear.com/7.x/identicon/svg?seed={st.session_state.get('username', 'User')}",
                    "size": 200,
                    "title": st.session_state.get("username", "User"),
                    "caption": st.session_state.get("bio", "No bio yet"),
                    "key": "profile_avatar_fallback",
                })

            avatar(avatar_items)

        with col1:
            st.header("Account Customization")
            new_display_name = st.text_input("Change display name", value=st.session_state.get("username", ""))
            max_bio_length = 250
            current_bio = st.session_state.get("bio", "")
            bio = st.text_area(
                "Bio",
                value=current_bio,
                max_chars=max_bio_length,
                height=120,
                key="bio_input"
            )

            with stylable_container("profile_upload_button", css_styles=purple_button_style):
                uploaded_picture = st.file_uploader("Profile picture", type=["jpg", "jpeg", "png"])

        with stylable_container("save_changes_button", css_styles=purple_button_style):
            if st.button("Save Changes"):
                new_display_name = new_display_name.strip()
                bio = bio.strip()
                if len(new_display_name) < 3 or len(new_display_name) > 30:
                    st.warning("Username must be between 3 and 30 characters.")
                    return
                if len(bio) > 250:
                    st.warning("Bio must be 250 characters or fewer.")
                    return

                payload = {
                    "username": st.session_state.get("username"),
                    "new_display_name": new_display_name,
                    "bio": bio
                }

                if uploaded_picture:
                    if uploaded_picture.size > 1 * 1024 * 1024:
                        st.warning("Profile picture must be smaller than 1MB.")
                        return
                    compressed_image = compress_image(uploaded_picture)
                    payload["profile_picture"] = base64.b64encode(compressed_image).decode("utf-8")
                    st.session_state.profile_picture = payload["profile_picture"]

                response = post_api("update_profile", payload)

                if response.get("status") == "success":
                    st.success("✅ Profile updated successfully!")
                    st.session_state.username = new_display_name
                    st.session_state.bio = bio
                    sleep(1)
                    st.rerun()
                else:
                    st.error(f"❌ Failed to update profile: {response.get('message')}")

        st.markdown("---")
        col1, col2, col3 = st.columns([2, 1, 2])
        with col1:
            with stylable_container("logout_button", css_styles=purple_button_style):
                if st.button("Logout"):
                    cookies.pop("token", None)
                    cookies.pop("username", None)
                    cookies.pop("expiry", None)
                    cookies.save()
                    st.session_state.clear()
                    st.rerun()
    else:
        if st.session_state.auth_mode == "login":
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.title("Login")
                with stylable_container("switch_to_register", css_styles=purple_button_style):
                    if st.button("Don't have an account? Register here"):
                        st.session_state.auth_mode = "register"
                        st.rerun()
        else:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.title("Sign up")
                with stylable_container("switch_to_login", css_styles=purple_button_style):
                    if st.button("Already have an account? Log in here"):
                        st.session_state.auth_mode = "login"
                        st.rerun()

        if st.session_state.auth_mode == "login":
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                with st.form("login_form"):
                    username_or_email = st.text_input("Username or Email")
                    password = st.text_input("Password", type="password")
                    with stylable_container("remember_me", css_styles=remember_checkbox_style):
                        remember = st.checkbox("Remember Me?", value=False)
                    with stylable_container("login_button", css_styles=purple_button_style):
                        submitted = st.form_submit_button("Login")

                    if submitted:
                        data = post_api("login", {
                            "username_or_email": username_or_email,
                            "password": password,
                            "remember_me": remember
                        })

                        if data.get("status") == "success":
                            st.session_state.token = data["token"]
                            st.session_state.username = data["username"]
                            st.session_state.bio = data.get("bio", "")
                            st.session_state.profile_picture = data.get("profile_picture", "")
                            st.success("✅ Logged in successfully!")

                            if remember:
                                expiry_time = datetime.now(timezone.utc) + timedelta(hours=24)
                                cookies["token"] = data["token"]
                                cookies["username"] = data["username"]
                                cookies["bio"] = data.get("bio", "")
                                cookies["profile_picture"] = data.get("profile_picture", "")
                                cookies["expiry"] = expiry_time.isoformat()
                                cookies.save()

                            st.rerun()
                        else:
                            st.error(data.get("message"))

                with stylable_container("reset_pass", css_styles=hover_text_purple):
                    with st.expander("Reset your password"):
                        handle_password_reset()

        elif st.session_state.auth_mode == "register":
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
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
                                st.success("✅ Registered successfully. Please log in!")
                                st.session_state.auth_mode = "login"
                                st.rerun()
                            else:
                                st.error(data.get("message"))
