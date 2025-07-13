
from flask import Flask
import sys
import os
import json

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# --- CONFIGURATION LOADING ---
CONFIG_FILE = 'conf/lalagolf.conf'

def load_config():
    config_path = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')), CONFIG_FILE)
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    with open(config_path, 'r') as f:
        config = json.load(f)
    return config

app = Flask(__name__)

try:
    app_config = load_config()
    app.config['DB_CONFIG'] = app_config.get('DB_CONFIG')
    app.config['WEBAPP_USERS'] = app_config.get('WEBAPP_USERS')
    if not app.config['DB_CONFIG']:
        raise ValueError("DB_CONFIG not found in configuration file.")
    if not app.config['WEBAPP_USERS']:
        raise ValueError("WEBAPP_USERS not found in configuration file.")
except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
    print(f"Error loading webapp configuration: {e}")
    sys.exit(1)

app.config['SECRET_KEY'] = 'a_very_secret_key_for_session_management' # Replace with a strong, random key in production

from src.webapp import routes
