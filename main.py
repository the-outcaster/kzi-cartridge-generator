#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
import urllib.request

# --- Constants for URLs ---
WINDOWS_RUNTIME_URL = "https://runtimes.kazeta.org/windows-1.0.kzr"
LINUX_RUNTIME_URL = "https://runtimes.kazeta.org/linux-1.0.kzr"

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
        self.root.geometry("600x530") # Increased height for the about button
        self.root.resizable(True, True)

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
        ttk.Entry(main_frame, textvariable=self.game_name_var).grid(row=0, column=1, columnspan=2, sticky="ew", pady=5)

        ttk.Label(main_frame, text="Game ID:").grid(row=1, column=0, sticky=tk.W)
        self.game_id_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.game_id_var).grid(row=1, column=1, columnspan=2, sticky="ew", pady=5)

        ttk.Label(main_frame, text="Executable Path:").grid(row=2, column=0, sticky=tk.W)
        self.exec_path_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.exec_path_var, state="readonly").grid(row=2, column=1, sticky="ew", pady=5)
        ttk.Button(main_frame, text="Browse...", command=self.browse_executable).grid(row=2, column=2, padx=(5,0))

        ttk.Label(main_frame, text="Icon Path:").grid(row=3, column=0, sticky=tk.W)
        self.icon_path_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.icon_path_var, state="readonly").grid(row=3, column=1, sticky="ew", pady=5)
        ttk.Button(main_frame, text="Browse...", command=self.browse_icon).grid(row=3, column=2, padx=(5,0))

        ttk.Label(main_frame, text="Runtime:").grid(row=4, column=0, sticky=tk.W)
        self.runtime_var = tk.StringVar(value="linux")
        runtime_options = ["linux", "windows", "none"]
        ttk.OptionMenu(main_frame, self.runtime_var, runtime_options[0], *runtime_options).grid(row=4, column=1, columnspan=2, sticky="ew", pady=5)

        # --- Generate Button ---
        ttk.Button(main_frame, text="Generate .kzi File", command=self.generate_kzi).grid(row=5, column=0, columnspan=3, pady=(15, 0))

        # --- Separator and Download Section ---
        ttk.Separator(main_frame, orient='horizontal').grid(row=6, column=0, columnspan=3, sticky='ew', pady=20)
        
        ttk.Label(main_frame, text="Download Runtimes (.kzr)", style="Bold.TLabel").grid(row=7, column=0, columnspan=3)

        self.win_dl_button = ttk.Button(main_frame, text="Download Windows Runtime", command=lambda: self.start_download(WINDOWS_RUNTIME_URL, "windows-1.0.kzr"))
        self.win_dl_button.grid(row=8, column=0, columnspan=3, sticky='ew', pady=5)

        self.linux_dl_button = ttk.Button(main_frame, text="Download Linux Runtime", command=lambda: self.start_download(LINUX_RUNTIME_URL, "linux-1.0.kzr"))
        self.linux_dl_button.grid(row=9, column=0, columnspan=3, sticky='ew', pady=5)

        self.progress_bar = ttk.Progressbar(main_frame, orient='horizontal', length=100, mode='determinate')
        self.progress_bar.grid(row=10, column=0, columnspan=3, sticky='ew', pady=(10, 0))

        # --- About Button ---
        ttk.Button(main_frame, text="About", command=self.show_about_window).grid(row=11, column=0, columnspan=3, pady=(20, 0))

    def show_about_window(self):
        """
        Displays a modal 'About' window with application information.
        """
        about_window = tk.Toplevel(self.root)
        about_window.title("About KZI Cartridge Generator")
        about_window.geometry("500x230")
        about_window.resizable(False, False)
        
        # Make the window modal
        about_window.transient(self.root)
        about_window.grab_set()

        about_frame = ttk.Frame(about_window, padding="15")
        about_frame.pack(expand=True, fill="both")

        about_text = (
            "GUI for making .kzi (Kazeta information file) files that are\n"
            "necessary for Kazeta cartridges to work.\n\n"
            "Kazeta Cartridge Generator v1.0 by Linux Gaming Central:\n"
            "(this will eventually have the link to the source code on GitHub)\n\n"
            "Copyright (C) 2025 Linux Gaming Central\n\n"
            "Kazeta home page: https://kazeta.org/"
        )

        about_label = ttk.Label(about_frame, text=about_text, justify=tk.LEFT, font=('Helvetica', 10))
        about_label.pack(pady=(0, 15), anchor="w")

        close_button = ttk.Button(about_frame, text="Close", command=about_window.destroy)
        close_button.pack()
        
        # Wait until the about window is closed before allowing main window interaction
        self.root.wait_window(about_window)


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

    def generate_kzi(self):
        game_name = self.game_name_var.get().strip()
        game_id = self.game_id_var.get().strip()
        exec_path_abs = self.exec_path_var.get().strip()
        icon_path_abs = self.icon_path_var.get().strip()
        runtime = self.runtime_var.get()

        if not all([game_name, game_id, exec_path_abs]):
            messagebox.showerror("Error", "Game Name, Game ID, and Executable Path are required fields.")
            return

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

if __name__ == "__main__":
    root = tk.Tk()
    app = KziGeneratorApp(root)
    root.mainloop()



