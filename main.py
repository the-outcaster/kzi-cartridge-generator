#!/usr/bin/env python3

# Optional Dependency: Pillow (for icon resizing). Install with: pip install Pillow

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import os
import threading
import urllib.request
import urllib.parse
import json

from about import show_about_window

# --- Constants for URLs ---
WINDOWS_RUNTIME_URL = "https://runtimes.kazeta.org/windows-1.0.kzr"
LINUX_RUNTIME_URL = "https://runtimes.kazeta.org/linux-1.0.kzr"
SEGA_GENESIS_RUNTIME_URL = "https://runtimes.kazeta.org/megadrive-1.0.kzr"

# SteamGridDB API key file
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "kzi-generator")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

# --- Pillow Dependency Check ---
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

class KziGeneratorApp:
    """
    A GUI application for creating .kzi files and downloading runtimes.
    """
    def __init__(self, root):
        """
        Initialize the application window and its widgets.
        """
        self.root = root
        self.root.title("KZI Cartridge Generator")
        self.root.geometry("600x600") # Increased height for the about button
        self.root.resizable(True, True)

        # set default dir to root
        os.chdir('/')

        # --- Style Configuration ---
        style = ttk.Style()
        style.configure("TLabel", padding=5, font=('Helvetica', 10))
        style.configure("TEntry", padding=5, font=('Helvetica', 10))
        style.configure("TButton", padding=5, font=('Helvetica', 10, 'bold'))
        style.configure("TMenubutton", padding=5, font=('Helvetica', 10))
        style.configure("Bold.TLabel", padding=5, font=('Helvetica', 10, 'bold'))

        # --- Main Frame ---
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(1, weight=1)

        # --- Input Fields ---
        ttk.Label(main_frame, text="Game Name:").grid(row=0, column=0, sticky=tk.W)
        self.game_name_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.game_name_var).grid(row=0, column=1, columnspan=3, sticky="ew", pady=5)

        ttk.Label(main_frame, text="Game ID:").grid(row=1, column=0, sticky=tk.W)
        self.game_id_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.game_id_var).grid(row=1, column=1, columnspan=3, sticky="ew", pady=5)

        ttk.Label(main_frame, text="Executable Path:").grid(row=2, column=0, sticky=tk.W)
        self.exec_path_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.exec_path_var, state="readonly").grid(row=2, column=1, columnspan=2, sticky="ew", pady=5)
        ttk.Button(main_frame, text="Browse...", command=self.browse_executable).grid(row=2, column=3, padx=(5,0))

        ttk.Label(main_frame, text="Icon Path:").grid(row=3, column=0, sticky=tk.W)
        self.icon_path_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.icon_path_var, state="readonly").grid(row=3, column=1, sticky="ew", pady=5)
        ttk.Button(main_frame, text="Browse...", command=self.browse_icon).grid(row=3, column=2, padx=(5,0))
        self.fetch_icon_button = ttk.Button(main_frame, text="Fetch Icon", command=self.start_fetch_icon)
        self.fetch_icon_button.grid(row=3, column=3, padx=(5,0))

        ttk.Label(main_frame, text="GameScope Options:").grid(row=4, column=0, sticky=tk.W)
        self.gamescope_options_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.gamescope_options_var).grid(row=4, column=1, columnspan=3, sticky="ew", pady=5)

        ttk.Label(main_frame, text="Runtime:").grid(row=5, column=0, sticky=tk.W)
        self.runtime_var = tk.StringVar(value="linux")
        runtime_options = ["linux", "windows", "megadrive", "none"]
        ttk.OptionMenu(main_frame, self.runtime_var, runtime_options[0], *runtime_options).grid(row=5, column=1, columnspan=3, sticky="ew", pady=5)

        # --- Generate Button ---
        ttk.Button(main_frame, text="Generate .kzi File", command=self.generate_kzi).grid(row=6, column=0, columnspan=4, pady=(15, 0))

        # --- Separator and Download Section ---
        ttk.Separator(main_frame, orient='horizontal').grid(row=7, column=0, columnspan=4, sticky='ew', pady=20)
        
        ttk.Label(main_frame, text="Download Runtimes (.kzr)", style="Bold.TLabel").grid(row=8, column=0, columnspan=3)

        self.win_dl_button = ttk.Button(main_frame, text="Download Windows Runtime", command=lambda: self.start_download(WINDOWS_RUNTIME_URL, "windows-1.0.kzr"))
        self.win_dl_button.grid(row=9, column=0, columnspan=4, sticky='ew', pady=5)

        self.linux_dl_button = ttk.Button(main_frame, text="Download Linux Runtime", command=lambda: self.start_download(LINUX_RUNTIME_URL, "linux-1.0.kzr"))
        self.linux_dl_button.grid(row=10, column=0, columnspan=4, sticky='ew', pady=5)
        
        self.megadrive_dl_button = ttk.Button(main_frame, text="Download Sega Genesis/Mega Drive Runtime", command=lambda: self.start_download(SEGA_GENESIS_RUNTIME_URL, "megadrive-1.0.kzr"))
        self.megadrive_dl_button.grid(row=11, column=0, columnspan=4, sticky='ew', pady=5)

        self.progress_bar = ttk.Progressbar(main_frame, orient='horizontal', length=100, mode='determinate')
        self.progress_bar.grid(row=12, column=0, columnspan=4, sticky='ew', pady=(10, 0))

        # --- About Button ---
        ttk.Button(main_frame, text="About", command=show_about_window).grid(row=13, column=0, columnspan=4, pady=(20, 0))

    def browse_executable(self):
        filepath = filedialog.askopenfilename(title="Select Game Executable")
        if filepath:
            self.exec_path_var.set(filepath)

    def browse_icon(self):
        filepath = filedialog.askopenfilename(
            title="Select Icon",
            filetypes=(("Image files", "*.png"), ("All files", "*.*"))
        )
        if filepath:
            self.icon_path_var.set(filepath)

    # SteamGridDB API stuff
    def load_api_key(self):
        """Loads the API key from the config file."""
        if not os.path.exists(CONFIG_FILE):
            return None
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return config.get("steamgriddb_api_key")
        except (IOError, json.JSONDecodeError):
            return None

    def save_api_key(self, api_key):
        """Saves the API key to the config file."""
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(CONFIG_FILE, 'w') as f:
                json.dump({"steamgriddb_api_key": api_key}, f)
        except IOError:
            messagebox.showwarning("Config Error", "Could not save the API key to the configuration file.")

    def start_fetch_icon(self):
        """
        Validates input and starts the icon fetching process in a new thread.
        """
        if not PIL_AVAILABLE:
            messagebox.showinfo(
                "Dependency Missing",
                "The 'Pillow' library is required to fetch and resize icons.\n\n"
                "Please install it by running:\npip install Pillow"
            )
            return

        api_key = self.load_api_key()
        if not api_key:
            api_key = self.ask_for_api_key()
        
        if not api_key:
            return # User cancelled or entered nothing

        game_name = self.game_name_var.get().strip()
        exec_path = self.exec_path_var.get().strip()

        if not game_name:
            messagebox.showerror("Input Required", "Please enter a Game Name first.")
            return
        
        if not exec_path:
            messagebox.showerror("Input Required", "Please select an Executable Path first.\nThe icon will be saved relative to it.")
            return

        # Run the fetch operation in a separate thread to keep the GUI responsive
        fetch_thread = threading.Thread(
            target=self.fetch_icon_from_steamgriddb, 
            args=(api_key, game_name, exec_path), 
            daemon=True
        )
        fetch_thread.start()

    def ask_for_api_key(self):
        """
        Prompts the user for their API key and saves it for future use.
        Returns the key if provided, otherwise None.
        """
        key = simpledialog.askstring(
            "API Key Required", 
            "Please enter your SteamGridDB API key:",
            parent=self.root
        )
        if key:
            stripped_key = key.strip()
            self.save_api_key(stripped_key)
            return stripped_key
        return None

    def fetch_icon_from_steamgriddb(self, api_key, game_name, exec_path):
        """
        Searches for, downloads, and sets the game icon from SteamGridDB.
        This method is designed to run in a background thread.
        """
        try:
            self.fetch_icon_button.config(state=tk.DISABLED)

            # 1. Search for the game ID
            search_url = f"https://www.steamgriddb.com/api/v2/search/autocomplete/{urllib.parse.quote(game_name)}"
            headers = {"Authorization": f"Bearer {api_key}", "User-Agent": "KziGenerator/1.0"}
            req = urllib.request.Request(search_url, headers=headers)
            
            with urllib.request.urlopen(req) as response:
                if response.status != 200:
                    raise ConnectionError(f"API Error: Status {response.status}")
                search_data = json.loads(response.read().decode())

            if not search_data.get("success") or not search_data.get("data"):
                messagebox.showerror("Not Found", f"Could not find an entry for '{game_name}' on SteamGridDB.")
                return

            game_id = search_data["data"][0]["id"]
            icon_url_to_download = None
            resize_needed = False

            # 2. Try to find a 64x64 PNG
            icons_url_64 = f"https://www.steamgriddb.com/api/v2/icons/game/{game_id}?dimensions=64"
            req = urllib.request.Request(icons_url_64, headers=headers)
            with urllib.request.urlopen(req) as response:
                icons_data = json.loads(response.read().decode())
                if icons_data.get("success") and icons_data.get("data"):
                    icon_url_to_download = next((icon.get("url") for icon in icons_data["data"] if icon.get("mime") == "image/png"), None)

            # 3. If not found, try to find a 32x32 PNG
            if not icon_url_to_download:
                icons_url_32 = f"https://www.steamgriddb.com/api/v2/icons/game/{game_id}?dimensions=32"
                req = urllib.request.Request(icons_url_32, headers=headers)
                with urllib.request.urlopen(req) as response:
                    icons_data = json.loads(response.read().decode())
                    if icons_data.get("success") and icons_data.get("data"):
                        icon_url_to_download = next((icon.get("url") for icon in icons_data["data"] if icon.get("mime") == "image/png"), None)

            # 4. If still not found, get any PNG and flag for resizing
            if not icon_url_to_download:
                resize_needed = True
                icons_url_any = f"https://www.steamgriddb.com/api/v2/icons/game/{game_id}"
                req = urllib.request.Request(icons_url_any, headers=headers)
                with urllib.request.urlopen(req) as response:
                    icons_data = json.loads(response.read().decode())
                    if icons_data.get("success") and icons_data.get("data"):
                        icon_url_to_download = next((icon.get("url") for icon in icons_data["data"] if icon.get("mime") == "image/png"), None)
            
            # 5. Check if any icon was found and process it
            if not icon_url_to_download:
                messagebox.showwarning("No Icon", f"Found '{game_name}', but no suitable PNG icon is available.")
                return

            # 6. Define save path in the parent directory of the executable
            exec_directory = os.path.dirname(exec_path)
            parent_directory = os.path.dirname(exec_directory)
            icon_save_path = os.path.join(parent_directory, "icon.png")

            # 7. Download and possibly resize the icon
            if resize_needed:
                temp_path, _ = urllib.request.urlretrieve(icon_url_to_download)
                with Image.open(temp_path) as img:
                    img_resized = img.resize((64, 64), Image.Resampling.LANCZOS)
                    img_resized.save(icon_save_path, "PNG")
                os.remove(temp_path) # Clean up temporary file
            else:
                urllib.request.urlretrieve(icon_url_to_download, icon_save_path)
            
            self.icon_path_var.set(icon_save_path)
            messagebox.showinfo("Success", f"Icon successfully downloaded and set to:\n{icon_save_path}")

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while fetching the icon: {e}")
        
        finally:
            self.fetch_icon_button.config(state=tk.NORMAL)

    def generate_kzi(self):
        game_name = self.game_name_var.get().strip()
        game_id = self.game_id_var.get().strip()
        exec_path_abs = self.exec_path_var.get().strip()
        gamescope_options = self.gamescope_options_var.get().strip()
        icon_path_abs = self.icon_path_var.get().strip()
        runtime = self.runtime_var.get()

        #if not all([game_name, game_id, exec_path_abs]):
            #messagebox.showerror("Error", "Game Name, Game ID, and Executable Path are required fields.")
            #return

        save_path = filedialog.asksaveasfilename(
            initialfile=f"cart.kzi",
            defaultextension=".kzi",
            filetypes=(("KZI files", "*.kzi"), ("All files", "*.*"))
        )
        if not save_path:
            return

        save_directory = os.path.dirname(save_path)
        relative_exec_path = os.path.relpath(exec_path_abs, save_directory)
        relative_icon_path = ""
        if icon_path_abs:
            relative_icon_path = os.path.relpath(icon_path_abs, save_directory)

        content = (
            f"Name={game_name}\n"
            f"Id={game_id}\n"
            f"Exec={relative_exec_path}\n"
            f"GameScopeOptions={gamescope_options}\n"
            f"Icon={relative_icon_path}\n"
            f"Runtime={runtime}\n"
        )

        try:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("Success", f"Successfully generated:\n{os.path.basename(save_path)}")
        except IOError as e:
            messagebox.showerror("File Error", f"Failed to save the file.\nError: {e}")

    def start_download(self, url, filename):
        """
        Prompts user for save location and starts the download in a new thread.
        """
        save_path = filedialog.asksaveasfilename(
            initialfile=filename,
            defaultextension=".kzr",
            filetypes=(("Kazeta Runtimes", "*.kzr"), ("All files", "*.*"))
        )
        if save_path:
            download_thread = threading.Thread(target=self.download_file, args=(url, save_path), daemon=True)
            download_thread.start()

    def download_file(self, url, save_path):
        """
        Handles the actual file download, updating the progress bar.
        This method is designed to run in a background thread.
        """
        try:
            self.win_dl_button.config(state=tk.DISABLED)
            self.linux_dl_button.config(state=tk.DISABLED)
            self.megadrive_dl_button.config(state=tk.DISABLED)
            self.progress_bar['value'] = 0

            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(save_path, 'wb') as out_file:
                total_size_str = response.info().get('Content-Length')
                if not total_size_str:
                    messagebox.showerror("Download Error", "Could not determine file size from server.")
                    return
                
                total_size = int(total_size_str)
                downloaded = 0
                chunk_size = 8192

                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    progress_percentage = (downloaded / total_size) * 100
                    self.progress_bar['value'] = progress_percentage

            messagebox.showinfo("Download Complete", f"Successfully downloaded:\n{os.path.basename(save_path)}")
        
        except Exception as e:
            messagebox.showerror("Download Error", f"An error occurred: {e}")
        
        finally:
            self.progress_bar['value'] = 0
            self.win_dl_button.config(state=tk.NORMAL)
            self.linux_dl_button.config(state=tk.NORMAL)
            self.megadrive_dl_button.config(state=tk.NORMAL)

if __name__ == "__main__":
    root = tk.Tk()
    app = KziGeneratorApp(root)
    root.mainloop()



