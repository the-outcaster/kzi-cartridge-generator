import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

def show_about_window():
	about_window = tk.Toplevel()
	about_window.title("About KZI Cartridge Generator")
	about_window.geometry("400x230")
	about_window.resizable(False, False)

	# Make the window modal
	about_window.transient()
	about_window.grab_set()

	about_frame = ttk.Frame(about_window, padding="15")
	about_frame.pack(expand=True, fill="both")

	about_text = (
	    "GUI for making .kzi (Kazeta information file) files that are\n"
	    "necessary for Kazeta cartridges to work.\n\n"
	    "Kazeta Cartridge Generator v1.2 by Linux Gaming Central:\n"
	    "https://github.com/the-outcaster/kzi-cartridge-generator\n\n"
	    "Copyright (C) 2025 Linux Gaming Central\n\n"
	    "Kazeta home page: https://kazeta.org/"
	)

	about_label = ttk.Label(about_frame, text=about_text, justify=tk.LEFT, font=('Helvetica', 10))
	about_label.pack(pady=(0, 15), anchor="w")

	close_button = ttk.Button(about_frame, text="Close", command=about_window.destroy)
	close_button.pack()
