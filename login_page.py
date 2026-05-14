import streamlit as st
from auth import login_user, register_user


def show_login_page() -> None:
    """
    Renders the full-screen login / register UI.
    Sets st.session_state.logged_in and st.session_state.user on success,
    then calls st.rerun() so the main app renders immediately.
    """
    st.markdown(
        """
        <div style="text-align:center; padding: 2.5rem 0 1rem;">
            <h1 style="font-size:2.4rem; margin-bottom:0.3rem;">🛍️ E-Commerce AI Support</h1>
            <p style="color:#6c757d; font-size:1.05rem; margin-top:0;">
                Sign in to access your personalised support experience
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Centre the form card
    left, center, right = st.columns([1, 1.6, 1])
    with center:
        tab_login, tab_register = st.tabs(["🔐  Login", "✏️  Create Account"])

        # ── LOGIN ──────────────────────────────────────────────────────────────
        with tab_login:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.form("login_form", clear_on_submit=False):
                username = st.text_input(
                    "Username or Email",
                    placeholder="Enter your username or email",
                )
                password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Enter your password",
                )
                submitted = st.form_submit_button(
                    "Login", use_container_width=True, type="primary"
                )

            if submitted:
                if not username or not password:
                    st.error("Please fill in both fields.")
                else:
                    with st.spinner("Authenticating…"):
                        result = login_user(username, password)
                    if result["success"]:
                        st.session_state.logged_in = True
                        st.session_state.user = result["user"]
                        st.success(f"Welcome back, {result['user']['full_name']}!")
                        st.rerun()
                    else:
                        st.error(result["message"])

        # ── REGISTER ───────────────────────────────────────────────────────────
        with tab_register:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.form("register_form", clear_on_submit=False):
                full_name = st.text_input("Full Name", placeholder="e.g. Ali Hassan")
                reg_username = st.text_input(
                    "Username", placeholder="Letters, numbers and _ only"
                )
                reg_email = st.text_input(
                    "Email Address", placeholder="you@example.com"
                )
                reg_password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="At least 6 characters",
                )
                reg_confirm = st.text_input(
                    "Confirm Password",
                    type="password",
                    placeholder="Repeat your password",
                )
                reg_submitted = st.form_submit_button(
                    "Create Account", use_container_width=True, type="primary"
                )

            if reg_submitted:
                if not all([full_name, reg_username, reg_email, reg_password, reg_confirm]):
                    st.error("Please fill in all fields.")
                elif reg_password != reg_confirm:
                    st.error("Passwords do not match.")
                else:
                    with st.spinner("Creating your account…"):
                        result = register_user(reg_username, reg_email, full_name, reg_password)
                    if result["success"]:
                        st.session_state.logged_in = True
                        st.session_state.user = result["user"]
                        st.success("Account created! Welcome aboard.")
                        st.rerun()
                    else:
                        st.error(result["message"])

    # Footer note
    st.markdown(
        "<p style='text-align:center; color:#adb5bd; font-size:0.8rem; margin-top:2rem;'>"
        "Your data is stored securely and never shared with third parties."
        "</p>",
        unsafe_allow_html=True,
    )
