#!/usr/bin/env python3
# ISO Creator and Burner for KZI File Generator

import glob
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import subprocess
import threading
import shutil
import time
import wave

class IsoBurnerWindow:
    def __init__(self, parent):
        self.parent = parent

        self.window = tk.Toplevel(parent)
        self.window.title("Create & Burn Disc (Data or Audio)") # Updated Title
        self.window.geometry("650x600") # Increased height for tabs
        self.window.transient(parent)
        self.window.grab_set()

        # Data Variables
        self.source_folder_var = tk.StringVar()
        self.iso_path_var = tk.StringVar()

        # Audio Variables
        self.audio_tracks = [] # List to store paths of .wav files

        # Shared Variables
        self.selected_drive_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")

        self.create_widgets()
        self.scan_optical_drives()

    def create_widgets(self):
        main_frame = ttk.Frame(self.window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Global: Drive Selection ---
        drive_frame = ttk.LabelFrame(main_frame, text="Target Optical Drive", padding=10)
        drive_frame.pack(fill=tk.X, pady=(0, 10))

        self.drive_combo = ttk.Combobox(drive_frame, textvariable=self.selected_drive_var, state="readonly")
        self.drive_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(drive_frame, text="Refresh", command=self.scan_optical_drives).pack(side=tk.LEFT)

        # --- Tabs ---
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=5)

        # Tab 1: Data / Game ISO
        self.tab_data = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_data, text="Data / Game ISO")
        self.setup_data_tab()

        # Tab 2: Audio CD
        self.tab_audio = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_audio, text="Audio CD")
        self.setup_audio_tab()

        # --- Global: Status ---
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(10, 0), side=tk.BOTTOM)

        ttk.Label(status_frame, textvariable=self.status_var).pack(anchor="w")
        self.progress = ttk.Progressbar(status_frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill=tk.X, pady=(5, 0))

    def setup_data_tab(self):
        # --- Section 1: Source ---
        source_frame = ttk.LabelFrame(self.tab_data, text="1. Source Selection", padding=10)
        source_frame.pack(fill=tk.X, pady=5)

        ttk.Label(source_frame, text="Game Folder:").grid(row=0, column=0, sticky="w")
        ttk.Entry(source_frame, textvariable=self.source_folder_var).grid(row=0, column=1, sticky="ew", padx=5)
        ttk.Button(source_frame, text="Browse...", command=self.browse_source_folder).grid(row=0, column=2)

        source_frame.columnconfigure(1, weight=1)
        ttk.Button(source_frame, text="Create ISO from Folder", command=self.start_create_iso).grid(row=2, column=1, pady=10, sticky="ew")

        # --- Section 2: Burn ---
        iso_frame = ttk.LabelFrame(self.tab_data, text="2. Burn ISO Image", padding=10)
        iso_frame.pack(fill=tk.X, pady=10)

        ttk.Label(iso_frame, text="ISO File:").grid(row=0, column=0, sticky="w")
        ttk.Entry(iso_frame, textvariable=self.iso_path_var).grid(row=0, column=1, sticky="ew", padx=5)
        ttk.Button(iso_frame, text="Browse...", command=self.browse_iso_file).grid(row=0, column=2)

        iso_frame.columnconfigure(1, weight=1)
        self.burn_iso_button = ttk.Button(iso_frame, text="Burn ISO to Disc", command=self.start_burn_iso)
        self.burn_iso_button.grid(row=1, column=1, pady=(10, 0), sticky="ew")

    def setup_audio_tab(self):
        info_lbl = ttk.Label(self.tab_audio, text="Add WAV files (16-bit, 44.1kHz). Track order matters.", foreground="gray")
        info_lbl.pack(anchor="w", pady=(0, 5))

        # Listbox with scrollbar
        list_frame = ttk.Frame(self.tab_audio)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.track_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED)
        self.track_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.track_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.track_listbox.config(yscrollcommand=scrollbar.set)

        # Stats Label
        self.audio_stats_var = tk.StringVar(value="Total Time: 00:00 | Total Size: 0 MB")
        stats_lbl = ttk.Label(self.tab_audio, textvariable=self.audio_stats_var, font=("", 9, "bold"))
        stats_lbl.pack(anchor="w", pady=(5, 5))

        # Toolbar
        btn_frame = ttk.Frame(self.tab_audio)
        btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(btn_frame, text="Add Files...", command=self.add_audio_files).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Remove", command=self.remove_audio_track).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Clear All", command=self.clear_audio_tracks).pack(side=tk.LEFT, padx=2)

        ttk.Frame(btn_frame).pack(side=tk.LEFT, fill=tk.X, expand=True) # Spacer

        ttk.Button(btn_frame, text="Move Up", command=lambda: self.move_track(-1)).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Move Down", command=lambda: self.move_track(1)).pack(side=tk.LEFT, padx=2)

        self.burn_audio_button = ttk.Button(self.tab_audio, text="Burn Audio CD", command=self.start_burn_audio)
        self.burn_audio_button.pack(fill=tk.X, pady=10)

    def add_audio_files(self):
        files = filedialog.askopenfilenames(
            title="Select Audio Tracks",
            filetypes=[("WAV Files", "*.wav")]
        )
        if files:
            for f in files:
                self.audio_tracks.append(f)
                display_text = self._get_track_display_text(f)
                self.track_listbox.insert(tk.END, display_text)
            self.update_audio_stats()

    def _get_track_display_text(self, path):
        """Helper to format listbox entry: Filename [MM:SS]"""
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
            pass # Keep default if unreadable

        return f"{filename}   [{duration_str}]"

    def remove_audio_track(self):
        # curselection returns a tuple of indices, e.g., (0, 2, 3)
        selection = self.track_listbox.curselection()

        if not selection:
            return

        # CRITICAL: Delete from the end of the list backwards.
        # If we delete index 0, index 1 shifts down to 0, breaking subsequent deletes.
        # sorted(..., reverse=True) ensures we safely delete from bottom up.
        for index in sorted(selection, reverse=True):
            self.track_listbox.delete(index)
            del self.audio_tracks[index]

        self.update_audio_stats()

    def clear_audio_tracks(self):
        self.track_listbox.delete(0, tk.END)
        self.audio_tracks = []
        self.update_audio_stats()

    def move_track(self, direction):
        sel = self.track_listbox.curselection()
        if not sel: return
        idx = sel[0]
        new_idx = idx + direction

        if 0 <= new_idx < len(self.audio_tracks):
            # Swap in list
            self.audio_tracks[idx], self.audio_tracks[new_idx] = self.audio_tracks[new_idx], self.audio_tracks[idx]
            # Update UI
            self.track_listbox.delete(idx)
            display_text = self._get_track_display_text(self.audio_tracks[new_idx])
            self.track_listbox.insert(new_idx, display_text)
            self.track_listbox.select_set(new_idx)

    def update_audio_stats(self):
        total_seconds = 0.0
        total_size_bytes = 0

        for track_path in self.audio_tracks:
            try:
                # Calculate Size
                total_size_bytes += os.path.getsize(track_path)

                # Calculate Duration
                with wave.open(track_path, 'r') as wav:
                    frames = wav.getnframes()
                    rate = wav.getframerate()
                    duration = frames / float(rate)
                    total_seconds += duration
            except Exception:
                pass # Skip bad files

        # Format Time (MM:SS)
        mins = int(total_seconds // 60)
        secs = int(total_seconds % 60)

        # Format Size (MB)
        size_mb = total_size_bytes / (1024 * 1024)

        # Capacity Check (80 min standard CD)
        color = "black"
        if mins >= 80:
            color = "red" # Warn user if over capacity

        status_text = f"Total Time: {mins:02d}:{secs:02d} | Total Size: {size_mb:.2f} MB"
        self.audio_stats_var.set(status_text)

    def start_burn_audio(self):
        drive = self.selected_drive_var.get()
        if not drive or "/dev/" not in drive:
            messagebox.showerror("Error", "Please select a valid optical drive.")
            return

        if not self.audio_tracks:
            messagebox.showerror("Error", "Please add at least one .wav file.")
            return

        if messagebox.askyesno("Confirm Audio Burn", f"Burn {len(self.audio_tracks)} tracks to {drive}?\nEnsure files are 16-bit 44.1kHz WAVs."):
            # We pass a COPY of the list so modifications during burn don't crash it
            threading.Thread(target=self._burn_audio_worker, args=(list(self.audio_tracks), drive), daemon=True).start()

    def scan_optical_drives(self):
        """Scans for optical drives using wodim --devices."""
        drives = []
        try:
            # 'wodim --devices' usually lists available drives
            result = subprocess.run(['wodim', '--devices'], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                # Example output: '/dev/sr0' ...
                if '/dev/' in line:
                    parts = line.split()
                    for part in parts:
                        if part.startswith('/dev/'):
                            # Strip quotes if present
                            drive = part.strip("'")
                            drives.append(drive)
                            break
        except FileNotFoundError:
             messagebox.showerror("Missing Dependency", "The tool 'wodim' is required to detect drives and burn discs.\nPlease install it (e.g., 'sudo dnf install wodim').")

        # Fallback if wodim fails or finds nothing (e.g. no perms), try listing /dev/sr*
        if not drives:
            import glob
            drives = glob.glob('/dev/sr*')

        self.drive_combo['values'] = drives
        if drives:
            self.drive_combo.current(0)
        else:
            self.selected_drive_var.set("No drives found")

    def browse_source_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.source_folder_var.set(path)

    def browse_iso_file(self):
        path = filedialog.askopenfilename(filetypes=[("ISO Image", "*.iso"), ("All files", "*.*")])
        if path:
            self.iso_path_var.set(path)

    def start_create_iso(self):
        source = self.source_folder_var.get()

        if not source or not os.path.isdir(source):
            messagebox.showerror("Error", "Please select a valid source folder first.")
            return

        # Check for .kzi file inside the folder
        kzi_files = glob.glob(os.path.join(source, "*.kzi"))

        if not kzi_files:
            messagebox.showerror("Error", "No .kzi file found in the selected folder.\nPlease ensure the game folder contains a valid Kazeta cartridge definition.")
            return

        # Use the name of the found .kzi file to guess the ISO name
        kzi_basename = os.path.splitext(os.path.basename(kzi_files[0]))[0]
        default_name = f"{kzi_basename}.iso"

        save_path = filedialog.asksaveasfilename(
            title="Save ISO As...",
            initialfile=default_name,
            defaultextension=".iso",
            filetypes=[("ISO Image", "*.iso")]
        )
        if not save_path:
            return

        # Pass only source and save_path. We don't need to pass the kzi path
        # because it's already in the folder.
        threading.Thread(target=self._create_iso_worker, args=(source, save_path), daemon=True).start()

    def _burn_audio_worker(self, track_list, drive):
        self.window.after(0, lambda: self._toggle_ui(False))
        self.status_var.set("Waiting for authentication...")
        self.progress['mode'] = 'indeterminate'
        self.progress.start(10)

        try:
            wodim_path = shutil.which('wodim')
            if not wodim_path:
                 raise Exception("wodim not found.")

            # Command for Audio CD
            # -audio: Tells wodim these are audio tracks
            # -pad: Adds silence if tracks aren't perfect sector multiples (prevents errors)
            cmd = ['pkexec', wodim_path, '-v', '-eject', '-dao', '-audio', '-pad', f'dev={drive}']

            # Append all track paths to the command
            cmd.extend(track_list)

            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

            self.window.after(0, lambda: self.status_var.set("Burning Audio CD..."))

            output_log = []
            for line in process.stdout:
                output_log.append(line)
                if "written" in line and "%" in line:
                    try:
                         clean_line = line.strip()
                         self.window.after(0, lambda l=clean_line: self.status_var.set(l))
                    except:
                        pass

            process.wait()

            if process.returncode == 0:
                self.window.after(0, lambda: messagebox.showinfo("Success", "Audio CD created successfully!"))
            else:
                if process.returncode in [126, 127]:
                     self.window.after(0, lambda: messagebox.showerror("Error", "Authentication failed or cancelled."))
                else:
                     error_details = "".join(output_log[-15:])
                     self.window.after(0, lambda: messagebox.showerror("Error", f"Burning failed.\n\nDetails:\n{error_details}"))

        except Exception as e:
            self.window.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.window.after(0, lambda: self._toggle_ui(True))
            self.window.after(0, self.progress.stop)
            self.window.after(0, lambda: self.status_var.set("Ready"))

    def _create_iso_worker(self, source, save_path):
        self.window.after(0, lambda: self._toggle_ui(False))
        self.status_var.set(f"Generating ISO: {os.path.basename(save_path)}...")
        self.progress['mode'] = 'indeterminate'
        self.progress.start(10)

        try:
            # Run genisoimage directly on the source folder
            cmd = ['genisoimage', '-o', save_path, '-J', '-R', source]
            process = subprocess.run(cmd, capture_output=True, text=True)

            if process.returncode != 0:
                raise Exception(f"genisoimage failed:\n{process.stderr}")

            self.window.after(0, lambda: self.iso_path_var.set(save_path))
            self.window.after(0, lambda: messagebox.showinfo("Success", "ISO created successfully!"))

        except Exception as e:
            err_msg = str(e) # Capture string immediately
            self.window.after(0, lambda: messagebox.showerror("Error", err_msg))
        finally:
            self.window.after(0, lambda: self._toggle_ui(True))
            self.window.after(0, self.progress.stop)
            self.window.after(0, lambda: self.status_var.set("Ready"))

    def start_burn_iso(self):
        iso_file = self.iso_path_var.get()
        drive = self.selected_drive_var.get()

        if not iso_file or not os.path.exists(iso_file):
            messagebox.showerror("Error", "Please select a valid ISO file.")
            return
        if not drive or "/dev/" not in drive:
            messagebox.showerror("Error", "Please select a valid optical drive.")
            return

        if messagebox.askyesno("Confirm Burn", f"Are you sure you want to burn '{os.path.basename(iso_file)}' to {drive}?\nThis will erase any re-writable data on the disc."):
            threading.Thread(target=self._burn_iso_worker, args=(iso_file, drive), daemon=True).start()

    def _burn_iso_worker(self, iso_file, drive):
        self.window.after(0, lambda: self._toggle_ui(False))
        self.status_var.set("Waiting for authentication...") # Update status to let user know
        self.progress['mode'] = 'indeterminate'
        self.progress.start(10)

        try:
            # Locate wodim executable
            wodim_path = shutil.which('wodim')
            if not wodim_path:
                 raise Exception("wodim not found. Please install 'cdrkit' or 'wodim'.")

            # construct command with pkexec to request admin permissions
            # pkexec will trigger a GUI password prompt
            cmd = ['pkexec', wodim_path, '-v', '-eject', '-dao', f'dev={drive}', iso_file]

            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

            # Once the process starts, update status
            self.window.after(0, lambda: self.status_var.set("Burning to disc (this may take a while)..."))

            output_log = []

            for line in process.stdout:
                output_log.append(line)
                if "written" in line and "%" in line:
                    try:
                         clean_line = line.strip()
                         self.window.after(0, lambda l=clean_line: self.status_var.set(l))
                    except:
                        pass

            process.wait()

            if process.returncode == 0:
                self.window.after(0, lambda: messagebox.showinfo("Success", "Burning complete! Disc ejected."))
            else:
                # Filter out lines that might just be pkexec noise if user cancelled
                if process.returncode == 126 or process.returncode == 127:
                     self.window.after(0, lambda: messagebox.showerror("Error", "Authentication failed or cancelled."))
                else:
                     error_details = "".join(output_log[-15:])
                     self.window.after(0, lambda: messagebox.showerror("Error", f"Burning process returned an error code.\n\nDetails:\n{error_details}"))

        except Exception as e:
            self.window.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.window.after(0, lambda: self._toggle_ui(True))
            self.window.after(0, self.progress.stop)
            self.window.after(0, lambda: self.status_var.set("Ready"))

    def _toggle_ui(self, enable):
        state = tk.NORMAL if enable else tk.DISABLED
        self.burn_iso_button.config(state=state)
        self.burn_audio_button.config(state=state)
        # Optional: Disable notebook tabs to prevent switching during burn
        self.notebook.state(['!disabled'] if enable else ['disabled'])
