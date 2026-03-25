#!/usr/bin/env python3
# ISO Creator and Burner for KZI File Generator

import os
import subprocess
import shutil
import glob
import time
import wave

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QTabWidget,
    QWidget, QLabel, QLineEdit, QPushButton, QComboBox, QProgressBar,
    QFileDialog, QMessageBox, QListWidget, QAbstractItemView, QListWidgetItem
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

# --- Background Worker for Creating ISO ---
class CreateIsoWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, source, save_path):
        super().__init__()
        self.source = source
        self.save_path = save_path

    def run(self):
        try:
            cmd = ['genisoimage', '-o', self.save_path, '-J', '-R', self.source]
            process = subprocess.run(cmd, capture_output=True, text=True)

            if process.returncode != 0:
                raise Exception(f"genisoimage failed:\n{process.stderr}")

            self.finished.emit(self.save_path)
        except Exception as e:
            self.error.emit(str(e))


# --- Background Worker for Burning (Wodim) ---
class WodimWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(int, str) # Return code, error details

    def __init__(self, cmd):
        super().__init__()
        self.cmd = cmd

    def run(self):
        try:
            process = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            output_log = []

            # Read output live
            for line in process.stdout:
                output_log.append(line)
                if "written" in line and "%" in line:
                    self.progress.emit(line.strip())

            process.wait()

            if process.returncode == 0:
                self.finished.emit()
            else:
                error_details = "".join(output_log[-15:])
                self.error.emit(process.returncode, error_details)

        except Exception as e:
            self.error.emit(-1, str(e))


class IsoBurnerWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create & Burn Disc (Data or Audio)")
        self.resize(650, 600)
        self.setWindowModality(Qt.WindowModality.WindowModal)

        self.setup_ui()
        self.scan_optical_drives()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Global: Drive Selection ---
        drive_group = QGroupBox("Target Optical Drive")
        drive_layout = QHBoxLayout(drive_group)

        self.drive_combo = QComboBox()
        self.btn_refresh_drives = QPushButton("Refresh")
        self.btn_refresh_drives.clicked.connect(self.scan_optical_drives)

        drive_layout.addWidget(self.drive_combo, stretch=1)
        drive_layout.addWidget(self.btn_refresh_drives)
        main_layout.addWidget(drive_group)

        # --- Tabs ---
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Tab 1: Data / Game ISO
        self.tab_data = QWidget()
        self.setup_data_tab(self.tab_data)
        self.tabs.addTab(self.tab_data, "Data / Game ISO")

        # Tab 2: Audio CD
        self.tab_audio = QWidget()
        self.setup_audio_tab(self.tab_audio)
        self.tabs.addTab(self.tab_audio, "Audio CD")

        # --- Global: Status ---
        status_layout = QVBoxLayout()
        self.status_label = QLabel("Ready")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.progress_bar)
        main_layout.addLayout(status_layout)

    def setup_data_tab(self, parent_widget):
        layout = QVBoxLayout(parent_widget)

        # Section 1: Source
        source_group = QGroupBox("1. Source Selection")
        source_layout = QGridLayout(source_group)

        source_layout.addWidget(QLabel("Game Folder:"), 0, 0)
        self.source_input = QLineEdit()
        source_layout.addWidget(self.source_input, 0, 1)

        self.btn_browse_source = QPushButton("Browse...")
        self.btn_browse_source.clicked.connect(self.browse_source_folder)
        source_layout.addWidget(self.btn_browse_source, 0, 2)

        self.btn_create_iso = QPushButton("Create ISO from Folder")
        self.btn_create_iso.clicked.connect(self.start_create_iso)
        source_layout.addWidget(self.btn_create_iso, 1, 1, 1, 2) # Span columns
        layout.addWidget(source_group)

        # Section 2: Burn
        iso_group = QGroupBox("2. Burn ISO Image")
        iso_layout = QGridLayout(iso_group)

        iso_layout.addWidget(QLabel("ISO File:"), 0, 0)
        self.iso_input = QLineEdit()
        iso_layout.addWidget(self.iso_input, 0, 1)

        self.btn_browse_iso = QPushButton("Browse...")
        self.btn_browse_iso.clicked.connect(self.browse_iso_file)
        iso_layout.addWidget(self.btn_browse_iso, 0, 2)

        self.btn_burn_iso = QPushButton("Burn ISO to Disc")
        self.btn_burn_iso.setMinimumHeight(40)
        self.btn_burn_iso.clicked.connect(self.start_burn_iso)
        iso_layout.addWidget(self.btn_burn_iso, 1, 1, 1, 2)
        layout.addWidget(iso_group)

        layout.addStretch() # Push everything to top

    def setup_audio_tab(self, parent_widget):
        layout = QVBoxLayout(parent_widget)

        info_lbl = QLabel("Add WAV files (16-bit, 44.1kHz). Track order matters.")
        info_lbl.setStyleSheet("color: gray;")
        layout.addWidget(info_lbl)

        # Listbox for tracks
        self.track_listbox = QListWidget()
        self.track_listbox.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        layout.addWidget(self.track_listbox)

        # Stats Label
        self.audio_stats_label = QLabel("Total Time: 00:00 | Total Size: 0.00 MB")
        self.audio_stats_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.audio_stats_label)

        # Toolbar
        toolbar_layout = QHBoxLayout()

        btn_add = QPushButton("Add Files...")
        btn_add.clicked.connect(self.add_audio_files)

        btn_remove = QPushButton("Remove")
        btn_remove.clicked.connect(self.remove_audio_track)

        btn_clear = QPushButton("Clear All")
        btn_clear.clicked.connect(self.clear_audio_tracks)

        btn_up = QPushButton("Move Up")
        btn_up.clicked.connect(lambda: self.move_track(-1))

        btn_down = QPushButton("Move Down")
        btn_down.clicked.connect(lambda: self.move_track(1))

        toolbar_layout.addWidget(btn_add)
        toolbar_layout.addWidget(btn_remove)
        toolbar_layout.addWidget(btn_clear)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(btn_up)
        toolbar_layout.addWidget(btn_down)
        layout.addLayout(toolbar_layout)

        self.btn_burn_audio = QPushButton("Burn Audio CD")
        self.btn_burn_audio.setMinimumHeight(40)
        self.btn_burn_audio.clicked.connect(self.start_burn_audio)
        layout.addWidget(self.btn_burn_audio)

    # --- Drive Logic ---
    def scan_optical_drives(self):
        self.drive_combo.clear()
        drives = []
        try:
            result = subprocess.run(['wodim', '--devices'], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                if '/dev/' in line:
                    parts = line.split()
                    for part in parts:
                        if part.startswith('/dev/'):
                            drives.append(part.strip("'"))
                            break
        except FileNotFoundError:
            QMessageBox.critical(self, "Missing Dependency", "The tool 'wodim' is required to detect drives and burn discs.\nPlease install it (e.g., 'sudo dnf install wodim').")

        # Fallback
        if not drives:
            drives = glob.glob('/dev/sr*')

        if drives:
            self.drive_combo.addItems(drives)
            self.drive_combo.setCurrentIndex(0)
        else:
            self.drive_combo.addItem("No drives found")

    # --- Data / ISO Logic ---
    def browse_source_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Source Directory")
        if path:
            self.source_input.setText(path)

    def browse_iso_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select ISO Image", "", "ISO Image (*.iso);;All files (*.*)")
        if path:
            self.iso_input.setText(path)

    def start_create_iso(self):
        source = self.source_input.text().strip()

        if not source or not os.path.isdir(source):
            QMessageBox.critical(self, "Error", "Please select a valid source folder first.")
            return

        kzi_files = glob.glob(os.path.join(source, "*.kzi"))
        if not kzi_files:
            QMessageBox.critical(self, "Error", "No .kzi file found in the selected folder.\nPlease ensure the game folder contains a valid Kazeta cartridge definition.")
            return

        kzi_basename = os.path.splitext(os.path.basename(kzi_files[0]))[0]
        default_name = f"{kzi_basename}.iso"

        save_path, _ = QFileDialog.getSaveFileName(self, "Save ISO As...", default_name, "ISO Image (*.iso)")
        if not save_path:
            return

        self._toggle_ui(False)
        self.status_label.setText(f"Generating ISO: {os.path.basename(save_path)}...")
        self.progress_bar.setRange(0, 0) # Indeterminate mode

        self.iso_worker = CreateIsoWorker(source, save_path)
        self.iso_worker.finished.connect(self.on_iso_created)
        self.iso_worker.error.connect(self.on_worker_error)
        self.iso_worker.start()

    def on_iso_created(self, save_path):
        self._toggle_ui(True)
        self.iso_input.setText(save_path)
        QMessageBox.information(self, "Success", "ISO created successfully!")

    def start_burn_iso(self):
        iso_file = self.iso_input.text().strip()
        drive = self.drive_combo.currentText()

        if not iso_file or not os.path.exists(iso_file):
            QMessageBox.critical(self, "Error", "Please select a valid ISO file.")
            return
        if not drive or "/dev/" not in drive:
            QMessageBox.critical(self, "Error", "Please select a valid optical drive.")
            return

        reply = QMessageBox.question(
            self, "Confirm Burn",
            f"Are you sure you want to burn '{os.path.basename(iso_file)}' to {drive}?\nThis will erase any re-writable data on the disc.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.No:
            return

        self._toggle_ui(False)
        self.status_label.setText("Waiting for authentication...")
        self.progress_bar.setRange(0, 0)

        wodim_path = shutil.which('wodim')
        if not wodim_path:
            self._toggle_ui(True)
            QMessageBox.critical(self, "Error", "wodim not found. Please install 'cdrkit' or 'wodim'.")
            return

        cmd = ['pkexec', wodim_path, '-v', '-eject', '-dao', f'dev={drive}', iso_file]

        self.burn_worker = WodimWorker(cmd)
        self.burn_worker.progress.connect(self.update_burn_progress)
        self.burn_worker.finished.connect(self.on_burn_success)
        self.burn_worker.error.connect(self.on_burn_error)
        self.burn_worker.start()

    # --- Audio Tab Logic ---
    def _get_audio_tracks(self):
        """Helper to extract filepaths stored in the list widget"""
        tracks = []
        for i in range(self.track_listbox.count()):
            item = self.track_listbox.item(i)
            # Retrieve the path we hid inside the Qt Item Role
            tracks.append(item.data(Qt.ItemDataRole.UserRole))
        return tracks

    def add_audio_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Audio Tracks", "", "WAV Files (*.wav)")
        if files:
            for path in files:
                display_text = self._get_track_display_text(path)
                item = QListWidgetItem(display_text)
                # Store the absolute path securely inside the item object
                item.setData(Qt.ItemDataRole.UserRole, path)
                self.track_listbox.addItem(item)
            self.update_audio_stats()

    def _get_track_display_text(self, path):
        filename = os.path.basename(path)
        duration_str = "--:--"
        try:
            with wave.open(path, 'r') as wav:
                frames = wav.getnframes()
                rate = wav.getframerate()
                duration = frames / float(rate)
                mins = int(duration // 60)
                secs = int(duration % 60)
                duration_str = f"{mins:02d}:{secs:02d}"
        except Exception:
            pass

        return f"{filename}   [{duration_str}]"

    def remove_audio_track(self):
        # Delete from bottom to top to prevent index shifting
        for item in self.track_listbox.selectedItems():
            self.track_listbox.takeItem(self.track_listbox.row(item))
        self.update_audio_stats()

    def clear_audio_tracks(self):
        self.track_listbox.clear()
        self.update_audio_stats()

    def move_track(self, direction):
        selected = self.track_listbox.selectedItems()
        if not selected:
            return

        # We only move the first selected item for simplicity
        item = selected[0]
        row = self.track_listbox.row(item)
        new_row = row + direction

        if 0 <= new_row < self.track_listbox.count():
            self.track_listbox.takeItem(row)
            self.track_listbox.insertItem(new_row, item)
            item.setSelected(True)

    def update_audio_stats(self):
        total_seconds = 0.0
        total_size_bytes = 0
        tracks = self._get_audio_tracks()

        for track_path in tracks:
            try:
                total_size_bytes += os.path.getsize(track_path)
                with wave.open(track_path, 'r') as wav:
                    frames = wav.getnframes()
                    rate = wav.getframerate()
                    duration = frames / float(rate)
                    total_seconds += duration
            except Exception:
                pass

        mins = int(total_seconds // 60)
        secs = int(total_seconds % 60)
        size_mb = total_size_bytes / (1024 * 1024)

        status_text = f"Total Time: {mins:02d}:{secs:02d} | Total Size: {size_mb:.2f} MB"
        self.audio_stats_label.setText(status_text)

        # Color coding warning
        if mins >= 80:
            self.audio_stats_label.setStyleSheet("font-weight: bold; color: red;")
        else:
            self.audio_stats_label.setStyleSheet("font-weight: bold; color: palette(text);")

    def start_burn_audio(self):
        drive = self.drive_combo.currentText()
        tracks = self._get_audio_tracks()

        if not drive or "/dev/" not in drive:
            QMessageBox.critical(self, "Error", "Please select a valid optical drive.")
            return

        if not tracks:
            QMessageBox.critical(self, "Error", "Please add at least one .wav file.")
            return

        reply = QMessageBox.question(
            self, "Confirm Audio Burn",
            f"Burn {len(tracks)} tracks to {drive}?\nEnsure files are 16-bit 44.1kHz WAVs.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.No:
            return

        self._toggle_ui(False)
        self.status_label.setText("Waiting for authentication...")
        self.progress_bar.setRange(0, 0)

        wodim_path = shutil.which('wodim')
        if not wodim_path:
            self._toggle_ui(True)
            QMessageBox.critical(self, "Error", "wodim not found. Please install 'cdrkit' or 'wodim'.")
            return

        cmd = ['pkexec', wodim_path, '-v', '-eject', '-dao', '-audio', '-pad', f'dev={drive}']
        cmd.extend(tracks)

        self.burn_worker = WodimWorker(cmd)
        self.burn_worker.progress.connect(self.update_burn_progress)
        self.burn_worker.finished.connect(self.on_burn_success)
        self.burn_worker.error.connect(self.on_burn_error)
        self.burn_worker.start()

    # --- Shared Burn Slots ---
    def update_burn_progress(self, progress_text):
        self.status_label.setText(progress_text)

    def on_burn_success(self):
        self._toggle_ui(True)
        QMessageBox.information(self, "Success", "Burning complete! Disc ejected.")

    def on_burn_error(self, returncode, error_details):
        self._toggle_ui(True)
        if returncode in [126, 127]:
            QMessageBox.critical(self, "Error", "Authentication failed or cancelled.")
        else:
            QMessageBox.critical(self, "Error", f"Burning failed.\n\nDetails:\n{error_details}")

    def on_worker_error(self, err_msg):
        self._toggle_ui(True)
        QMessageBox.critical(self, "Error", err_msg)

    def _toggle_ui(self, enable):
        self.tabs.setEnabled(enable)
        self.btn_burn_iso.setEnabled(enable)
        self.btn_burn_audio.setEnabled(enable)

        if enable:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.status_label.setText("Ready")


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = IsoBurnerWindow()
    window.show()
    sys.exit(app.exec())
