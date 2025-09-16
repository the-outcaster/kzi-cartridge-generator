#!/usr/bin/env python3
# SteamGridDB API Handler for KZI File Generator

import os
import json
import threading
import urllib.request
import urllib.parse
import tkinter as tk
from tkinter import messagebox, simpledialog

# --- Pillow Dependency Check for resizing ---
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# --- Custom Exceptions for clear error handling ---
class APIError(Exception): pass
class GameNotFound(Exception): pass
class NoIconFound(Exception): pass

# --- Configuration File Constants ---
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "kzi-cartridge-generator")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")


def load_api_key():
    """Loads the API key from the config file."""
    if not os.path.exists(CONFIG_FILE):
        return None
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            return config.get("steamgriddb_api_key")
    except (IOError, json.JSONDecodeError):
        return None

def save_api_key(api_key):
    """Saves the API key to the config file."""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump({"steamgriddb_api_key": api_key}, f)
        return True
    except IOError:
        return False

def find_and_download_icon(api_key, game_name, exec_path, ssl_context):
    """
    Handles the core logic of searching for, downloading, and saving a game icon.
    This function contains no UI code and raises exceptions on failure.
    """
    headers = {"Authorization": f"Bearer {api_key}", "User-Agent": "KziGenerator/1.0"}

    try:
        search_url = f"https://www.steamgriddb.com/api/v2/search/autocomplete/{urllib.parse.quote(game_name)}"
        req = urllib.request.Request(search_url, headers=headers)
        with urllib.request.urlopen(req, context=ssl_context) as response:
            if response.status != 200:
                raise APIError(f"API Error: Status {response.status}")
            search_data = json.loads(response.read().decode())
    except Exception as e:
        raise APIError(str(e))

    if not search_data.get("success") or not search_data.get("data"):
        raise GameNotFound()

    game_id = search_data["data"][0]["id"]
    icon_url_to_download = None
    resize_needed = False

    for dimension in ["64", "32", None]:
        try:
            icons_url = f"https://www.steamgriddb.com/api/v2/icons/game/{game_id}"
            if dimension:
                icons_url += f"?dimensions={dimension}"

            req = urllib.request.Request(icons_url, headers=headers)
            with urllib.request.urlopen(req, context=ssl_context) as response:
                icons_data = json.loads(response.read().decode())
                if icons_data.get("success") and icons_data.get("data"):
                    icon_url_to_download = next((icon.get("url") for icon in icons_data["data"] if icon.get("mime") == "image/png"), None)

            if icon_url_to_download:
                if dimension is None:
                    resize_needed = True
                break
        except Exception:
            continue

    if not icon_url_to_download:
        raise NoIconFound()

    exec_directory = os.path.dirname(exec_path)
    parent_directory = os.path.dirname(exec_directory)
    icon_save_path = os.path.join(parent_directory, "icon.png")

    if resize_needed:
        if not PIL_AVAILABLE:
            raise ImportError("Pillow is required to resize the icon.")
        temp_path, _ = urllib.request.urlretrieve(icon_url_to_download)
        with Image.open(temp_path) as img:
            img_resized = img.resize((64, 64), Image.Resampling.LANCZOS)
            img_resized.save(icon_save_path, "PNG")
        os.remove(temp_path)
    else:
        urllib.request.urlretrieve(icon_url_to_download, icon_save_path)

    return icon_save_path


def _fetch_icon_thread_worker(api_key, game_name, exec_path, app_instance):
    """
    Private worker function that runs in a thread. It calls the core API logic
    and handles showing UI messages based on the outcome.
    """
    try:
        app_instance.fetch_icon_button.config(state=tk.DISABLED)

        icon_save_path = find_and_download_icon(
            api_key, game_name, exec_path, app_instance.ssl_context
        )

        app_instance.icon_path_var.set(icon_save_path)
        messagebox.showinfo("Success", f"Icon successfully downloaded and set to:\n{icon_save_path}")

    except GameNotFound:
        messagebox.showerror("Not Found", f"Could not find an entry for '{game_name}' on SteamGridDB.")
    except NoIconFound:
        messagebox.showwarning("No Icon", f"Found '{game_name}', but no suitable PNG icon is available.")
    except ImportError as e:
        messagebox.showinfo("Dependency Missing", f"{e}\nPlease install it by running:\npip install Pillow")
    except (APIError, Exception) as e:
        messagebox.showerror("Error", f"An error occurred while fetching the icon: {e}")
    finally:
        app_instance.fetch_icon_button.config(state=tk.NORMAL)


def handle_fetch_icon_flow(app_instance):
    """
    Manages the entire UI flow for fetching an icon, including asking for an
    API key and starting the background thread. This is the main entry point
    called by the GUI.
    """
    api_key = load_api_key()
    if not api_key:
        key = simpledialog.askstring(
            "API Key Required",
            "Please enter your SteamGridDB API key:",
            parent=app_instance.root
        )
        if key:
            stripped_key = key.strip()
            if not save_api_key(stripped_key):
                messagebox.showwarning("Config Error", "Could not save the API key.")
            api_key = stripped_key
        else:
            return

    game_name = app_instance.game_name_var.get().strip()
    exec_path = app_instance.exec_path_var.get().strip()

    if not game_name:
        messagebox.showerror("Input Required", "Please enter a Game Name first.")
        return
    if not exec_path:
        messagebox.showerror("Input Required", "Please select an Executable Path first.")
        return

    fetch_thread = threading.Thread(
        target=_fetch_icon_thread_worker,
        args=(api_key, game_name, exec_path, app_instance),
        daemon=True
    )
    fetch_thread.start()

