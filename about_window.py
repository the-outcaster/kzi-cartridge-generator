#!/usr/bin/env python3
# About Window for KZI File Generator

import tkinter as tk
from tkinter import ttk
import webbrowser
from tkinter import font as tkFont

version = "2.0"
copyright_year = "2025"
source_code_link = "https://github.com/the-outcaster/kzi-cartridge-generator"
kazeta_home_link = "https://kazeta.org/"
window_dimensions = "480x300"
author = "Linux Gaming Central"

def show_about_window(parent):
    """Displays a custom 'About' window with hyperlinks."""
    about_window = tk.Toplevel(parent)
    about_window.title("About Kazeta Cartridge Generator")
    about_window.geometry(window_dimensions)
    about_window.resizable(False, False)
    about_window.transient(parent)
    about_window.grab_set()

    # --- Button Frame (packed at the bottom first) ---
    button_frame = ttk.Frame(about_window, padding=(0, 10, 0, 10))
    button_frame.pack(side="bottom", fill="x")
    ok_button = ttk.Button(button_frame, text="OK", command=about_window.destroy)
    ok_button.pack() # Center the button in its frame

    # --- Main Content Frame (fills the remaining space) ---
    content_frame = ttk.Frame(about_window, padding="15")
    content_frame.pack(expand=True, fill="both", side="top")


    # Create a font for the hyperlinks
    hyperlink_font = tkFont.Font(family="Helvetica", size=10, underline=True)

    def open_url(url):
        webbrowser.open_new_tab(url)

    # --- Content Labels (placed in the content_frame) ---
    ttk.Label(content_frame, text="Swiss-army knife utility for making .kzi files, Kazeta+ themes, \noptical media discs, runtimes, and Kazeta game package (KZP) files.").pack(anchor="w")
    ttk.Label(content_frame, text="").pack() # Spacer

    ttk.Label(content_frame, text="Version: " + version).pack(anchor="w")

    # --- Source Code Link ---
    source_frame = ttk.Frame(content_frame)
    source_frame.pack(anchor="w")
    ttk.Label(source_frame, text="Source Code: ").pack(side=tk.LEFT)
    source_label = ttk.Label(source_frame, text=source_code_link, foreground="blue", cursor="hand2", font=hyperlink_font)
    source_label.pack(side=tk.LEFT)
    source_label.bind("<Button-1>", lambda e: open_url(source_code_link))

    ttk.Label(content_frame, text="").pack() # Spacer

    # --- Kazeta Home Link ---
    kazeta_frame = ttk.Frame(content_frame)
    kazeta_frame.pack(anchor="w")
    ttk.Label(kazeta_frame, text="Kazeta Home: ").pack(side=tk.LEFT)
    kazeta_label = ttk.Label(kazeta_frame, text=kazeta_home_link, foreground="blue", cursor="hand2", font=hyperlink_font)
    kazeta_label.pack(side=tk.LEFT)
    kazeta_label.bind("<Button-1>", lambda e: open_url(kazeta_home_link))

    ttk.Label(content_frame, text="Copyright (C) " + copyright_year + " " + author).pack(anchor="w", pady=(10, 10))

    parent.eval(f'tk::PlaceWindow {str(about_window)} center')
