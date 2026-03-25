#!/usr/bin/env python3
# Kazeta+ Theme Creator for KZI Generator

import os
import shutil
import toml
from PIL import Image
from pydub import AudioSegment
import pathlib

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QLineEdit, QTextEdit, QComboBox, QPushButton, QFileDialog,
    QMessageBox, QProgressDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

class ExportWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, theme_data_dict, paths_dict, output_dir):
        super().__init__()
        self.data = theme_data_dict
        self.paths = paths_dict
        self.output_dir = output_dir

    def run(self):
        try:
            theme_name_str = self.data['theme_name']
            safe_theme_name = theme_name_str.lower().replace(' ', '_')
            theme_dir = os.path.join(self.output_dir, theme_name_str)
            sfx_dir = os.path.join(theme_dir, f"{safe_theme_name}_sfx")

            self.progress.emit("Setting up theme directories...")
            os.makedirs(theme_dir, exist_ok=True)

            if self.paths['sfx_path']:
                os.makedirs(sfx_dir, exist_ok=True)
            else:
                if os.path.isdir(sfx_dir):
                    shutil.rmtree(sfx_dir)

            # Process Assets
            bgm_filename = f"{safe_theme_name}_bgm.ogg"
            if self.paths['bgm_path']:
                self.progress.emit("Converting BGM track...")
                self._convert_and_copy_audio(self.paths['bgm_path'], os.path.join(theme_dir, bgm_filename))

            logo_filename = f"{safe_theme_name}_logo.png"
            if self.paths['logo_path']:
                self.progress.emit("Converting logo image...")
                self._convert_and_copy_image(self.paths['logo_path'], os.path.join(theme_dir, logo_filename))

            bg_filename = "None"
            if self.paths['background_path']:
                source_path = self.paths['background_path']
                ext = pathlib.Path(source_path).suffix.lower()

                if ext == ".mp4":
                    bg_filename = f"{safe_theme_name}_background.mp4"
                    self.progress.emit("Copying background video...")
                    self._safe_copy(source_path, os.path.join(theme_dir, bg_filename))
                else:
                    bg_filename = f"{safe_theme_name}_background.png"
                    self.progress.emit("Converting background image...")
                    self._convert_and_copy_image(source_path, os.path.join(theme_dir, bg_filename))

            font_filename = f"{safe_theme_name}_font.ttf"
            if self.paths['font_path']:
                self.progress.emit("Copying font file...")
                self._safe_copy(self.paths['font_path'], os.path.join(theme_dir, font_filename))

            sfx_pack_name = f"{safe_theme_name}_sfx"
            if self.paths['sfx_path']:
                self.progress.emit("Processing SFX pack...")
                sfx_files = os.listdir(self.paths['sfx_path'])
                total_files = len(sfx_files)
                for i, filename in enumerate(sfx_files):
                    self.progress.emit(f"Processing SFX {i+1}/{total_files}:\n{filename}")
                    self._process_sfx_file(os.path.join(self.paths['sfx_path'], filename), sfx_dir)

            # Create theme.toml
            self.progress.emit("Writing theme.toml file...")

            # Map filenames back into the output data
            toml_output = self.data.copy()
            del toml_output['theme_name'] # Don't write this to the toml

            toml_output.update({
                'bgm_track': bgm_filename if self.paths['bgm_path'] else "None",
                'logo_selection': logo_filename if self.paths['logo_path'] else "None",
                'background_selection': bg_filename,
                'font_selection': font_filename if self.paths['font_path'] else "None",
                'sfx_pack': sfx_pack_name if self.paths['sfx_path'] else "None"
            })

            with open(os.path.join(theme_dir, 'theme.toml'), 'w') as f:
                toml.dump(toml_output, f)

            self.finished.emit(theme_dir)

        except Exception as e:
            self.error.emit(str(e))

    # Re-used helper methods inside the thread
    def _safe_copy(self, src_path, dest_path):
        if os.path.abspath(src_path) != os.path.abspath(dest_path):
            shutil.copy2(src_path, dest_path)

    def _convert_and_copy_audio(self, src_path, dest_path):
        if os.path.abspath(src_path) == os.path.abspath(dest_path): return
        if pathlib.Path(src_path).suffix.lower() == ".ogg":
            self._safe_copy(src_path, dest_path)
            return
        AudioSegment.from_file(src_path).export(dest_path, format="ogg")

    def _convert_and_copy_image(self, src_path, dest_path):
        if os.path.abspath(src_path) == os.path.abspath(dest_path): return
        if pathlib.Path(src_path).suffix.lower() == ".png":
            self._safe_copy(src_path, dest_path)
            return
        with Image.open(src_path) as img:
            img.save(dest_path, "PNG")

    def _process_sfx_file(self, src_path, dest_dir):
        p = pathlib.Path(src_path)
        if not os.path.isfile(src_path): return
        if p.suffix.lower() == ".ogg":
            dest_path = os.path.join(dest_dir, f"{p.stem}.wav")
            AudioSegment.from_ogg(src_path).export(dest_path, format="wav")
        elif p.suffix.lower() == ".wav":
            self._safe_copy(src_path, os.path.join(dest_dir, p.name))


class KazetaThemeCreator(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kazeta+ Theme Creator")
        self.resize(700, 650)
        self.setWindowModality(Qt.WindowModality.WindowModal)

        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        # We use a grid layout for the main form
        form_layout = QGridLayout()
        form_layout.setColumnStretch(1, 1) # Make entry columns expand

        positions = ["Center", "TopLeft", "TopRight", "BottomLeft", "BottomRight"]
        colors = ["WHITE", "BLACK", "PINK", "RED", "ORANGE", "YELLOW", "GREEN", "BLUE", "PURPLE"]
        speeds = ["NORMAL", "SLOW", "FAST", "OFF"]
        cursor_styles = ["BOX", "TEXT"]

        row = 0

        # Basic Info
        self.theme_name_input = self._add_form_row(form_layout, "Theme Name:", row); row += 1
        self.author_input = self._add_form_row(form_layout, "Author:", row); row += 1

        form_layout.addWidget(self._make_bold_label("Description:"), row, 0, Qt.AlignmentFlag.AlignTop)
        self.desc_input = QTextEdit()
        self.desc_input.setMaximumHeight(60)
        form_layout.addWidget(self.desc_input, row, 1, 1, 3); row += 1

        # Dropdowns
        self.menu_pos_combo = self._add_dropdown_row(form_layout, "Menu Position:", positions, row); row += 1
        self.font_color_combo = self._add_dropdown_row(form_layout, "Font Color:", colors, row); row += 1
        self.cursor_color_combo = self._add_dropdown_row(form_layout, "Cursor Color:", colors, row); row += 1
        self.bg_scroll_combo = self._add_dropdown_row(form_layout, "BG Scroll Speed:", speeds, row); row += 1
        self.color_shift_combo = self._add_dropdown_row(form_layout, "Color Shift Speed:", speeds, row); row += 1
        self.cursor_style_combo = self._add_dropdown_row(form_layout, "Cursor Style:", cursor_styles, row); row += 1
        self.cursor_blink_combo = self._add_dropdown_row(form_layout, "Cursor Blink Speed:", speeds, row); row += 1
        self.cursor_trans_combo = self._add_dropdown_row(form_layout, "Cursor Trans. Speed:", speeds, row); row += 1

        # Spacer
        form_layout.setRowMinimumHeight(row, 20); row += 1

        # File Pickers
        self.bgm_input = self._add_file_picker_row(form_layout, "BGM Track (.ogg):", "Audio Files (*.ogg *.wav *.mp3);;All files (*.*)", row); row += 1
        self.logo_input = self._add_file_picker_row(form_layout, "Logo Image (.png):", "Image Files (*.png *.jpg *.jpeg *.bmp);;All files (*.*)", row); row += 1
        self.bg_input = self._add_file_picker_row(form_layout, "Background (Img/Vid):", "Media Files (*.png *.jpg *.jpeg *.bmp *.mp4);;All files (*.*)", row); row += 1
        self.font_input = self._add_file_picker_row(form_layout, "Font File (.ttf):", "Font Files (*.ttf);;All files (*.*)", row); row += 1
        self.sfx_input = self._add_folder_picker_row(form_layout, "SFX Pack (Folder):", row); row += 1

        main_layout.addLayout(form_layout)
        main_layout.addStretch()

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_load = QPushButton("Load Theme")
        btn_load.clicked.connect(self.load_theme)

        btn_export = QPushButton("Export Theme")
        btn_export.clicked.connect(self.export_theme)

        btn_layout.addWidget(btn_load)
        btn_layout.addWidget(btn_export)
        main_layout.addLayout(btn_layout)

    def _make_bold_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("font-weight: bold;")
        return lbl

    def _add_form_row(self, layout, label_text, row):
        layout.addWidget(self._make_bold_label(label_text), row, 0)
        entry = QLineEdit()
        layout.addWidget(entry, row, 1, 1, 3)
        return entry

    def _add_dropdown_row(self, layout, label_text, options, row):
        layout.addWidget(self._make_bold_label(label_text), row, 0)
        combo = QComboBox()
        combo.addItems(options)
        layout.addWidget(combo, row, 1, 1, 3)
        return combo

    def _add_file_picker_row(self, layout, label_text, filter_str, row):
        layout.addWidget(self._make_bold_label(label_text), row, 0)
        entry = QLineEdit()
        entry.setReadOnly(True)
        layout.addWidget(entry, row, 1)

        btn_clear = QPushButton("Clear")
        btn_clear.clicked.connect(entry.clear)
        layout.addWidget(btn_clear, row, 2)

        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(lambda: self._browse_file(entry, filter_str))
        layout.addWidget(btn_browse, row, 3)
        return entry

    def _add_folder_picker_row(self, layout, label_text, row):
        layout.addWidget(self._make_bold_label(label_text), row, 0)
        entry = QLineEdit()
        entry.setReadOnly(True)
        layout.addWidget(entry, row, 1)

        btn_clear = QPushButton("Clear")
        btn_clear.clicked.connect(entry.clear)
        layout.addWidget(btn_clear, row, 2)

        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(lambda: self._browse_folder(entry))
        layout.addWidget(btn_browse, row, 3)
        return entry

    def _browse_file(self, entry_widget, filter_str):
        path, _ = QFileDialog.getOpenFileName(self, "Select File", "", filter_str)
        if path:
            entry_widget.setText(path)

    def _browse_folder(self, entry_widget):
        path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if path:
            entry_widget.setText(path)

    def _get_default_theme_dir(self):
        default_dir = os.path.expanduser('~/.local/share/kazeta-plus/themes/')
        return default_dir if os.path.isdir(default_dir) else os.path.expanduser('~')

    def load_theme(self):
        initial_dir = self._get_default_theme_dir()
        toml_path, _ = QFileDialog.getOpenFileName(
            self, "Select a theme.toml file", initial_dir, "Theme TOML (theme.toml);;All files (*.*)"
        )
        if not toml_path: return

        try:
            with open(toml_path, 'r') as f:
                data = toml.load(f)

            theme_dir = os.path.dirname(toml_path)
            theme_folder_name = os.path.basename(theme_dir)

            self.theme_name_input.setText(theme_folder_name)
            self.author_input.setText(data.get('author', ''))
            self.desc_input.setPlainText(data.get('description', ''))

            # Helper to set combobox text
            def set_combo(combo, text):
                idx = combo.findText(text)
                if idx >= 0: combo.setCurrentIndex(idx)

            set_combo(self.menu_pos_combo, data.get('menu_position', 'BottomLeft'))
            set_combo(self.font_color_combo, data.get('font_color', 'WHITE'))
            set_combo(self.cursor_color_combo, data.get('cursor_color', 'WHITE'))
            set_combo(self.bg_scroll_combo, data.get('background_scroll_speed', 'OFF'))
            set_combo(self.color_shift_combo, data.get('color_shift_speed', 'OFF'))
            set_combo(self.cursor_blink_combo, data.get('cursor_blink_speed', 'NORMAL'))
            set_combo(self.cursor_trans_combo, data.get('cursor_transition_speed', 'NORMAL'))
            set_combo(self.cursor_style_combo, data.get('cursor_style', 'BOX'))

            asset_map = {
                'bgm_track': self.bgm_input,
                'logo_selection': self.logo_input,
                'background_selection': self.bg_input,
                'font_selection': self.font_input,
                'sfx_pack': self.sfx_input
            }

            for key, widget in asset_map.items():
                asset_name = data.get(key, '')
                if asset_name and asset_name != "None":
                    full_path = os.path.join(theme_dir, asset_name)
                    widget.setText(full_path if os.path.exists(full_path) else '')
                else:
                    widget.clear()

        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load theme file: {e}")

    def export_theme(self):
        theme_name_str = self.theme_name_input.text().strip()
        author_str = self.author_input.text().strip()

        if not theme_name_str or not author_str:
            QMessageBox.critical(self, "Error", "Theme Name and Author are mandatory fields.")
            return

        initial_dir = self._get_default_theme_dir()
        output_parent_dir = QFileDialog.getExistingDirectory(self, "Select where to save the theme folder", initial_dir)
        if not output_parent_dir: return

        theme_dir = os.path.join(output_parent_dir, theme_name_str)

        if os.path.isdir(theme_dir):
            reply = QMessageBox.question(
                self, "Confirm Overwrite",
                "A theme with this name already exists.\nDo you want to overwrite it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        # Prepare data for thread
        theme_data = {
            'theme_name': theme_name_str,
            'author': author_str,
            'description': self.desc_input.toPlainText().strip(),
            'menu_position': self.menu_pos_combo.currentText(),
            'font_color': self.font_color_combo.currentText(),
            'cursor_color': self.cursor_color_combo.currentText(),
            'background_scroll_speed': self.bg_scroll_combo.currentText(),
            'color_shift_speed': self.color_shift_combo.currentText(),
            'cursor_blink_speed': self.cursor_blink_combo.currentText(),
            'cursor_transition_speed': self.cursor_trans_combo.currentText(),
            'cursor_style': self.cursor_style_combo.currentText(),
        }

        paths_data = {
            'bgm_path': self.bgm_input.text(),
            'logo_path': self.logo_input.text(),
            'background_path': self.bg_input.text(),
            'font_path': self.font_input.text(),
            'sfx_path': self.sfx_input.text()
        }

        # Setup Progress Dialog
        self.progress_dialog = QProgressDialog("Preparing to export...", None, 0, 0, self)
        self.progress_dialog.setWindowTitle("Exporting...")
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setCancelButton(None) # Can't cancel mid-conversion safely
        self.progress_dialog.show()

        # Start Worker
        self.worker = ExportWorker(theme_data, paths_data, output_parent_dir)
        self.worker.progress.connect(self.progress_dialog.setLabelText)
        self.worker.finished.connect(self.on_export_finished)
        self.worker.error.connect(self.on_export_error)
        self.worker.start()

    def on_export_finished(self, theme_dir):
        self.progress_dialog.accept()
        QMessageBox.information(self, "Success", f"Theme exported successfully to:\n{theme_dir}")

    def on_export_error(self, err_msg):
        self.progress_dialog.accept()
        QMessageBox.critical(self, "Export Failed", f"An error occurred: {err_msg}")

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = KazetaThemeCreator()
    window.show()
    sys.exit(app.exec())
