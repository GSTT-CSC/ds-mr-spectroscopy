import configparser
import os
import shutil


APP_DATA_DIR = '/mrs_app_data'
CONFIG_DIR = os.path.dirname(os.path.realpath(__file__))  # same dir as this file

if os.path.exists(APP_DATA_DIR):
    shutil.rmtree(APP_DATA_DIR)
os.makedirs(APP_DATA_DIR, exist_ok=True)


# Create configparser reader objects
SETTINGS = configparser.ConfigParser()
# This makes a list of config files for both server and local files
config_files = list(os.path.join(CONFIG_DIR, x) for x in os.listdir(CONFIG_DIR) if x.endswith('cfg'))
# Read config files
SETTINGS.read(config_files)
