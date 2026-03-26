#!/usr/bin/env python3
# KZI File Generator - A GUI for creating .kzi cartridge files for Kazeta

import sys
import os
import getpass
import time
import re
import subprocess
import shlex
import shutil
import urllib.request
import webbrowser

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QLineEdit, QPushButton, QComboBox, QCheckBox,
    QTextEdit, QLabel, QFileDialog, QMessageBox, QGroupBox,
    QProgressBar, QDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QIcon

# Import from our other modules
from about_window import show_about_window
from erofs_manager import ErofsManagerWindow
from iso_burner import IsoBurnerWindow
from steamgriddb_api import handle_fetch_icon_flow
from steamgriddb_api import ssl_context
from theme_creator import KazetaThemeCreator

def get_default_media_path():
    username = getpass.getuser()
    possible_paths = [f"/run/media/{username}", f"/media/{username}", "/media"]
    for path in possible_paths:
        if os.path.isdir(path):
            return path
    home_dir = os.path.expanduser("~")
    for path in [os.path.join(home_dir, "media"), os.path.join(home_dir, "run/media")]:
        if os.path.isdir(path):
            return path
    return home_dir

def is_steam_running():
    try:
        subprocess.check_call(['pgrep', '-x', 'steam'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def run_command_in_new_terminal(command_list, env=None, cwd=None):
    if len(command_list) == 1 and ' ' in command_list[0]:
         command_string = command_list[0]
    else:
         command_string = shlex.join(command_list)

    cd_command = f'cd {shlex.quote(cwd)} && ' if cwd else ''
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

    # --- THE FIX: Clean the environment to prevent LD_LIBRARY_PATH poisoning ---
    clean_env = env.copy() if env else os.environ.copy()

    # AppImage and PyInstaller save the original paths with an "_ORIG" suffix.
    # We restore the original paths (or delete the overrides) before launching the host terminal.
    for key in ['LD_LIBRARY_PATH', 'QT_PLUGIN_PATH']:
        orig_key = f"{key}_ORIG"
        if orig_key in clean_env:
            clean_env[key] = clean_env[orig_key]
        elif key in clean_env:
            del clean_env[key]
    # -------------------------------------------------------------------------

    for term, flag in terminals:
        if shutil.which(term):
            try:
                final_command = [term, flag, 'bash', '-c', wrapper_script]
                # Pass the sanitized environment to the child process
                subprocess.Popen(final_command, env=clean_env)
                return
            except Exception as e:
                print(f"Warning: Failed to launch with {term}: {e}")
                continue

    print("Error: Could not automatically launch a terminal window.")


# --- Background Worker for Downloading ---
class DownloadWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, url, save_path):
        super().__init__()
        self.url = url
        self.save_path = save_path

    def run(self):
        try:
            # Spoof a standard web browser to bypass 403 CDN blocks
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            req = urllib.request.Request(self.url, headers=headers)

            # Pass the 'req' object instead of the raw string 'self.url'
            with urllib.request.urlopen(req, context=ssl_context) as response, open(self.save_path, 'wb') as out_file:
                total_size = int(response.getheader('Content-Length', 0))
                downloaded = 0
                start_time = time.time()

                while True:
                    buffer = response.read(1024 * 1024)
                    if not buffer:
                        break

                    out_file.write(buffer)
                    downloaded += len(buffer)

                    percent = int((downloaded / total_size) * 100) if total_size > 0 else 0
                    elapsed_time = time.time() - start_time
                    speed = (downloaded / elapsed_time) / (1024 * 1024) if elapsed_time > 0 else 0

                    status_text = (
                        f"{downloaded/1024/1024:.2f} MB / {total_size/1024/1024:.2f} MB "
                        f"({percent}%) at {speed:.2f} MB/s"
                    )
                    self.progress.emit(percent, status_text)

            self.finished.emit(self.save_path)
        except Exception as e:
            self.error.emit(str(e))


class KziGeneratorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kazeta Cartridge Generator")
        self.setMinimumWidth(650)

        # Apply Wayland Fallback Icon
        script_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(script_dir, "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.runtime_urls = {
            "Linux": "https://runtimes.kazeta.org/linux-1.0.kzr",
            "Linux 1.1": "https://github.com/the-outcaster/kazeta-plus/releases/download/runtimes/linux-1.1.kzr",
            "Windows": "https://runtimes.kazeta.org/windows-1.0.kzr",
            "Windows 1.1": "https://github.com/the-outcaster/kazeta-plus/releases/download/runtimes/windows-1.1.kzr",
            "Windows 1.2 (Experimental)": "https://github.com/the-outcaster/kazeta-plus/releases/download/runtimes/windows-1.2-experimental.kzr",
            "NES": "https://runtimes.kazeta.org/nes-1.0.kzr",
            "SNES": "https://runtimes.kazeta.org/snes-1.0.kzr",
            "Sega Genesis/Mega Drive": "https://runtimes.kazeta.org/megadrive-1.1.kzr",
            "Nintendo 64": "https://runtimes.kazeta.org/nintendo64-1.0.kzr",
            "Dreamcast": "https://github.com/the-outcaster/kazeta-plus/releases/download/runtimes/dreamcast-1.0.kzr",
            "GameCube/Wii": "https://github.com/the-outcaster/kazeta-plus/releases/download/runtimes/dolphin-1.0.kzr",
        }

        self.setup_ui()
        self.setup_menus()
        self.connect_signals()
        self._update_preview()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Base Form Layout (Always Visible Inputs) ---
        form_layout = QFormLayout()

        self.game_name_entry = QLineEdit()
        form_layout.addRow("Game Name:", self.game_name_entry)

        self.game_id_entry = QLineEdit()
        form_layout.addRow("Game ID:", self.game_id_entry)

        exec_layout = QHBoxLayout()
        self.exec_path_entry = QLineEdit()
        self.btn_browse_exec = QPushButton("Browse...")
        exec_layout.addWidget(self.exec_path_entry)
        exec_layout.addWidget(self.btn_browse_exec)
        form_layout.addRow("Executable Path:", exec_layout)

        icon_layout = QHBoxLayout()
        self.icon_path_entry = QLineEdit()
        self.btn_browse_icon = QPushButton("Browse...")
        self.btn_fetch_icon = QPushButton("Fetch from SteamGridDB")
        icon_layout.addWidget(self.icon_path_entry)
        icon_layout.addWidget(self.btn_browse_icon)
        icon_layout.addWidget(self.btn_fetch_icon)
        form_layout.addRow("Icon Path:", icon_layout)

        self.runtime_menu = QComboBox()
        self.populate_runtime_dropdown()
        form_layout.addRow("Runtime:", self.runtime_menu)

        main_layout.addLayout(form_layout)

        # --- Option Toggles (Side-by-Side) ---
        toggles_layout = QHBoxLayout()

        self.advanced_toggle = QCheckBox("Show Advanced Options")
        self.advanced_toggle.setStyleSheet("font-weight: bold; margin-top: 10px;")
        toggles_layout.addWidget(self.advanced_toggle)

        self.kazeta_plus_toggle = QCheckBox("Show Kazeta+ Options")
        self.kazeta_plus_toggle.setStyleSheet("font-weight: bold; margin-top: 10px; color: #a86a11;")
        toggles_layout.addWidget(self.kazeta_plus_toggle)

        toggles_layout.addStretch()
        main_layout.addLayout(toggles_layout)

        # --- Advanced Options Widget (Hidden by default) ---
        self.advanced_widget = QWidget()
        advanced_layout = QFormLayout(self.advanced_widget)
        advanced_layout.setContentsMargins(0, 5, 0, 5)

        self.params_entry = QLineEdit()
        advanced_layout.addRow("Additional Parameters:", self.params_entry)

        self.gamescope_entry = QLineEdit()
        advanced_layout.addRow("Gamescope Options:", self.gamescope_entry)

        proton_layout = QHBoxLayout()
        self.proton_path_entry = QLineEdit()
        self.btn_browse_proton = QPushButton("Browse...")
        proton_layout.addWidget(self.proton_path_entry)
        proton_layout.addWidget(self.btn_browse_proton)
        advanced_layout.addRow("Proton/Wine Path:", proton_layout)

        self.advanced_widget.setVisible(False)
        main_layout.addWidget(self.advanced_widget)

        # --- Kazeta+ Options Widget (Hidden by default) ---
        self.kazeta_plus_widget = QWidget()
        kazeta_plus_layout = QFormLayout(self.kazeta_plus_widget)
        kazeta_plus_layout.setContentsMargins(0, 0, 0, 10)

        controller_layout = QHBoxLayout()
        self.controller_profile_entry = QLineEdit()
        self.btn_browse_controller = QPushButton("Browse...")
        controller_layout.addWidget(self.controller_profile_entry)
        controller_layout.addWidget(self.btn_browse_controller)
        kazeta_plus_layout.addRow("Controller Profile (.yaml):", controller_layout)

        self.default_game_checkbox = QCheckBox("Set as the default game (for multi-carts, Kazeta+ only)")
        kazeta_plus_layout.addRow(self.default_game_checkbox)

        self.kazeta_plus_widget.setVisible(False)
        main_layout.addWidget(self.kazeta_plus_widget)

        # --- UPDATED: Download Section with Dropdowns ---
        download_group = QGroupBox("Download runtimes")
        download_layout = QVBoxLayout(download_group)

        runtime_categories = {
            "Linux": ["Linux", "Linux 1.1"],
            "Windows": ["Windows", "Windows 1.1", "Windows 1.2 (Experimental)"],
            "Emulators": ["NES", "SNES", "Sega Genesis/Mega Drive", "Nintendo 64", "Dreamcast", "GameCube/Wii"]
        }

        for category, runtimes in runtime_categories.items():
            row_layout = QHBoxLayout()

            label = QLabel(f"{category}:")
            label.setFixedWidth(80) # Cleanly align the labels
            row_layout.addWidget(label)

            combo = QComboBox()
            combo.addItems(runtimes)
            combo.setFixedWidth(220) # Uniform dropdown width
            row_layout.addWidget(combo)

            btn = QPushButton("Download")
            btn.setFixedWidth(100)
            # Use a lambda default argument (c=combo) to capture the specific combobox for this row!
            btn.clicked.connect(lambda checked, c=combo: self.download_runtime(c.currentText()))
            row_layout.addWidget(btn)

            row_layout.addStretch()
            download_layout.addLayout(row_layout)

        main_layout.addWidget(download_group)

        # --- Preview Section ---
        preview_group = QGroupBox("KZI File Preview")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMinimumHeight(150) # Forces the window to grow instead of squishing this box
        preview_layout.addWidget(self.preview_text)
        main_layout.addWidget(preview_group)

        # --- Bottom Bar ---
        bottom_layout = QHBoxLayout()
        self.btn_load = QPushButton("Load .kzi File")
        self.btn_unload = QPushButton("Unload Cartridge")
        self.btn_test = QPushButton("Test Cartridge")
        self.btn_generate = QPushButton("Generate .kzi File")

        bottom_layout.addWidget(self.btn_load)
        bottom_layout.addWidget(self.btn_unload)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btn_test)
        bottom_layout.addWidget(self.btn_generate)

        main_layout.addLayout(bottom_layout)

    def populate_runtime_dropdown(self):
        def add_category_header(title):
            self.runtime_menu.addItem(title)
            idx = self.runtime_menu.count() - 1
            item = self.runtime_menu.model().item(idx)
            item.setEnabled(False)
            font = item.font()
            font.setBold(True)
            item.setFont(font)

        self.runtime_menu.addItem("None", "none")
        self.runtime_menu.insertSeparator(self.runtime_menu.count())

        add_category_header("--- Linux ---")
        self.runtime_menu.addItem("Linux 1.0", "linux")
        self.runtime_menu.addItem("Linux 1.1", "linux-1.1")

        self.runtime_menu.insertSeparator(self.runtime_menu.count())
        add_category_header("--- Windows ---")
        self.runtime_menu.addItem("Windows 1.0", "windows")
        self.runtime_menu.addItem("Windows 1.1", "windows-1.1")
        self.runtime_menu.addItem("Windows 1.2 (Experimental)", "windows-1.2")

        self.runtime_menu.insertSeparator(self.runtime_menu.count())
        add_category_header("--- Emulators ---")
        self.runtime_menu.addItem("NES", "nes")
        self.runtime_menu.addItem("SNES", "snes")
        self.runtime_menu.addItem("Sega Genesis / Mega Drive", "megadrive")
        self.runtime_menu.addItem("Nintendo 64", "nintendo64")
        self.runtime_menu.addItem("Dreamcast", "dreamcast")
        self.runtime_menu.addItem("GameCube / Wii (Dolphin)", "dolphin")

    def setup_menus(self):
        menubar = self.menuBar()

        func_menu = menubar.addMenu("Functions")

        erofs_action = QAction("Create Runtime/Game Package", self)
        erofs_action.triggered.connect(self.open_erofs_manager)
        func_menu.addAction(erofs_action)

        iso_action = QAction("Create Optical Media (Kazeta+)", self)
        iso_action.triggered.connect(self.open_iso_burner)
        func_menu.addAction(iso_action)

        theme_action = QAction("Create Theme (Kazeta+)", self)
        theme_action.triggered.connect(self.open_theme_creator)
        func_menu.addAction(theme_action)

        help_menu = menubar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(lambda: show_about_window(self))
        help_menu.addAction(about_action)

    def connect_signals(self):
        # Traces for live preview update
        self.game_name_entry.textChanged.connect(self._update_game_id)
        self.game_id_entry.textChanged.connect(self._update_preview)
        self.exec_path_entry.textChanged.connect(self._update_preview)
        self.params_entry.textChanged.connect(self._update_preview)
        self.icon_path_entry.textChanged.connect(self._update_preview)
        self.gamescope_entry.textChanged.connect(self._update_preview)
        self.controller_profile_entry.textChanged.connect(self._update_preview)

        self.runtime_menu.currentIndexChanged.connect(self._update_preview)
        self.default_game_checkbox.stateChanged.connect(self._update_preview)

        # UI Toggles
        self.advanced_toggle.toggled.connect(self.toggle_advanced_options)
        self.kazeta_plus_toggle.toggled.connect(self.toggle_kazeta_options)

        # Button clicks
        self.btn_browse_exec.clicked.connect(self.browse_executable)
        self.btn_browse_proton.clicked.connect(self.browse_proton)
        self.btn_browse_icon.clicked.connect(self.browse_icon)
        self.btn_browse_controller.clicked.connect(self.browse_controller)
        self.btn_fetch_icon.clicked.connect(self.start_fetch_icon)

        self.btn_load.clicked.connect(self.load_kzi_file)
        self.btn_unload.clicked.connect(self.unload_cartridge)
        self.btn_test.clicked.connect(self.test_cartridge)
        self.btn_generate.clicked.connect(self.generate_kzi)

    def toggle_advanced_options(self, checked):
        self.advanced_widget.setVisible(checked)
        self.adjust_window_height()

    def toggle_kazeta_options(self, checked):
        self.kazeta_plus_widget.setVisible(checked)
        self.adjust_window_height()

    def adjust_window_height(self):
        # Force Qt to immediately process the visibility changes
        QApplication.processEvents()
        # Resize the window to its new minimum required height, keeping the current width
        self.resize(self.width(), self.minimumSizeHint().height())

    def _update_game_id(self, text):
        sanitized_id = re.sub(r'[^a-z0-9-]', '', text.lower().replace(' ', '-'))
        if self.game_id_entry.text() != sanitized_id:
             self.game_id_entry.setText(sanitized_id)
        self._update_preview()

    def _get_kzi_content(self, for_preview=False, kzi_save_dir=None):
        game_name = self.game_name_entry.text().strip()
        game_id = self.game_id_entry.text().strip()
        exec_path = self.exec_path_entry.text().strip()
        params = self.params_entry.text().strip()
        icon_path = self.icon_path_entry.text().strip()
        gamescope_options = self.gamescope_entry.text().strip()
        controller_profile = self.controller_profile_entry.text().strip()

        runtime = self.runtime_menu.currentData()
        set_default = self.default_game_checkbox.isChecked()

        media_path_base = get_default_media_path()
        base_dir = kzi_save_dir if kzi_save_dir else media_path_base

        content_lines = []
        content_lines.append(f"Name={game_name}")
        content_lines.append(f"Id={game_id}")

        exec_command = ""
        if exec_path:
            if exec_path.startswith(media_path_base) or (kzi_save_dir and exec_path.startswith(kzi_save_dir)):
                try:
                    exec_command = os.path.relpath(exec_path, base_dir)
                except ValueError:
                    exec_command = exec_path

                if ' ' in exec_command and not exec_command.startswith('"'):
                    exec_command = f'"{exec_command}"'
            else:
                if os.path.isfile(exec_path) or os.path.isabs(exec_path):
                     exec_command = os.path.basename(exec_path)
                else:
                     exec_command = exec_path

            if params:
                exec_command += f" {params}"

        content_lines.append(f"Exec={exec_command}")

        relative_icon_path = ""
        if icon_path:
             try:
                 relative_icon_path = os.path.relpath(icon_path, base_dir)
             except ValueError:
                 relative_icon_path = icon_path
             content_lines.append(f"Icon={relative_icon_path}")

        if gamescope_options:
            content_lines.append(f"GamescopeOptions={gamescope_options}")

        if runtime and runtime != "none":
            content_lines.append(f"Runtime={runtime}")

        if controller_profile:
            controller_name = os.path.basename(controller_profile)
            content_lines.append(f"Controller={controller_name}")

        if set_default:
            content_lines.append("SetAsDefaultGame=true")

        return "\n".join(content_lines) + "\n"

    def _update_preview(self):
        content = self._get_kzi_content(for_preview=True)
        self.preview_text.setPlainText(content)

    def browse_executable(self):
        file_filter = "All files (*);;Windows Executables (*.exe);;Linux Executables (*.x86_64 *.sh *.AppImage);;NES ROMs (*.nes);;SNES ROMs (*.sfc);;Nintendo 64 ROMs (*.n64 *.z64);;Sega Genesis/Mega Drive ROMs (*.bin);;Dreamcast ROMs (*.cue *.chd *.gdi *.cdi);;GameCube/Wii ROMs (*.iso *.gcm *.wbfs *.rvz)"
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select Executable File", get_default_media_path(), file_filter
        )
        if filepath:
            self.exec_path_entry.setText(filepath)

    def browse_proton(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select Proton/Wine Executable", os.path.expanduser("~/.steam/root/compatibilitytools.d")
        )
        if filepath:
            self.proton_path_entry.setText(filepath)

    def browse_icon(self):
        file_filter = "PNG files (*.png);;All files (*.*)"
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select Icon File", get_default_media_path(), file_filter
        )
        if filepath:
            self.icon_path_entry.setText(filepath)

    def browse_controller(self):
        file_filter = "YAML Profiles (*.yaml);;All files (*.*)"
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select Controller Profile", get_default_media_path(), file_filter
        )
        if filepath:
            self.controller_profile_entry.setText(filepath)

    def start_fetch_icon(self):
        handle_fetch_icon_flow(self)

    def open_theme_creator(self):
        dialog = KazetaThemeCreator(self)
        dialog.exec()

    def open_erofs_manager(self):
        dialog = ErofsManagerWindow(self)
        dialog.exec()

    def open_iso_burner(self):
        dialog = IsoBurnerWindow(self)
        dialog.exec()

    def test_cartridge(self):
        exec_path = self.exec_path_entry.text().strip()
        params = self.params_entry.text().strip()
        runtime = self.runtime_menu.currentData()
        proton_path = self.proton_path_entry.text().strip()
        env = None

        if not exec_path:
            QMessageBox.critical(self, "Error", "Executable Path must be specified.")
            return

        work_dir = os.path.dirname(exec_path)

        if is_steam_running():
            QMessageBox.warning(self, "Steam is Running", "Please close Steam before testing.")

        command = []
        if runtime in ["windows", "windows-1.1", "windows-1.2"]:
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
                    QMessageBox.warning(self, "Steam Not Found", "Could not find Steam installation path. Proton may fail.")
            else:
                command.append("wine")
        elif runtime and runtime not in ["none", "linux", "linux-1.1"]:
            QMessageBox.critical(self, "Unsupported Runtime", f"The '{runtime}' runtime cannot be tested directly.")
            return

        full_command_string = exec_path
        if params:
            full_command_string += f" {params}"

        try:
             command.extend(shlex.split(full_command_string))
        except ValueError as e:
             QMessageBox.critical(self, "Parsing Error", f"Error parsing executable or parameters:\n{e}")
             return

        run_command_in_new_terminal(command, env=env, cwd=work_dir)

    def generate_kzi(self):
        game_id = self.game_id_entry.text().strip()
        exec_path = self.exec_path_entry.text().strip()
        media_path_base = get_default_media_path()

        if not all([self.game_name_entry.text().strip(), game_id, exec_path]):
             QMessageBox.critical(self, "Error", "Game Name, ID, and Executable Path are required.")
             return

        if not re.match(r'^[a-z0-9-]+$', game_id):
             QMessageBox.critical(self, "Invalid ID", "The 'Game ID' field can only contain lowercase letters, numbers, and hyphens.")
             return

        kzi_filepath, _ = QFileDialog.getSaveFileName(
            self, "Save .kzi File",
            os.path.join(media_path_base, f"{game_id}.kzi"),
            "Kazeta Info files (*.kzi)"
        )
        if not kzi_filepath:
            return

        try:
            kzi_dir = os.path.dirname(kzi_filepath)
            content = self._get_kzi_content(for_preview=False, kzi_save_dir=kzi_dir)

            with open(kzi_filepath, "w") as f:
                f.write(content)

            QMessageBox.information(self, "Success", f"Successfully generated {os.path.basename(kzi_filepath)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")

    def load_kzi_file(self):
        kzi_filepath, _ = QFileDialog.getOpenFileName(
            self, "Load .kzi File", get_default_media_path(), ".kzi files (*.kzi);;All files (*.*)"
        )
        if not kzi_filepath:
            return

        self.unload_cartridge()

        try:
            kzi_dir = os.path.dirname(kzi_filepath)
            parsed_data = {}
            with open(kzi_filepath, 'r') as f:
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        parsed_data[key.lower()] = value

            self.game_name_entry.setText(parsed_data.get('name', ''))
            self.game_id_entry.setText(parsed_data.get('id', ''))
            self.gamescope_entry.setText(parsed_data.get('gamescopeoptions', ''))

            runtime_val = parsed_data.get('runtime', 'none').lower()

            # Catch legacy or explicit 1.0 definitions and map them to our internal data values
            if runtime_val == 'windows-1.0':
                runtime_val = 'windows'
            elif runtime_val == 'linux-1.0':
                runtime_val = 'linux'

            idx = self.runtime_menu.findData(runtime_val)
            if idx >= 0:
                self.runtime_menu.setCurrentIndex(idx)

            if 'icon' in parsed_data and parsed_data['icon']:
                icon_full_path = os.path.abspath(os.path.join(kzi_dir, parsed_data['icon']))
                self.icon_path_entry.setText(icon_full_path)

            if 'controller' in parsed_data and parsed_data['controller']:
                self.controller_profile_entry.setText(parsed_data['controller'])

            if 'exec' in parsed_data and parsed_data['exec']:
                value = parsed_data['exec']
                match = re.match(r'^(?:"([^"]+)"|([^\s]+))(?:\s+(.*))?$', value)
                if match:
                    path_part = match.group(1) or match.group(2)
                    params = match.group(3) or ""

                    potential_path = os.path.abspath(os.path.join(kzi_dir, path_part))

                    if os.path.exists(potential_path):
                        self.exec_path_entry.setText(potential_path)
                    elif shutil.which(path_part):
                        self.exec_path_entry.setText(path_part)
                    else:
                        self.exec_path_entry.setText(path_part)

                    self.params_entry.setText(params)

            if 'setasdefaultgame' in parsed_data:
                self.default_game_checkbox.setChecked(parsed_data['setasdefaultgame'].lower() == 'true')

            # Expand the toggles if the user loaded a file utilizing them
            if self.params_entry.text() or self.gamescope_entry.text():
                self.advanced_toggle.setChecked(True)

            if self.default_game_checkbox.isChecked() or self.controller_profile_entry.text():
                self.kazeta_plus_toggle.setChecked(True)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load .kzi file: {e}")

    def unload_cartridge(self):
        self.game_id_entry.blockSignals(True)

        self.game_name_entry.clear()
        self.game_id_entry.clear()
        self.exec_path_entry.clear()
        self.params_entry.clear()
        self.icon_path_entry.clear()
        self.gamescope_entry.clear()
        self.proton_path_entry.clear()
        self.controller_profile_entry.clear()

        self.runtime_menu.setCurrentIndex(0)
        self.default_game_checkbox.setChecked(False)
        self.advanced_toggle.setChecked(False)
        self.kazeta_plus_toggle.setChecked(False)

        self.game_id_entry.blockSignals(False)
        self._update_preview()

    def download_runtime(self, name):
        url = self.runtime_urls[name]
        filename = os.path.basename(url)

        # Combine the default media path with the downloaded filename
        initial_path = os.path.join(get_default_media_path(), filename)

        save_path, _ = QFileDialog.getSaveFileName(self, f"Save {name} Runtime", initial_path)

        if not save_path:
            return

        self.progress_dialog = QDialog(self)
        self.progress_dialog.setWindowTitle("Downloading...")
        self.progress_dialog.setFixedSize(450, 150)
        layout = QVBoxLayout(self.progress_dialog)

        self.status_label = QLabel("Starting download...", self.progress_dialog)
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar(self.progress_dialog)
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        self.worker = DownloadWorker(url, save_path)
        self.worker.progress.connect(self.update_download_progress)
        self.worker.finished.connect(self.download_finished)
        self.worker.error.connect(self.download_error)

        self.worker.start()
        self.progress_dialog.exec()

    def update_download_progress(self, percent, status_text):
        self.progress_bar.setValue(percent)
        self.status_label.setText(status_text)

    def download_finished(self, save_path):
        self.progress_dialog.accept()
        QMessageBox.information(self, "Download Complete", f"Successfully downloaded {os.path.basename(save_path)}")

    def download_error(self, error_msg):
        self.progress_dialog.reject()
        QMessageBox.critical(self, "Download Failed", f"An error occurred: {error_msg}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setDesktopFileName("kazeta-cartridge-generator.desktop")

    window = KziGeneratorApp()
    window.show()
    sys.exit(app.exec())
