#!/usr/bin/env python3
# SteamGridDB API Handler for KZI File Generator

import os
import json
import urllib.request
import urllib.parse
from io import BytesIO
import ssl
import traceback

from PyQt6.QtWidgets import QMessageBox, QInputDialog, QFileDialog, QLineEdit
from PyQt6.QtCore import QThread, pyqtSignal

# --- Pillow (PIL) Dependency Check ---
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Standard browser spoof to bypass Cloudflare/API 403 blocks
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# --- Robust SSL Context Fix ---
def create_robust_ssl_context():
    """
    Creates an SSL context that works reliably on different systems, especially Linux.
    It prioritizes the certifi package, then standard system paths.
    """
    cert_path = None
    try:
        import certifi
        candidate_path = certifi.where()
        if os.path.exists(candidate_path):
            cert_path = candidate_path
    except (ImportError, Exception):
        pass

    if not cert_path:
        system_cert_paths = [
            "/etc/ssl/certs/ca-certificates.crt",      # Debian/Ubuntu/Gentoo etc.
            "/etc/pki/tls/certs/ca-bundle.crt",       # Fedora/RHEL
        ]
        for path in system_cert_paths:
            if os.path.exists(path):
                cert_path = path
                break
    try:
        if cert_path:
            return ssl.create_default_context(cafile=cert_path)
        else:
            return ssl.create_default_context()
    except Exception:
        return ssl.create_default_context()

ssl_context = create_robust_ssl_context()


# --- API Key Management ---
def get_steamgriddb_api_key(parent_window):
    config_dir = os.path.join(os.path.expanduser("~"), ".config", "kzi-cartridge-generator")
    config_file = os.path.join(config_dir, "config.json")

    config = {}
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            try:
                config = json.load(f)
            except json.JSONDecodeError:
                pass

    if 'steamgriddb_api_key' in config and config['steamgriddb_api_key']:
        return config['steamgriddb_api_key']
    else:
        key, ok = QInputDialog.getText(
            parent_window,
            "SteamGridDB API Key",
            "Please enter your SteamGridDB API key.\nThis is required to fetch icons.",
            QLineEdit.EchoMode.Normal
        )
        if ok and key:
            clean_key = key.strip()
            if clean_key:
                config['steamgriddb_api_key'] = clean_key
                os.makedirs(config_dir, exist_ok=True)
                with open(config_file, 'w') as f:
                    json.dump(config, f, indent=4)
                return clean_key
    return None


# --- Worker Thread for API Calls ---
class FetchIconWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, api_key, game_name, save_path):
        super().__init__()
        self.api_key = api_key
        self.game_name = game_name
        self.save_path = save_path

    def run(self):
        try:
            # Step 1: Search for the game to get its ID
            encoded_game_name = urllib.parse.quote(self.game_name)
            search_url = f"https://www.steamgriddb.com/api/v2/search/autocomplete/{encoded_game_name}"

            # ADDED USER-AGENT
            req = urllib.request.Request(search_url, headers={
                'Authorization': f'Bearer {self.api_key}',
                'User-Agent': USER_AGENT
            })

            with urllib.request.urlopen(req, context=ssl_context) as response:
                search_data = json.loads(response.read().decode())

            if not search_data.get('success') or not search_data.get('data'):
                raise ValueError(f"Game '{self.game_name}' not found on SteamGridDB.")

            game_id = search_data['data'][0]['id']

            # Step 2: Get icons for that game ID
            icons_url = f"https://www.steamgriddb.com/api/v2/icons/game/{game_id}"

            # ADDED USER-AGENT
            req = urllib.request.Request(icons_url, headers={
                'Authorization': f'Bearer {self.api_key}',
                'User-Agent': USER_AGENT
            })

            with urllib.request.urlopen(req, context=ssl_context) as response:
                icons_data = json.loads(response.read().decode())

            if not icons_data.get('success') or not icons_data.get('data'):
                raise ValueError("No icons found for this game.")

            # Step 3: Find the best icon URL
            icons = icons_data['data']
            icon_url = None

            for icon in icons:
                if icon['width'] == 32 and icon['height'] == 32 and icon['mime'] == 'image/png':
                    icon_url = icon['url']
                    break

            if not icon_url:
                for icon in icons:
                    if icon['mime'] == 'image/png':
                        icon_url = icon['url']
                        break

            if not icon_url:
                raise ValueError("No suitable PNG icon could be found.")

            # Step 4: Download the icon
            # ADDED USER-AGENT (No Auth header needed for the CDN, but UA is critical)
            req = urllib.request.Request(icon_url, headers={'User-Agent': USER_AGENT})
            with urllib.request.urlopen(req, context=ssl_context) as response:
                image_data = response.read()

            if not PIL_AVAILABLE:
                raise ImportError("Pillow library is required to resize icons. Please install it (`pip install Pillow`).")

            # Step 5: Load with Pillow, FORCE resize to 32x32, and save
            with Image.open(BytesIO(image_data)) as img:
                if img.size != (32, 32):
                    resized_img = img.resize((32, 32), Image.Resampling.LANCZOS)
                    resized_img.save(self.save_path, "PNG")
                else:
                    with open(self.save_path, 'wb') as f:
                        f.write(image_data)

            self.finished.emit(self.save_path)

        except Exception as e:
            traceback.print_exc()
            self.error.emit(f"{type(e).__name__}: {e}")


# --- Main Handler ---
def handle_fetch_icon_flow(app_instance):
    api_key = get_steamgriddb_api_key(app_instance)
    if not api_key:
        QMessageBox.warning(app_instance, "API Key Missing", "Cannot fetch icon without an API key.")
        return

    game_name = app_instance.game_name_entry.text().strip()
    exec_path = app_instance.exec_path_entry.text().strip()

    if not game_name:
        QMessageBox.critical(app_instance, "Error", "Please enter a Game Name to search for an icon.")
        return

    if not exec_path:
        default_save_dir = os.path.expanduser("~")
    else:
        default_save_dir = os.path.dirname(exec_path)

    save_path, _ = QFileDialog.getSaveFileName(
        app_instance,
        "Save Icon As...",
        os.path.join(default_save_dir, "icon.png"),
        "PNG files (*.png)"
    )

    if not save_path:
        return

    app_instance.fetch_icon_worker = FetchIconWorker(api_key, game_name, save_path)

    def on_success(saved_to_path):
        app_instance.icon_path_entry.setText(saved_to_path)
        QMessageBox.information(app_instance, "Success", f"Icon downloaded and saved to:\n{saved_to_path}")

    def on_error(error_message):
        QMessageBox.critical(app_instance, "Error", f"An error occurred while fetching the icon:\n\n{error_message}")

    app_instance.fetch_icon_worker.finished.connect(on_success)
    app_instance.fetch_icon_worker.error.connect(on_error)
    app_instance.fetch_icon_worker.start()
