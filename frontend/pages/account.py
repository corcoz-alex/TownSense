import streamlit as st
import requests
from streamlit_extras.stylable_container import stylable_container

# --- Constants ---
API_BASE = "http://localhost:5000"

# --- Helpers ---
def api_url(path):
    return f"{API_BASE}/{path}"

def post_api(path, payload):
    try:
        res = requests.post(api_url(path), json=payload)
        return res.json()
    except Exception as e:
        st.error("⚠️ Failed to connect to the backend.")
        st.exception(e)
        return {"status": "error", "message": str(e)}

def handle_password_reset():
    if st.session_state.reset_step == 1:
        email = st.text_input("Enter your email to receive a reset code")
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

        if st.button("Cancel Reset"):
            st.session_state.reset_step = 1
            st.rerun()

# --- Main UI Entry ---
def show_account():
    # --- Initial State ---
    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "login"
    if "token" not in st.session_state:
        st.session_state.token = None
    if "reset_step" not in st.session_state:
        st.session_state.reset_step = 1

    # --- Global Style Injection ---
    st.markdown("""
    <style>
        [data-testid="stExpander"] {
            background-color: white;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            padding: 10px;
        }
        [data-testid="stExpander"] > div {
            background-color: white;
        }
        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea {
            background-color: #f9f9f9;
            border: 1px solid #ddd;
            border-radius: 6px;
            padding: 6px 10px;
            font-size: 14px;
        }
        [data-testid="stTextInput"] input:focus,
        [data-testid="stTextArea"] textarea:focus {
            outline: none;
            border: 1px solid #726d57;
            box-shadow: 0 0 0 1px #726d57;
        }
    </style>
    """, unsafe_allow_html=True)

    # --- Logged In View ---
    if st.session_state.token:
        st.title(f"👤 Welcome, {st.session_state.get('username', 'User')}!")
        st.markdown("---")
        st.markdown("### ✏️ Account Customization")

        st.text_input("Change display name", value=st.session_state.get("username", ""))
        st.text_area("Bio")
        st.file_uploader("Profile picture", type=["jpg", "jpeg", "png"])
        st.button("Save Changes")
        st.info("This section is for demo only. Profile updates not yet implemented.")

        st.markdown("---")
        col1, col2, col3 = st.columns([2, 1, 2])
        with col1:
            with stylable_container(
                key="logout_button",
                css_styles="""
                    button {
                        background-color: #FF7878;
                        color: black;
                    }
                    button:focus {
                        outline: none;
                        box-shadow: 0 0 0 2px white;
                    }
                """,
            ):
                if st.button("Logout"):
                    st.session_state.clear()
                    st.rerun()

    else:
        # --- Auth Toggle ---
        if st.session_state.auth_mode == "login":
            st.title("🔐 Login")
            if st.button("Don't have an account? Register here"):
                st.session_state.auth_mode = "register"
                st.rerun()
        else:
            st.title("📝 Register")
            if st.button("Already have an account? Log in here"):
                st.session_state.auth_mode = "login"
                st.rerun()

        # --- Login Form ---
        if st.session_state.auth_mode == "login":
            with st.form("login_form"):
                username_or_email = st.text_input("Username or Email")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Login")

                if submitted:
                    data = post_api("login", {"username_or_email": username_or_email, "password": password})
                    if data.get("status") == "success":
                        st.session_state.token = data["token"]
                        st.session_state.username = data["username"]
                        st.success("✅ Logged in successfully")
                        st.rerun()
                    else:
                        st.error(data.get("message"))

            with st.expander("Reset your password"):
                handle_password_reset()

        # --- Register Form ---
        if st.session_state.auth_mode == "register":
            with st.form("register_form"):
                email = st.text_input("Email")
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")
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
