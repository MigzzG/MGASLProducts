import streamlit as st

st.set_page_config(
    page_title="MGASLProducts Test",
    layout="centered",
)

st.title("MGASLProducts deployment test")
st.success("The Streamlit app is running correctly.")
st.write("No Google login, no Google Sheets and no Secrets are being used.")
st.write("Repository: MigzzG/MGASLProducts")
st.write("Entrypoint: app.py")
