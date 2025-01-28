import streamlit as st
import requests
import yaml
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import telebot
import os

# Load config
def load_config():
    try:
        with open("config.yaml", "r") as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        st.error("Config file not found. Please ensure 'config.yaml' exists.")
        return {}

def save_config(config):
    with open("config.yaml", "w") as file:
        yaml.dump(config, file)

config = load_config()

# Load sensitive data securely
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", config.get("telegram_bot_token"))
TELEGRAM_CHAT_ID = config.get("telegram_chat_id", "TheRealJackPotTheBot")  # Default to provided chat ID

if not TELEGRAM_BOT_TOKEN:
    st.error("Telegram Bot Token is missing. Please set it in the environment variables or config file.")

# Initialize Telegram bot
telegram_bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Database setup
DATABASE_URL = config.get("database_url", "sqlite:///default.db")  # Default to SQLite for testing
engine = create_engine(DATABASE_URL)
Base = declarative_base()

class TokenData(Base):
    __tablename__ = "token_data"
    id = Column(Integer, primary_key=True)
    token_address = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    liquidity = Column(Float, nullable=False)
    dev_address = Column(String, nullable=True)  # Developer address
    fake_volume_ratio = Column(Float, nullable=True)  # Fake volume ratio
    is_bundled = Column(Boolean, nullable=False, default=False)  # Bundled supply flag
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)

# Fetch token data from DexScreener
def fetch_token_data(token_address):
    response = requests.get(f"{config.get('dex_api_url', '')}{token_address}")
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to fetch data for token: {token_address}")
        return None

# Fetch contract analysis from rugcheck.xyz
def fetch_rugcheck_data(token_address):
    params = {"token_address": token_address}
    response = requests.get(config.get("rugcheck_api_url", ""), params=params)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to fetch rugcheck data for token: {token_address}")
        return None

# Check if token is blacklisted
def is_blacklisted(token_data):
    token_address = token_data.get("address")
    dev_address = token_data.get("devAddress")

    if token_address in config.get("blacklist", {}).get("coins", []):
        return True
    if dev_address in config.get("blacklist", {}).get("devs", []):
        return True
    return False

# Apply filters
def apply_filters(token_data):
    liquidity = token_data.get("liquidity", 0)
    price_change = token_data.get("priceChange24h", 0)

    filters = config.get("filters", {})
    if liquidity < filters.get("min_liquidity", 0):
        return False
    if abs(price_change) > filters.get("max_price_change", 0):
        return False
    return True

# Save token data
def save_token_data(token_data):
    Session = sessionmaker(bind=engine)
    session = Session()
    token = TokenData(
        token_address=token_data['address'],
        price=token_data['price'],
        volume=token_data['volume'],
        liquidity=token_data['liquidity'],
        dev_address=token_data.get('devAddress'),
        fake_volume_ratio=token_data.get('fake_volume_ratio'),
        is_bundled=token_data.get('is_bundled', False)
    )
    session.add(token)
    session.commit()
    session.close()

# Send Telegram notification
def send_telegram_notification(message):
    try:
        telegram_bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as e:
        st.error(f"Failed to send Telegram message: {e}")

# Streamlit UI
st.title("Crypto Trading Bot")

# Sidebar for configuration
st.sidebar.header("Configuration")
min_liquidity = st.sidebar.number_input("Minimum Liquidity (USD)", value=config.get("filters", {}).get("min_liquidity", 0))
max_price_change = st.sidebar.number_input("Maximum Price Change (%)", value=config.get("filters", {}).get("max_price_change", 0))

if st.sidebar.button("Update Filters"):
    config["filters"]["min_liquidity"] = min_liquidity
    config["filters"]["max_price_change"] = max_price_change
    save_config(config)
    st.sidebar.success("Filters updated!")

# Main UI
st.header("Token Monitoring")
token_address = st.text_input("Enter Token Address")

if st.button("Check Token"):
    token_data = fetch_token_data(token_address)
    if token_data and not is_blacklisted(token_data) and apply_filters(token_data):
        save_token_data(token_data)
        st.success(f"Token {token_address} is valid and saved to the database.")
    else:
        st.error(f"Token {token_address} is invalid or blacklisted.")

# Display blacklists
st.header("Blacklists")
st.subheader("Blacklisted Coins")
st.write(config.get("blacklist", {}).get("coins", []))

st.subheader("Blacklisted Developers")
st.write(config.get("blacklist", {}).get("devs", []))

