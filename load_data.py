
import os
import json
from src.data_parser import parse_file
from src.db_loader import save_round_data, init_connection_pool

# --- CONFIGURATION LOADING ---
CONFIG_FILE = 'conf/lalagolf.conf'

def load_config():
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(f"Configuration file not found: {CONFIG_FILE}")
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    return config

try:
    app_config = load_config()
    DB_CONFIG = app_config.get('DB_CONFIG')
    if not DB_CONFIG:
        raise ValueError("DB_CONFIG not found in configuration file.")
except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
    print(f"Error loading configuration: {e}")
    exit(1)

def main():
    init_connection_pool(DB_CONFIG)
    data_dir = 'data'
    for year_dir in os.listdir(data_dir):
        year_path = os.path.join(data_dir, year_dir)
        if os.path.isdir(year_path):
            for file_name in os.listdir(year_path):
                if file_name.endswith('.txt'):
                    file_path = os.path.join(year_path, file_name)
                    print(f"Processing {file_path}...")
                    try:
                        raw_content, round_data, scores_and_stats = parse_file(file_path)
                        save_round_data(round_data, scores_and_stats, raw_content)
                        print(f"Successfully loaded {file_path} into the database.")
                    except Exception as e:
                        print(f"Error processing {file_path}: {e}")

if __name__ == '__main__':
    main()
