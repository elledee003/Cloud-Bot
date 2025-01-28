import streamlit as st
import requests
import yaml

# Load config
def load_config():
    with open("config.yaml", "r") as file:
        return yaml.safe_load(file)

config = load_config()

# Streamlit UI
st.title("Crypto Trading Bot")
st.write("Welcome to the Crypto Trading Bot!")

# Example functionality
token_address = st.text_input("Enter Token Address")
if st.button("Check Token"):
    st.write(f"Checking token: {token_address}")

    # Fetch token data from DexScreener
    dex_api_url = config["dex_api_url"]
    response = requests.get(f"{dex_api_url}{token_address}")
    if response.status_code == 200:
        token_data = response.json()
        st.write("Token Data:", token_data)
    else:
        st.error("Failed to fetch token data.")
