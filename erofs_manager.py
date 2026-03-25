#!/usr/bin/env python3
# EROFS Manager for KZI Generator
# Handles packing .kzr/.kzp files and mounting images

import os
import subprocess
import shutil
import glob
import time

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QGroupBox, QLineEdit, QPushButton, QRadioButton, QComboBox,
    QCheckBox, QLabel, QProgressBar, QFileDialog, QMessageBox,
    QButtonGroup
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

# --- Background Worker for Creating EROFS ---
class CreateWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, source, save_path, algo, single_thread):
        super().__init__()
        self.source = source
        self.save_path = save_path
        self.algo = algo
        self.single_thread = single_thread

    def run(self):
        try:
            mkfs = shutil.which("mkfs.erofs")
            if not mkfs:
                raise Exception("mkfs.erofs not found. Please install erofs-utils.")

            # 1. Build the base mkfs command
            base_cmd = [mkfs]

            if self.algo != "uncompressed":
                base_cmd.append(f"-z{self.algo}")

            base_cmd.extend([self.save_path, self.source])

            # 2. Handle Single Thread Mode
            final_cmd = base_cmd
            if self.single_thread:
                taskset = shutil.which("taskset")
                if not taskset:
                    raise Exception("taskset command not found (required for single thread mode).")
                # Prepend taskset -c 0
                final_cmd = [taskset, "-c", "0"] + base_cmd

            # 3. Run
            process = subprocess.run(final_cmd, capture_output=True, text=True)

            if process.returncode != 0:
                raise Exception(f"mkfs.erofs failed:\n{process.stderr}")

            self.finished.emit(self.save_path)

        except Exception as e:
            self.error.emit(str(e))


# --- Background Worker for Mounting/Unmounting ---
class MountWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, img_path, mount_point, action):
        super().__init__()
        self.img_path = img_path
        self.mount_point = mount_point
        self.action = action

    def run(self):
        try:
            mount_point = os.path.abspath(os.path.expanduser(self.mount_point))
            img_path = os.path.abspath(os.path.expanduser(self.img_path)) if self.img_path else None

            if self.action == "mount":
                erofsfuse = shutil.which("erofsfuse")
                if not erofsfuse:
                    raise Exception("erofsfuse not found. Please install 'erofs-utils' or 'erofsfuse'.")

                if not os.path.exists(mount_point):
                    os.makedirs(mount_point, exist_ok=True)

                if os.listdir(mount_point):
                    print(f"Warning: Mount point {mount_point} is not empty.")

                cmd = [erofsfuse, img_path, mount_point]

            else: # Unmount
                fusermount = shutil.which("fusermount")
                if not fusermount:
                     fusermount = "umount"
                cmd = [fusermount, '-u', mount_point]

            # Run the command
            process = subprocess.run(cmd, capture_output=True, text=True)

            if process.returncode != 0:
                raise Exception(f"{self.action.capitalize()} failed:\n{process.stderr}")

            # Verification Step
            if self.action == "mount":
                time.sleep(0.5) # Give the filesystem a moment to initialize
                if not os.path.ismount(mount_point):
                    raise Exception("Mount command finished, but the folder is not mounted.\nThe background process likely crashed (check permissions or FUSE version).")

            self.finished.emit(mount_point)

        except Exception as e:
            self.error.emit(str(e))


class ErofsManagerWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kazeta Package Manager (EROFS)")
        self.resize(600, 550)

        # Since this acts as a tool window, we make it modal to the main app
        self.setWindowModality(Qt.WindowModality.WindowModal)

        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Tabs ---
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Tab 1: Create
        self.tab_create = QWidget()
        self.setup_create_tab(self.tab_create)
        self.tabs.addTab(self.tab_create, "Create Package (.kzr/.kzp)")

        # Tab 2: Mount
        self.tab_mount = QWidget()
        self.setup_mount_tab(self.tab_mount)
        self.tabs.addTab(self.tab_mount, "Mount Image")

        # --- Status Bar ---
        status_layout = QVBoxLayout()
        self.status_label = QLabel("Ready")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.progress_bar)
        main_layout.addLayout(status_layout)

    def setup_create_tab(self, parent_widget):
        layout = QVBoxLayout(parent_widget)

        # Source
        src_group = QGroupBox("1. Source Folder")
        src_layout = QHBoxLayout(src_group)
        self.source_input = QLineEdit()
        self.btn_browse_src = QPushButton("Browse...")
        self.btn_browse_src.clicked.connect(self.browse_source)
        src_layout.addWidget(self.source_input)
        src_layout.addWidget(self.btn_browse_src)
        layout.addWidget(src_group)

        # Type Selection
        type_group = QGroupBox("2. Package Type")
        type_layout = QVBoxLayout(type_group)

        self.radio_kzr = QRadioButton("Runtime (.kzr) - Generic folders")
        self.radio_kzp = QRadioButton("Game Package (.kzp) - Must contain .kzi file")
        self.radio_kzr.setChecked(True) # Default

        self.type_btn_group = QButtonGroup(self)
        self.type_btn_group.addButton(self.radio_kzr)
        self.type_btn_group.addButton(self.radio_kzp)

        type_layout.addWidget(self.radio_kzr)
        type_layout.addWidget(self.radio_kzp)
        layout.addWidget(type_group)

        # Compression Options
        comp_group = QGroupBox("3. Compression Settings")
        comp_layout = QHBoxLayout(comp_group)

        comp_layout.addWidget(QLabel("Algorithm:"))
        self.algo_combo = QComboBox()
        self.algo_combo.addItems(['lz4', 'lz4hc', 'lzma', 'deflate', 'libdeflate', 'zstd', 'uncompressed'])
        comp_layout.addWidget(self.algo_combo)

        self.single_thread_check = QCheckBox("Single Thread Mode (taskset -c 0)")
        comp_layout.addWidget(self.single_thread_check)
        comp_layout.addStretch() # Push everything to the left
        layout.addWidget(comp_group)

        # Action Button
        layout.addStretch() # Push button to bottom
        self.btn_create = QPushButton("Create EROFS Image")
        self.btn_create.setMinimumHeight(40)
        self.btn_create.clicked.connect(self.start_creation)
        layout.addWidget(self.btn_create)

    def setup_mount_tab(self, parent_widget):
        layout = QVBoxLayout(parent_widget)

        # Image Input
        img_group = QGroupBox("Image File")
        img_layout = QHBoxLayout(img_group)
        self.mount_img_input = QLineEdit()
        self.btn_browse_img = QPushButton("Browse...")
        self.btn_browse_img.clicked.connect(self.browse_image_to_mount)
        img_layout.addWidget(self.mount_img_input)
        img_layout.addWidget(self.btn_browse_img)
        layout.addWidget(img_group)

        # Mount Point
        mnt_group = QGroupBox("Mount Point")
        mnt_layout = QVBoxLayout(mnt_group)

        row_layout = QHBoxLayout()
        self.mount_point_input = QLineEdit(os.path.expanduser("~/mnt"))
        self.btn_browse_mnt = QPushButton("Browse...")
        self.btn_browse_mnt.clicked.connect(self.browse_mount_point)
        row_layout.addWidget(self.mount_point_input)
        row_layout.addWidget(self.btn_browse_mnt)
        mnt_layout.addLayout(row_layout)

        note_label = QLabel("Note: Uses FUSE. No sudo required.")
        note_label.setStyleSheet("color: green; font-size: 11px;")
        mnt_layout.addWidget(note_label)
        layout.addWidget(mnt_group)

        # Buttons
        layout.addStretch()
        btn_layout = QHBoxLayout()
        self.btn_mount = QPushButton("Mount Image")
        self.btn_mount.setMinimumHeight(40)
        self.btn_mount.clicked.connect(self.start_mount)

        self.btn_unmount = QPushButton("Unmount Path")
        self.btn_unmount.setMinimumHeight(40)
        self.btn_unmount.clicked.connect(self.start_unmount)

        btn_layout.addWidget(self.btn_mount)
        btn_layout.addWidget(self.btn_unmount)
        layout.addLayout(btn_layout)

    # --- Helpers ---
    def browse_source(self):
        path = QFileDialog.getExistingDirectory(self, "Select Source Directory")
        if path:
            self.source_input.setText(path)

    def browse_image_to_mount(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select EROFS Image", "", "EROFS Images (*.kzr *.kzp *.img);;All files (*.*)"
        )
        if path:
            self.mount_img_input.setText(path)

    def browse_mount_point(self):
        path = QFileDialog.getExistingDirectory(self, "Select Mount Point Directory")
        if path:
            self.mount_point_input.setText(path)

    def _toggle_ui(self, enable):
        self.btn_create.setEnabled(enable)
        self.btn_mount.setEnabled(enable)
        self.btn_unmount.setEnabled(enable)
        self.tabs.setEnabled(enable) # Optionally lock the whole tab widget during ops

        if enable:
            self.progress_bar.setRange(0, 100) # Reset to determinate
            self.progress_bar.setValue(0)
            self.status_label.setText("Ready")
        else:
            self.progress_bar.setRange(0, 0) # Set to indeterminate (bouncing back and forth)

    # --- Logic: Create ---
    def start_creation(self):
        source = self.source_input.text().strip()
        pkg_type = "kzr" if self.radio_kzr.isChecked() else "kzp"

        if not source or not os.path.isdir(source):
            QMessageBox.critical(self, "Error", "Invalid source folder.")
            return

        if pkg_type == "kzp":
            kzi_files = glob.glob(os.path.join(source, "*.kzi"))
            if not kzi_files:
                QMessageBox.critical(self, "Error", "Selected folder must contain a .kzi file for .kzp packages.")
                return

        ext = f".{pkg_type}"
        default_name = f"package{ext}"
        if pkg_type == "kzp" and kzi_files:
            default_name = os.path.basename(kzi_files[0]).replace(".kzi", ext)

        save_path, _ = QFileDialog.getSaveFileName(
            self, f"Save {pkg_type.upper()} File", default_name, f"{pkg_type.upper()} Image (*{ext})"
        )

        if not save_path:
            return

        algo = self.algo_combo.currentText()
        single_thread = self.single_thread_check.isChecked()

        self._toggle_ui(False)
        self.status_label.setText("Packing EROFS image...")

        self.create_worker = CreateWorker(source, save_path, algo, single_thread)
        self.create_worker.finished.connect(self.on_create_finished)
        self.create_worker.error.connect(self.on_worker_error)
        self.create_worker.start()

    def on_create_finished(self, save_path):
        self._toggle_ui(True)
        QMessageBox.information(self, "Success", f"Created {os.path.basename(save_path)}")

    # --- Logic: Mount/Unmount ---
    def start_mount(self):
        img = self.mount_img_input.text().strip()
        mnt = self.mount_point_input.text().strip()

        if not img or not os.path.exists(img):
            QMessageBox.critical(self, "Error", "Invalid image file.")
            return
        if not mnt:
            QMessageBox.critical(self, "Error", "Mount point is required.")
            return

        self._toggle_ui(False)
        self.status_label.setText("Performing mount...")

        self.mount_worker = MountWorker(img, mnt, "mount")
        self.mount_worker.finished.connect(lambda p: self.on_mount_action_finished("mount", p))
        self.mount_worker.error.connect(self.on_worker_error)
        self.mount_worker.start()

    def start_unmount(self):
        mnt = self.mount_point_input.text().strip()
        if not mnt:
             QMessageBox.critical(self, "Error", "Mount point is required.")
             return

        self._toggle_ui(False)
        self.status_label.setText("Performing unmount...")

        self.unmount_worker = MountWorker(None, mnt, "unmount")
        self.unmount_worker.finished.connect(lambda p: self.on_mount_action_finished("unmount", p))
        self.unmount_worker.error.connect(self.on_worker_error)
        self.unmount_worker.start()

    def on_mount_action_finished(self, action, mount_point):
        self._toggle_ui(True)
        QMessageBox.information(self, "Success", f"Successfully {action}ed at:\n{mount_point}")

    def on_worker_error(self, err_msg):
        self._toggle_ui(True)
        QMessageBox.critical(self, "Error", err_msg)


if __name__ == "__main__":
    # Standard testing block if you want to run this file directly
    import sys
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = ErofsManagerWindow()
    window.show()
    sys.exit(app.exec())
