import streamlit as st

st.set_page_config(
    page_title="MGASLProducts Login Test",
    layout="centered",
)

st.title("MGASLProducts — Google login test")
st.caption(
    "This temporary page tests only Google authentication. "
    "It does not load the DXF generator or Google Sheets."
)

required_keys = (
    "redirect_uri",
    "cookie_secret",
    "client_id",
    "client_secret",
    "server_metadata_url",
)

try:
    auth_settings = st.secrets["auth"]
except Exception:
    st.error("The [auth] section is missing from Streamlit Secrets.")
    st.stop()

missing_keys = [
    key for key in required_keys
    if not str(auth_settings.get(key, "")).strip()
]

if missing_keys:
    st.error(
        "Missing authentication values: "
        + ", ".join(missing_keys)
    )
    st.stop()

redirect_uri = str(auth_settings["redirect_uri"]).strip()

st.success("The [auth] settings were loaded.")
st.code(f"Configured callback: {redirect_uri}")

expected_callback = (
    "https://mgaslappucts.streamlit.app/oauth2callback"
)

if redirect_uri != expected_callback:
    st.error(
        "The callback does not match the current app domain.\n\n"
        f"Expected: {expected_callback}"
    )
    st.stop()

if not st.user.is_logged_in:
    st.info("Authentication is configured. Press the button to test Google login.")

    if st.button(
        "Log in with Google",
        type="primary",
        use_container_width=True,
    ):
        st.login()

    st.stop()

st.success("Google login completed successfully.")
st.write(f"Name: {getattr(st.user, 'name', '')}")
st.write(f"Email: {getattr(st.user, 'email', '')}")

if st.button("Log out", use_container_width=True):
    st.logout()
