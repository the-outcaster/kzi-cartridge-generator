#!/usr/bin/env python3
# SteamGridDB API Handler for KZI File Generator

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import threading
import os
import json
import urllib.request
import urllib.parse
from io import BytesIO
import ssl
import traceback

# --- Pillow (PIL) Dependency Check ---
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

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
                # print(f"Found system SSL certificates at: {path}")
                cert_path = path
                break
    try:
        if cert_path:
            return ssl.create_default_context(cafile=cert_path)
        else:
            return ssl.create_default_context()
    except Exception:
        return ssl.create_default_context()

# Create the SSL context to be imported and used by other modules
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
        key = simpledialog.askstring(
            "SteamGridDB API Key",
            "Please enter your SteamGridDB API key.\nThis is required to fetch icons.",
            parent=parent_window
        )
        if key:
            clean_key = key.strip()
            if clean_key:
                config['steamgriddb_api_key'] = clean_key
                os.makedirs(config_dir, exist_ok=True)
                with open(config_file, 'w') as f:
                    json.dump(config, f, indent=4)
                return clean_key
    return None

# --- Error Handler ---
def _show_fetch_error(app_instance, e):
    """Displays a formatted error message on the main thread."""
    traceback.print_exc()
    error_message = f"An error occurred while fetching the icon:\n\n{type(e).__name__}: {e}"
    messagebox.showerror("Error", error_message)

# --- Success Handler (Moved to module level) ---
def _update_gui_success(app_instance, save_path):
    """Called on the main thread after a successful download."""
    app_instance.icon_path_var.set(save_path)
    messagebox.showinfo("Success", f"Icon downloaded and saved to:\n{save_path}")

# --- Main Handler ---
def handle_fetch_icon_flow(app_instance):
    api_key = get_steamgriddb_api_key(app_instance.root)
    if not api_key:
        messagebox.showwarning("API Key Missing", "Cannot fetch icon without an API key.")
        return

    game_name = app_instance.game_name_entry.get().strip()
    exec_path = app_instance.exec_path_entry.get().strip()

    if not game_name:
        messagebox.showerror("Error", "Please enter a Game Name to search for an icon.")
        return
    if not exec_path:
        # We can still proceed, but we'll save relative to the user's media path
        default_save_dir = os.path.expanduser("~")
    else:
        default_save_dir = os.path.dirname(exec_path)

    # Prompt user for save location
    save_path = filedialog.asksaveasfilename(
        title="Save Icon As...",
        initialdir=default_save_dir,
        initialfile="icon.png",
        filetypes=[("PNG files", "*.png")]
    )

    if not save_path:
        return # User cancelled

    thread = threading.Thread(
        target=_fetch_icon_worker,
        args=(app_instance, api_key, game_name, save_path), # Pass save_path
        daemon=True
    )
    thread.start()

# --- Worker Thread for API Calls ---
def _fetch_icon_worker(app_instance, api_key, game_name, save_path): # Changed exec_path to save_path
    """
    Performs the actual API calls and image processing in the background.
    """
    try:
        # Step 1: Search for the game to get its ID
        encoded_game_name = urllib.parse.quote(game_name)
        search_url = f"https://www.steamgriddb.com/api/v2/search/autocomplete/{encoded_game_name}"

        req = urllib.request.Request(search_url, headers={'Authorization': f'Bearer {api_key}'})

        with urllib.request.urlopen(req, context=ssl_context) as response:
            search_data = json.loads(response.read().decode())

        if not search_data.get('success') or not search_data.get('data'):
            raise ValueError(f"Game '{game_name}' not found on SteamGridDB.")

        game_id = search_data['data'][0]['id']

        # Step 2: Get icons for that game ID
        icons_url = f"https://www.steamgriddb.com/api/v2/icons/game/{game_id}"
        req = urllib.request.Request(icons_url, headers={'Authorization': f'Bearer {api_key}'})

        with urllib.request.urlopen(req, context=ssl_context) as response:
            icons_data = json.loads(response.read().decode())

        if not icons_data.get('success') or not icons_data.get('data'):
            raise ValueError("No icons found for this game.")

        # Step 3: Find the best icon URL
        icons = icons_data['data']
        icon_url = None

        for icon in icons:
            if icon['width'] == 64 and icon['height'] == 64 and icon['mime'] == 'image/png':
                icon_url = icon['url']
                break
        if not icon_url:
            for icon in icons:
                if icon['width'] == 32 and icon['height'] == 32 and icon['mime'] == 'image/png':
                    icon_url = icon['url']
                    break

        resize_needed = not icon_url
        if not icon_url:
            for icon in icons:
                if icon['mime'] == 'image/png':
                    icon_url = icon['url']
                    break

        if not icon_url:
            raise ValueError("No suitable PNG icon could be found.")

        # Step 4: Download the icon
        req = urllib.request.Request(icon_url) # No auth header needed for CDN
        with urllib.request.urlopen(req, context=ssl_context) as response:
            image_data = response.read()

        # Step 5: Resize if necessary and save
        if resize_needed:
            if not PIL_AVAILABLE:
                raise ImportError("Pillow library is required to resize icons. Please install it (`pip install Pillow`).")

            with Image.open(BytesIO(image_data)) as img:
                resized_img = img.resize((64, 64), Image.Resampling.LANCZOS)
                resized_img.save(save_path, "PNG")
        else:
            with open(save_path, 'wb') as f:
                f.write(image_data)

        # Step 6: Update the GUI on the main thread
        # FIX: Use a lambda to robustly schedule the success call,
        # mirroring the structure of the error handler.
        app_instance.root.after(0, lambda app=app_instance, path=save_path: _update_gui_success(app, path))

    except Exception as e:
        # Use the robust error handler
        app_instance.root.after(0, lambda e=e: _show_fetch_error(app_instance, e))

