#!/usr/bin/env python3
# KZI File Generator - A GUI for creating .kzi cartridge files for Kazeta

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext # Added scrolledtext for the preview box
import threading
import os
import getpass
import time
import re
import subprocess
import shlex
import shutil

# Import from our other modules
from steamgriddb_api import handle_fetch_icon_flow
from about_window import show_about_window
import urllib.request
# Import the shared SSL context
from steamgriddb_api import ssl_context


def get_default_media_path():
    """Finds a likely path for mounted removable media."""
    username = getpass.getuser()
    possible_paths = [f"/run/media/{username}", f"/media/{username}", "/media"]
    for path in possible_paths:
        if os.path.isdir(path):
            return path
    return os.path.expanduser("~")

def is_steam_running():
    """Checks if a Steam process is currently running using pgrep."""
    try:
        subprocess.check_call(['pgrep', '-x', 'steam'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def run_command_in_new_terminal(command_list, env=None, cwd=None):
    """
    Tries to run a command in a new terminal window, with an optional environment and working directory.
    The window will remain open after the command finishes.
    """
    cd_command = f'cd {shlex.quote(cwd)} && ' if cwd else ''
    command_string = shlex.join(command_list)

    wrapper_script = (
        f'{cd_command}{command_string};'
        ' echo;'
        ' echo "----------------------------------------";'
        ' echo "Process finished. Press Enter to close this window.";'
        ' read'
    )

    terminals = [
        ('konsole',        '-e'),
        ('gnome-terminal', '--'),
        ('xfce4-terminal', '-e'),
        ('xterm',          '-e'),
    ]

    for term, flag in terminals:
        if shutil.which(term):
            try:
                final_command = [term, flag, 'bash', '-c', wrapper_script]
                subprocess.Popen(final_command, env=env)
                return
            except Exception as e:
                print(f"Warning: Failed to launch with {term}: {e}")
                continue

    messagebox.showerror(
        "Terminal Not Found",
        "Could not automatically launch a terminal window.\n"
        "Please ensure a standard terminal is installed (e.g., konsole, gnome-terminal, xterm)."
    )


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
            "Nintendo 64": "https://runtimes.kazeta.org/nintendo64-1.0.kzr",
        }

        # --- Variable setup ---
        self.game_name_var = tk.StringVar()
        self.game_id_var = tk.StringVar()
        self.exec_path_var = tk.StringVar()
        self.params_var = tk.StringVar()
        self.icon_path_var = tk.StringVar()
        self.gamescope_var = tk.StringVar()
        self.proton_path_var = tk.StringVar()
        self.dpad_fix_var = tk.BooleanVar(value=False)

        # Traces for live preview update
        self.game_name_var.trace_add("write", self._update_game_id)
        self.game_id_var.trace_add("write", self._update_preview_trace)
        self.exec_path_var.trace_add("write", self._update_preview_trace)
        self.params_var.trace_add("write", self._update_preview_trace)
        self.icon_path_var.trace_add("write", self._update_preview_trace)
        self.gamescope_var.trace_add("write", self._update_preview_trace)
        self.dpad_fix_var.trace_add("write", self._update_preview_trace)

        runtime_options = ["none", "linux", "windows", "nes", "snes", "megadrive", "nintendo64"]
        self.runtime_var = tk.StringVar(value=runtime_options[0])
        self.runtime_var.trace_add("write", self._update_preview_trace) # Trace runtime changes


        self.create_widgets(main_frame)
        self._update_preview() # Initial preview population

    def _update_game_id(self, *args):
        game_name = self.game_name_var.get()
        sanitized_id = re.sub(r'[^a-z0-9-]', '', game_name.lower().replace(' ', '-'))
        if self.game_id_var.get() != sanitized_id:
             self.game_id_var.set(sanitized_id)
        self._update_preview()

    def _update_preview_trace(self, *args):
        self._update_preview()

    def _get_preview_relative_path(self, absolute_path):
        """Generates a representative relative path for the preview."""
        if not absolute_path:
            return ""
        try:
            # Attempt to find common media path structure
            media_path_base = get_default_media_path()
            if absolute_path.startswith(media_path_base):
                 # Find the part after the username-specific media folder
                 path_parts = absolute_path.split(os.sep)
                 username_index = -1
                 for i, part in enumerate(path_parts):
                     if part == getpass.getuser() and i > 0 and path_parts[i-1] in ["media", "run"]:
                         username_index = i
                         break
                 if username_index != -1 and username_index + 1 < len(path_parts):
                      # Assume the next part is the card name, and everything after is relative
                      card_name_index = username_index + 1
                      if card_name_index + 1 < len(path_parts):
                           relative_part = os.path.join(*path_parts[card_name_index + 1:])
                           return relative_part
            # Fallback: Use the last two components (directory + filename)
            return os.path.join(os.path.basename(os.path.dirname(absolute_path)), os.path.basename(absolute_path))
        except Exception:
            # Safest fallback: just the filename
            return os.path.basename(absolute_path)


    def _get_kzi_content(self, for_preview=False, kzi_save_dir=None):
        """Helper function to generate KZI content string."""
        game_name = self.game_name_var.get().strip()
        game_id = self.game_id_var.get().strip()
        exec_path = self.exec_path_var.get().strip()
        params = self.params_var.get().strip()
        icon_path = self.icon_path_var.get().strip()
        gamescope_options = self.gamescope_var.get().strip()
        runtime = self.runtime_var.get()
        apply_dpad_fix = self.dpad_fix_var.get()

        content = f"Name={game_name}\nId={game_id}\n"

        exec_command = ""
        if exec_path:
             if for_preview:
                  exec_command = self._get_preview_relative_path(exec_path)
             elif kzi_save_dir:
                  try:
                       exec_command = os.path.relpath(exec_path, kzi_save_dir)
                  except ValueError: # Handle paths on different drives
                       exec_command = exec_path # Use absolute path as fallback
             else: # Should not happen during generation, but handle defensively
                  exec_command = exec_path

             # Apply quoting logic for spaces ONLY to the path part
             path_part = exec_command
             params_part = params
             if ' ' in path_part and not path_part.startswith('"'):
                  path_part = f'"{path_part}"'

             if params_part:
                  exec_command = f"{path_part} {params_part}"
             else:
                  exec_command = path_part

        content += f"Exec={exec_command}\n"


        if gamescope_options:
            content += f"GameScopeOptions={gamescope_options}\n"

        relative_icon_path = ""
        if icon_path:
             if for_preview:
                 relative_icon_path = self._get_preview_relative_path(icon_path)
             elif kzi_save_dir:
                 try:
                     relative_icon_path = os.path.relpath(icon_path, kzi_save_dir)
                 except ValueError:
                     relative_icon_path = icon_path # Fallback to absolute
             else:
                 relative_icon_path = icon_path

             content += f"Icon={relative_icon_path}\n"


        content += f"Runtime={runtime}\n"

        if apply_dpad_fix:
            content += "PreExec=busctl call org.shadowblip.InputPlumber /org/shadowblip/InputPlumber/CompositeDevice0 org.shadowblip.Input.CompositeDevice LoadProfilePath \"s\" /usr/share/inputplumber/profiles/steam-deck-dpad-fix.yaml\n"
            content += "PostExec=busctl call org.shadowblip.InputPlumber /org/shadowblip/InputPlumber/CompositeDevice0 org.shadowblip.Input.CompositeDevice LoadProfilePath \"s\" /usr/share/inputplumber/profiles/steam-deck.yaml\n"

        return content

    def _update_preview(self):
        """Updates the content of the preview text box."""
        content = self._get_kzi_content(for_preview=True)
        self.preview_text.config(state=tk.NORMAL) # Enable writing
        self.preview_text.delete('1.0', tk.END)
        self.preview_text.insert('1.0', content)
        self.preview_text.config(state=tk.DISABLED) # Disable editing

    def create_widgets(self, parent):
        parent.columnconfigure(1, weight=1)

        row_index = 0
        tk.Label(parent, text="Game Name:").grid(row=row_index, column=0, sticky="w", pady=2); row_index += 1
        self.game_name_entry = tk.Entry(parent, textvariable=self.game_name_var, width=50)
        self.game_name_entry.grid(row=row_index-1, column=1, sticky="ew", pady=2)

        tk.Label(parent, text="Game ID:").grid(row=row_index, column=0, sticky="w", pady=2); row_index += 1
        self.game_id_entry = tk.Entry(parent, textvariable=self.game_id_var)
        self.game_id_entry.grid(row=row_index-1, column=1, sticky="ew", pady=2)

        tk.Label(parent, text="Executable Path:").grid(row=row_index, column=0, sticky="w", pady=2); row_index += 1
        exec_frame = tk.Frame(parent)
        exec_frame.grid(row=row_index-1, column=1, sticky="ew")
        exec_frame.columnconfigure(0, weight=1)
        self.exec_path_entry = tk.Entry(exec_frame, textvariable=self.exec_path_var)
        self.exec_path_entry.grid(row=0, column=0, sticky="ew")
        tk.Button(exec_frame, text="Browse...", command=self.browse_executable).grid(row=0, column=1, padx=(5,0))

        tk.Label(parent, text="Additional Parameters:").grid(row=row_index, column=0, sticky="w", pady=2); row_index += 1
        self.params_entry = tk.Entry(parent, textvariable=self.params_var)
        self.params_entry.grid(row=row_index-1, column=1, sticky="ew", pady=2)

        tk.Label(parent, text="Icon Path:").grid(row=row_index, column=0, sticky="w", pady=2); row_index += 1
        icon_frame = tk.Frame(parent)
        icon_frame.grid(row=row_index-1, column=1, sticky="ew")
        icon_frame.columnconfigure(0, weight=1)
        self.icon_path_entry = tk.Entry(icon_frame, textvariable=self.icon_path_var)
        self.icon_path_entry.grid(row=0, column=0, sticky="ew")
        tk.Button(icon_frame, text="Browse...", command=self.browse_icon).grid(row=0, column=1, padx=(5,2))
        self.fetch_button = tk.Button(icon_frame, text="Fetch from SteamGridDB", command=self.start_fetch_icon)
        self.fetch_button.grid(row=0, column=2)

        tk.Label(parent, text="GameScope Options:").grid(row=row_index, column=0, sticky="w", pady=2); row_index += 1
        self.gamescope_entry = tk.Entry(parent, textvariable=self.gamescope_var)
        self.gamescope_entry.grid(row=row_index-1, column=1, sticky="ew", pady=2)

        tk.Label(parent, text="Runtime:").grid(row=row_index, column=0, sticky="w", pady=2); row_index += 1
        runtime_options = ["none", "linux", "windows", "nes", "snes", "megadrive", "nintendo64"]
        self.runtime_menu = tk.OptionMenu(parent, self.runtime_var, *runtime_options)
        self.runtime_menu.grid(row=row_index-1, column=1, sticky="ew", pady=2)

        tk.Label(parent, text="Proton/Wine Path:").grid(row=row_index, column=0, sticky="w", pady=2); row_index += 1
        proton_frame = tk.Frame(parent)
        proton_frame.grid(row=row_index-1, column=1, sticky="ew")
        proton_frame.columnconfigure(0, weight=1)
        self.proton_path_entry = tk.Entry(proton_frame, textvariable=self.proton_path_var)
        self.proton_path_entry.grid(row=0, column=0, sticky="ew")
        tk.Button(proton_frame, text="Browse...", command=self.browse_proton).grid(row=0, column=1, padx=(5,0))

        self.dpad_fix_checkbox = tk.Checkbutton(
            parent,
            text="Enable D-Pad reversal fix for native Linux games (Kazeta+ only)",
            variable=self.dpad_fix_var,
            command=self._update_preview
        )
        self.dpad_fix_checkbox.grid(row=row_index, column=0, columnspan=2, sticky="w", pady=2); row_index += 1

        download_frame = tk.LabelFrame(parent, text="Download runtimes", padx=10, pady=10)
        download_frame.grid(row=row_index, column=0, columnspan=2, sticky="ew", pady=10); row_index += 1
        download_frame.columnconfigure(0, weight=1)

        button_container = tk.Frame(download_frame)
        button_container.grid(row=0, column=0)
        runtime_buttons = ["Linux", "Windows", "NES", "SNES", "Sega Genesis/Mega Drive", "Nintendo 64"]
        for r_name in runtime_buttons:
            tk.Button(button_container, text=r_name, command=lambda n=r_name: self.download_runtime(n)).pack(side=tk.LEFT, padx=3)

        # KZI File Preview Box - Increased height
        preview_frame = tk.LabelFrame(parent, text="KZI File Preview", padx=10, pady=5)
        preview_frame.grid(row=row_index, column=0, columnspan=2, sticky="ew", pady=5); row_index += 1
        self.preview_text = scrolledtext.ScrolledText(preview_frame, height=10, wrap=tk.WORD, state=tk.DISABLED) # Increased height
        self.preview_text.pack(fill=tk.BOTH, expand=True)

        bottom_bar = tk.Frame(parent)
        bottom_bar.grid(row=row_index, column=0, columnspan=2, sticky="ew", pady=(10,0)); row_index += 1
        bottom_bar.columnconfigure(1, weight=1) # Spacer column
        bottom_bar.columnconfigure(3, weight=1) # Spacer column

        # Button rearrangement
        tk.Button(bottom_bar, text="Load .kzi File", command=self.load_kzi_file).grid(row=0, column=0, sticky="w", padx=(0, 5))
        tk.Button(bottom_bar, text="Unload Cartridge", command=self.unload_cartridge).grid(row=0, column=1, sticky="w") # New button
        tk.Button(bottom_bar, text="About", command=lambda: show_about_window(self.root)).grid(row=0, column=2)
        tk.Button(bottom_bar, text="Test Cartridge", command=self.test_cartridge).grid(row=0, column=3, sticky="e", padx=(5, 5)) # Moved closer
        tk.Button(bottom_bar, text="Generate .kzi File", command=self.generate_kzi).grid(row=0, column=4, sticky="e")

    def browse_executable(self):
        filetypes = [
            ("All files", "*.*"),
            ("Windows Executables", "*.exe"),
            ("Linux Executables", "*.x86_64 *.sh *.AppImage"),
            ("NES ROMs", "*.nes"),
            ("SNES ROMs", "*.sfc"),
            ("Nintendo 64 ROMs", "*.n64 *.z64"),
            ("Sega Genesis/Mega Drive ROMs", "*.bin"),
        ]
        filepath = filedialog.askopenfilename(
            title="Select Executable File",
            initialdir=get_default_media_path(),
            filetypes=filetypes
        )
        if filepath:
            self.exec_path_var.set(filepath)

    def browse_proton(self):
        filepath = filedialog.askopenfilename(
            title="Select Proton/Wine Executable",
            initialdir=os.path.expanduser("~/.steam/root/compatibilitytools.d")
        )
        if filepath:
            self.proton_path_var.set(filepath)

    def browse_icon(self):
        filepath = filedialog.askopenfilename(
            title="Select Icon File",
            initialdir=get_default_media_path(),
            filetypes=(("PNG files", "*.png"), ("All files", "*.*"))
        )
        if filepath:
            self.icon_path_var.set(filepath)

    def start_fetch_icon(self):
        handle_fetch_icon_flow(self)

    def test_cartridge(self):
        exec_path = self.exec_path_var.get().strip()
        params = self.params_var.get().strip()
        runtime = self.runtime_var.get()
        proton_path = self.proton_path_var.get().strip()
        env = None

        if not exec_path:
            messagebox.showerror("Error", "Executable Path must be specified.")
            return

        work_dir = os.path.dirname(exec_path)

        if is_steam_running():
            messagebox.showwarning("Steam is Running", "Please close Steam before testing.")

        command = []
        if runtime == "windows":
            if proton_path:
                command.extend([proton_path, "run"])
                env = os.environ.copy()
                compat_path = os.path.join(work_dir, 'compatdata')
                os.makedirs(compat_path, exist_ok=True)
                env['STEAM_COMPAT_DATA_PATH'] = compat_path

                steam_install_paths = [
                    os.path.expanduser("~/.steam/steam"),
                    os.path.expanduser("~/.steam/root"),
                    os.path.expanduser("~/.local/share/Steam")
                ]
                steam_client_path = next((path for path in steam_install_paths if os.path.isdir(path)), None)

                if steam_client_path:
                    env['STEAM_COMPAT_CLIENT_INSTALL_PATH'] = steam_client_path
                else:
                    messagebox.showwarning("Steam Not Found", "Could not find Steam installation path. Proton may fail.")
            else:
                command.append("wine")
        elif runtime not in ["none", "linux"]:
            messagebox.showerror("Unsupported Runtime", f"The '{runtime}' runtime cannot be tested directly.")
            return

        command.append(exec_path)
        if params:
            command.extend(shlex.split(params))

        run_command_in_new_terminal(command, env=env, cwd=work_dir)

    def generate_kzi(self):
        game_id = self.game_id_var.get().strip()
        exec_path = self.exec_path_var.get().strip()
        runtime = self.runtime_var.get()
        apply_dpad_fix = self.dpad_fix_var.get()

        if not all([self.game_name_var.get().strip(), game_id, exec_path]):
             messagebox.showerror("Error", "Game Name, ID, and Executable Path are required.")
             return

        if not re.match(r'^[a-z0-9-]+$', game_id):
             messagebox.showerror("Invalid ID", "The 'Game ID' field can only contain lowercase letters, numbers, and hyphens.")
             return

        if apply_dpad_fix and runtime not in ["none", "linux"]:
            proceed = messagebox.askyesno(
                "Confirm D-Pad Fix",
                "The D-Pad reversal fix is usually only needed for native Linux games.\n"
                f"Your selected runtime is '{runtime}'.\n\n"
                "Do you still want to include the fix in the .kzi file?",
                icon='warning'
            )
            if not proceed:
                return

        kzi_filepath = filedialog.asksaveasfilename(
            defaultextension=".kzi",
            filetypes=[("Kazeta Info files", "*.kzi")],
            initialdir=get_default_media_path(),
            initialfile=f"{game_id}.kzi",
            title="Save .kzi File"
        )
        if not kzi_filepath:
            return

        try:
            kzi_dir = os.path.dirname(kzi_filepath)
            # Use the directory where the KZI file is being saved as the base for relpath
            content = self._get_kzi_content(for_preview=False, kzi_save_dir=kzi_dir)

            with open(kzi_filepath, "w") as f:
                f.write(content)

            messagebox.showinfo("Success", f"Successfully generated {os.path.basename(kzi_filepath)}")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")

    def load_kzi_file(self):
        kzi_filepath = filedialog.askopenfilename(
            title="Load .kzi File",
            initialdir=get_default_media_path(),
            filetypes=((".kzi files", "*.kzi"), ("All files", "*.*"))
        )
        if not kzi_filepath:
            return

        self.unload_cartridge() # Clear fields before loading

        try:
            kzi_dir = os.path.dirname(kzi_filepath)

            parsed_data = {}
            with open(kzi_filepath, 'r') as f:
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        parsed_data[key.lower()] = value

            self.game_name_var.set(parsed_data.get('name', ''))
            self.game_id_var.set(parsed_data.get('id', '')) # ID update will trigger preview
            self.gamescope_var.set(parsed_data.get('gamescopeoptions', ''))
            self.runtime_var.set(parsed_data.get('runtime', 'none'))

            if 'icon' in parsed_data and parsed_data['icon']:
                icon_full_path = os.path.abspath(os.path.join(kzi_dir, parsed_data['icon']))
                self.icon_path_var.set(icon_full_path)

            if 'exec' in parsed_data and parsed_data['exec']:
                value = parsed_data['exec']
                # Updated regex to handle quoted paths potentially anywhere
                match = re.match(r'^(?:"([^"]+)"|([^\s]+))(?:\s+(.*))?$', value)
                if match:
                    path_part = match.group(1) or match.group(2)
                    params = match.group(3) or ""
                    # Ensure path_part exists before trying to join
                    if path_part:
                         exec_full_path = os.path.abspath(os.path.join(kzi_dir, path_part))
                         self.exec_path_var.set(exec_full_path)
                         self.params_var.set(params)


            if 'preexec' in parsed_data and 'postexec' in parsed_data:
                 if "steam-deck-dpad-fix" in parsed_data['preexec']:
                      self.dpad_fix_var.set(True)

            self._update_preview() # Ensure preview updates after all loading

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load .kzi file: {e}")

    def unload_cartridge(self):
        """Clears all input fields in the UI."""
        for var in [self.game_name_var, self.game_id_var, self.exec_path_var,
                      self.params_var, self.icon_path_var, self.gamescope_var, self.proton_path_var]:
            var.set("")
        self.runtime_var.set("none")
        self.dpad_fix_var.set(False)
        self._update_preview() # Clear preview too


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
                    buffer = response.read(1024 * 1024)
                    if not buffer:
                        break

                    out_file.write(buffer)
                    downloaded += len(buffer)

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
