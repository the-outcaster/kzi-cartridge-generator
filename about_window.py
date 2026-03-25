#!/usr/bin/env python3
# About Window for KZI File Generator

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt

version = "2.1"
copyright_year = "2026"
source_code_link = "https://github.com/the-outcaster/kzi-cartridge-generator"
kazeta_home_link = "https://kazeta.org/"
window_dimensions = (480, 300)  # Changed to a tuple for easier unpacking in PyQt
author = "Linux Gaming Central"

def show_about_window(parent=None):
    """Displays a custom 'About' modal dialog with hyperlinks."""
    # QDialog is the standard class for popup windows
    about_window = QDialog(parent)
    about_window.setWindowTitle("About Kazeta Cartridge Generator")
    about_window.setFixedSize(*window_dimensions) # Enforces exactly 480x300, replacing resizable(False, False)

    # Main vertical layout
    main_layout = QVBoxLayout(about_window)
    main_layout.setContentsMargins(15, 15, 15, 10) # Left, Top, Right, Bottom padding

    # --- Description ---
    desc_label = QLabel(
        "Swiss-army knife utility for making .kzi files, Kazeta+ themes,\n"
        "optical media discs, runtimes, and Kazeta game package (KZP) files."
    )
    main_layout.addWidget(desc_label)
    main_layout.addSpacing(10) # Spacer

    # --- Version ---
    version_label = QLabel(f"Version: {version}")
    main_layout.addWidget(version_label)
    main_layout.addSpacing(10)

    # --- Links (PyQt natively handles HTML links!) ---
    source_label = QLabel(f'Source Code: <a href="{source_code_link}">{source_code_link}</a>')
    source_label.setOpenExternalLinks(True) # Tells Qt to use the default system browser
    main_layout.addWidget(source_label)

    main_layout.addSpacing(5)

    kazeta_label = QLabel(f'Kazeta Home: <a href="{kazeta_home_link}">{kazeta_home_link}</a>')
    kazeta_label.setOpenExternalLinks(True)
    main_layout.addWidget(kazeta_label)

    # --- Copyright ---
    main_layout.addSpacing(15)
    copyright_label = QLabel(f"Copyright (C) {copyright_year} {author}")
    main_layout.addWidget(copyright_label)

    # Push all the text to the top, so the button sits cleanly at the bottom
    main_layout.addStretch()

    # --- OK Button ---
    button_layout = QHBoxLayout()
    button_layout.addStretch() # Left spacer to center the button

    ok_button = QPushButton("OK")
    ok_button.setFixedWidth(80)
    # .accept() closes a QDialog successfully
    ok_button.clicked.connect(about_window.accept)

    button_layout.addWidget(ok_button)
    button_layout.addStretch() # Right spacer to center the button

    main_layout.addLayout(button_layout)

    # .exec() blocks interactions with the main parent window until this dialog is closed
    # (This replaces transient and grab_set from Tkinter)
    about_window.exec()
