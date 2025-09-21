#!/usr/bin/env python3
# KZI File Generator - A GUI for creating .kzi cartridge files for Kazeta

import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import os
import getpass
import time

# Import from our other modules
from steamgriddb_api import handle_fetch_icon_flow, ssl_context
from about_window import show_about_window
import urllib.request


def get_default_media_path():
    """Finds a likely path for mounted removable media."""
    username = getpass.getuser()
    possible_paths = [f"/run/media/{username}", f"/media/{username}", "/media"]
    for path in possible_paths:
        if os.path.isdir(path):
            return path
    return os.path.expanduser("~")

class KziGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Kazeta Cartridge Generator")

        main_frame = tk.Frame(root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.runtime_urls = {
            "Linux": "https://runtimes.kazeta.org/linux-1.0.kzr",
            "Windows": "https://runtimes.kazeta.org/windows-1.0.kzr",
            "NES": "https://runtimes.kazeta.org/nes-1.0.kzr",
            "SNES": "https://runtimes.kazeta.org/snes-1.0.kzr",
            "Sega Genesis/Mega Drive": "https://runtimes.kazeta.org/megadrive-1.1.kzr",
        }

        # --- Variable setup ---
        self.game_name_var = tk.StringVar()
        self.game_id_var = tk.StringVar()
        self.exec_path_var = tk.StringVar()
        self.icon_path_var = tk.StringVar()
        self.gamescope_var = tk.StringVar()

        runtime_options = ["none", "linux", "windows", "nes", "snes", "megadrive"]
        self.runtime_var = tk.StringVar(value=runtime_options[0])

        self.create_widgets(main_frame)

    def create_widgets(self, parent):
        # Using a grid layout for better alignment
        parent.columnconfigure(1, weight=1)

        # Game Name
        tk.Label(parent, text="Game Name:").grid(row=0, column=0, sticky="w", pady=2)
        self.game_name_entry = tk.Entry(parent, textvariable=self.game_name_var, width=50)
        self.game_name_entry.grid(row=0, column=1, sticky="ew", pady=2)

        # Game ID
        tk.Label(parent, text="Game ID:").grid(row=1, column=0, sticky="w", pady=2)
        self.game_id_entry = tk.Entry(parent, textvariable=self.game_id_var)
        self.game_id_entry.grid(row=1, column=1, sticky="ew", pady=2)

        # Executable Path
        tk.Label(parent, text="Executable Path:").grid(row=2, column=0, sticky="w", pady=2)
        exec_frame = tk.Frame(parent)
        exec_frame.grid(row=2, column=1, sticky="ew")
        exec_frame.columnconfigure(0, weight=1)
        self.exec_path_entry = tk.Entry(exec_frame, textvariable=self.exec_path_var)
        self.exec_path_entry.grid(row=0, column=0, sticky="ew")
        tk.Button(exec_frame, text="Browse...", command=self.browse_executable).grid(row=0, column=1, padx=(5,0))

        # Icon Path
        tk.Label(parent, text="Icon Path:").grid(row=3, column=0, sticky="w", pady=2)
        icon_frame = tk.Frame(parent)
        icon_frame.grid(row=3, column=1, sticky="ew")
        icon_frame.columnconfigure(0, weight=1)
        self.icon_path_entry = tk.Entry(icon_frame, textvariable=self.icon_path_var)
        self.icon_path_entry.grid(row=0, column=0, sticky="ew")
        tk.Button(icon_frame, text="Browse...", command=self.browse_icon).grid(row=0, column=1, padx=(5,2))
        self.fetch_button = tk.Button(icon_frame, text="Fetch from SteamGridDB", command=self.start_fetch_icon)
        self.fetch_button.grid(row=0, column=2)

        # GameScope Options
        tk.Label(parent, text="GameScope Options:").grid(row=4, column=0, sticky="w", pady=2)
        self.gamescope_entry = tk.Entry(parent, textvariable=self.gamescope_var)
        self.gamescope_entry.grid(row=4, column=1, sticky="ew", pady=2)

        # Runtime
        tk.Label(parent, text="Runtime:").grid(row=5, column=0, sticky="w", pady=2)
        runtime_options = ["none", "linux", "windows", "nes", "snes", "megadrive"]
        self.runtime_menu = tk.OptionMenu(parent, self.runtime_var, *runtime_options)
        self.runtime_menu.grid(row=5, column=1, sticky="ew", pady=2)

        # --- Download Runtimes ---
        download_frame = tk.LabelFrame(parent, text="Download runtimes", padx=10, pady=10)
        download_frame.grid(row=6, column=0, columnspan=2, sticky="ew", pady=10)
        download_frame.columnconfigure(0, weight=1) # Center the button frame

        button_container = tk.Frame(download_frame)
        button_container.grid(row=0, column=0)

        tk.Button(button_container, text="Linux", command=lambda: self.download_runtime("Linux")).pack(side=tk.LEFT, padx=5)
        tk.Button(button_container, text="Windows", command=lambda: self.download_runtime("Windows")).pack(side=tk.LEFT, padx=5)
        tk.Button(button_container, text="NES", command=lambda: self.download_runtime("NES")).pack(side=tk.LEFT, padx=5)
        tk.Button(button_container, text="SNES", command=lambda: self.download_runtime("SNES")).pack(side=tk.LEFT, padx=5)
        tk.Button(button_container, text="Sega Genesis/Mega Drive", command=lambda: self.download_runtime("Sega Genesis/Mega Drive")).pack(side=tk.LEFT, padx=5)

        # --- Main Action Buttons ---
        bottom_bar = tk.Frame(parent)
        bottom_bar.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(10,0))
        bottom_bar.columnconfigure(0, weight=1) # Push buttons to sides

        tk.Button(bottom_bar, text="About", command=lambda: show_about_window(self.root)).grid(row=0, column=0, sticky="w")
        tk.Button(bottom_bar, text="Generate .kzi File", command=self.generate_kzi).grid(row=0, column=1, sticky="e")

    def browse_executable(self):
        filetypes = [
            ("All files", "*.*"),
            ("Windows Executables", "*.exe"),
            ("Linux Executables", "*.x86_64 *.sh *.AppImage"),
            ("NES ROMs", "*.nes"),
            ("SNES ROMs", "*.sfc"),
            ("Sega Genesis/Mega Drive ROMs", "*.bin"),
        ]
        filepath = filedialog.askopenfilename(
            title="Select Executable File",
            initialdir=get_default_media_path(),
            filetypes=filetypes
        )
        if filepath:
            self.exec_path_var.set(filepath)

    def browse_icon(self):
        filepath = filedialog.askopenfilename(
            title="Select Icon File",
            initialdir=get_default_media_path(),
            filetypes=(("PNG files", "*.png"), ("All files", "*.*"))
        )
        if filepath:
            self.icon_path_var.set(filepath)

    def start_fetch_icon(self):
        # Pass self (the app instance) to the handler
        handle_fetch_icon_flow(self)

    def generate_kzi(self):
        game_name = self.game_name_var.get().strip()
        game_id = self.game_id_var.get().strip()
        exec_path = self.exec_path_var.get().strip()
        icon_path = self.icon_path_var.get().strip()
        gamescope_options = self.gamescope_var.get().strip()
        runtime = self.runtime_var.get()

        if not all([game_name, game_id, exec_path]):
            messagebox.showerror("Error", "Game Name, Game ID, and Executable Path are required.")
            return

        if ' ' in game_id:
            messagebox.showerror("Invalid ID", "The 'Game ID' field cannot contain spaces.")
            return

        kzi_filepath = filedialog.asksaveasfilename(
            defaultextension=".kzi",
            filetypes=[("Kazeta Info files", "*.kzi")],
            initialfile="cart.kzi",
            title="Save .kzi File"
        )
        if not kzi_filepath:
            return

        try:
            kzi_dir = os.path.dirname(kzi_filepath)
            relative_exec_path = os.path.relpath(exec_path, kzi_dir)
            relative_icon_path = os.path.relpath(icon_path, kzi_dir) if icon_path else ""

            content = (
                f"Name={game_name}\n"
                f"Id={game_id}\n"
                f"Exec={relative_exec_path}\n"
            )
            if gamescope_options:
                content += f"GameScopeOptions={gamescope_options}\n"
            if relative_icon_path:
                content += f"Icon={relative_icon_path}\n"
            content += f"Runtime={runtime}\n"

            with open(kzi_filepath, "w") as f:
                f.write(content)

            messagebox.showinfo("Success", f"Successfully generated {os.path.basename(kzi_filepath)}")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while generating the file: {e}")

    def download_runtime(self, name):
        url = self.runtime_urls[name]
        filename = os.path.basename(url)
        save_path = filedialog.asksaveasfilename(initialfile=filename, title=f"Save {name} Runtime")
        if not save_path:
            return

        thread = threading.Thread(target=self._download_worker, args=(url, save_path), daemon=True)
        thread.start()

    def _download_worker(self, url, save_path):
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Downloading...")
        progress_window.transient(self.root)
        progress_window.grab_set()

        status_var = tk.StringVar()
        tk.Label(progress_window, textvariable=status_var, width=50).pack(pady=10, padx=20)
        progress_bar = tk.ttk.Progressbar(progress_window, orient="horizontal", length=400, mode="determinate")
        progress_bar.pack(pady=10, fill=tk.X, expand=True, padx=20)

        try:
            with urllib.request.urlopen(url, context=ssl_context) as response, open(save_path, 'wb') as out_file:
                total_size = int(response.getheader('Content-Length', 0))
                downloaded = 0
                start_time = time.time()

                while True:
                    # FIX: Increased buffer size for significantly faster downloads
                    buffer = response.read(1024 * 1024) # 1 MB chunks
                    if not buffer:
                        break

                    out_file.write(buffer)
                    downloaded += len(buffer)

                    # --- Update Progress UI ---
                    percent = (downloaded / total_size) * 100 if total_size > 0 else 0
                    elapsed_time = time.time() - start_time
                    speed = (downloaded / elapsed_time) / (1024 * 1024) if elapsed_time > 0 else 0

                    status_text = (
                        f"{downloaded/1024/1024:.2f} MB / {total_size/1024/1024:.2f} MB "
                        f"({percent:.1f}%) at {speed:.2f} MB/s"
                    )

                    progress_bar['value'] = percent
                    status_var.set(status_text)
                    progress_window.update_idletasks()

            progress_window.destroy()
            messagebox.showinfo("Download Complete", f"Successfully downloaded {os.path.basename(save_path)}")
        except Exception as e:
            progress_window.destroy()
            messagebox.showerror("Download Failed", f"An error occurred: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = KziGeneratorApp(root)
    root.mainloop()

