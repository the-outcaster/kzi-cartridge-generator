#!/usr/bin/env python3
# EROFS Manager for KZI Generator
# Handles packing .kzr/.kzp files and mounting images

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import subprocess
import threading
import shutil
import glob
import time

class ErofsManagerWindow:
    def __init__(self, parent):
        self.parent = parent

        self.window = tk.Toplevel(parent)
        self.window.title("Kazeta Package Manager (EROFS)")
        self.window.geometry("600x550")
        self.window.transient(parent)
        self.window.grab_set()

        # Variables
        self.source_folder_var = tk.StringVar()
        self.image_type_var = tk.StringVar(value="kzr") # kzr or kzp

        self.comp_algo_var = tk.StringVar(value="lz4")

        self.mount_image_path_var = tk.StringVar()
        self.mount_point_var = tk.StringVar(value=os.path.expanduser("~/mnt"))

        self.status_var = tk.StringVar(value="Ready")

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=5)

        # --- Tab 1: Create Package ---
        self.tab_create = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_create, text="Create Package (.kzr/.kzp)")
        self.setup_create_tab()

        # --- Tab 2: Mount Image ---
        self.tab_mount = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_mount, text="Mount Image")
        self.setup_mount_tab()

        # Status Bar
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(10, 0), side=tk.BOTTOM)
        ttk.Label(status_frame, textvariable=self.status_var).pack(anchor="w")
        self.progress = ttk.Progressbar(status_frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill=tk.X, pady=(5, 0))

    def setup_create_tab(self):
        # Source
        src_frame = ttk.LabelFrame(self.tab_create, text="1. Source Folder", padding=10)
        src_frame.pack(fill=tk.X, pady=5)

        ttk.Entry(src_frame, textvariable=self.source_folder_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(src_frame, text="Browse...", command=self.browse_source).pack(side=tk.LEFT)

        # Type Selection
        type_frame = ttk.LabelFrame(self.tab_create, text="2. Package Type", padding=10)
        type_frame.pack(fill=tk.X, pady=5)

        ttk.Radiobutton(type_frame, text="Kazeta Runtime (.kzr)", variable=self.image_type_var, value="kzr").pack(anchor="w")
        ttk.Radiobutton(type_frame, text="Kazeta Game Package (.kzp) - Must contain .kzi file", variable=self.image_type_var, value="kzp").pack(anchor="w")

        # Compression Options
        comp_frame = ttk.LabelFrame(self.tab_create, text="3. Compression Settings", padding=10)
        comp_frame.pack(fill=tk.X, pady=5)

        ttk.Label(comp_frame, text="Algorithm:").grid(row=0, column=0, sticky="w", padx=5)
        algos = ['lz4', 'lz4hc', 'lzma', 'deflate', 'libdeflate', 'zstd', 'uncompressed']
        ttk.OptionMenu(comp_frame, self.comp_algo_var, algos[0], *algos).grid(row=0, column=1, sticky="w", padx=5)

        # Action
        self.create_btn = ttk.Button(self.tab_create, text="Create EROFS Image", command=self.start_creation)
        self.create_btn.pack(fill=tk.X, pady=15)

    def setup_mount_tab(self):
        # Image Input
        img_frame = ttk.LabelFrame(self.tab_mount, text="Image File", padding=10)
        img_frame.pack(fill=tk.X, pady=5)
        ttk.Entry(img_frame, textvariable=self.mount_image_path_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(img_frame, text="Browse...", command=self.browse_image_to_mount).pack(side=tk.LEFT)

        # Mount Point
        mnt_frame = ttk.LabelFrame(self.tab_mount, text="Mount Point", padding=10)
        mnt_frame.pack(fill=tk.X, pady=5)

        # Sub-frame to hold Entry and Button on the same row
        row_frame = ttk.Frame(mnt_frame)
        row_frame.pack(fill=tk.X)

        ttk.Entry(row_frame, textvariable=self.mount_point_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(row_frame, text="Browse...", command=self.browse_mount_point).pack(side=tk.LEFT)

        ttk.Label(mnt_frame, text="Note: Uses FUSE. No sudo required.", font=("", 8), foreground="green").pack(anchor="w", pady=(5,0))

        # Buttons
        btn_frame = ttk.Frame(self.tab_mount)
        btn_frame.pack(fill=tk.X, pady=15)

        self.mount_btn = ttk.Button(btn_frame, text="Mount Image", command=self.start_mount)
        self.mount_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.unmount_btn = ttk.Button(btn_frame, text="Unmount Path", command=self.start_unmount)
        self.unmount_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

    # --- Helpers ---
    def browse_source(self):
        path = filedialog.askdirectory()
        if path: self.source_folder_var.set(path)

    def browse_image_to_mount(self):
        path = filedialog.askopenfilename(filetypes=[("EROFS Images", "*.kzr *.kzp *.img"), ("All files", "*.*")])
        if path: self.mount_image_path_var.set(path)

    def browse_mount_point(self):
        path = filedialog.askdirectory(title="Select Mount Point Directory")
        if path:
            self.mount_point_var.set(path)

    def _toggle_ui(self, enable):
        state = tk.NORMAL if enable else tk.DISABLED
        self.create_btn.config(state=state)
        self.mount_btn.config(state=state)
        self.unmount_btn.config(state=state)

    # --- Logic: Create ---
    def start_creation(self):
        source = self.source_folder_var.get()
        pkg_type = self.image_type_var.get()

        if not source or not os.path.isdir(source):
            messagebox.showerror("Error", "Invalid source folder.")
            return

        # Validation for .kzp
        if pkg_type == "kzp":
            kzi_files = glob.glob(os.path.join(source, "*.kzi"))
            if not kzi_files:
                messagebox.showerror("Error", "Selected folder must contain a .kzi file for .kzp packages.")
                return

        # Save Dialog
        ext = f".{pkg_type}"
        default_name = f"package{ext}"
        if pkg_type == "kzp" and kzi_files:
            default_name = os.path.basename(kzi_files[0]).replace(".kzi", ext)

        save_path = filedialog.asksaveasfilename(
            title=f"Save {pkg_type.upper()} File",
            initialfile=default_name,
            defaultextension=ext,
            filetypes=[(f"{pkg_type.upper()} Image", f"*{ext}")]
        )
        if not save_path: return

        threading.Thread(target=self._creation_worker, args=(source, save_path), daemon=True).start()

    def _creation_worker(self, source, save_path):
        self._toggle_ui(False)
        self.status_var.set("Packing EROFS image...")
        self.progress['mode'] = 'indeterminate'
        self.progress.start(10)

        try:
            mkfs = shutil.which("mkfs.erofs")
            if not mkfs:
                raise Exception("mkfs.erofs not found. Please install erofs-utils.")

            algo = self.comp_algo_var.get()
            # Hardcoded default for algorithms that support levels
            default_level = "9"

            cmd = [mkfs]

            if algo == "uncompressed":
                pass
            elif algo in ["lz4", "lzma"]:
                # These do not accept a level argument
                cmd.append(f"-z{algo}")
            else:
                # lz4hc, deflate, etc. accept a level. We use 9 by default.
                cmd.append(f"-z{algo},{default_level}")

            cmd.extend([save_path, source])

            process = subprocess.run(cmd, capture_output=True, text=True)

            if process.returncode != 0:
                raise Exception(f"mkfs.erofs failed:\n{process.stderr}")

            self.window.after(0, lambda: messagebox.showinfo("Success", f"Created {os.path.basename(save_path)}"))

        except Exception as e:
            err_msg = str(e)
            self.window.after(0, lambda: messagebox.showerror("Error", err_msg))
        finally:
            self.window.after(0, lambda: self._toggle_ui(True))
            self.window.after(0, self.progress.stop)
            self.window.after(0, lambda: self.status_var.set("Ready"))

    # --- Logic: Mount/Unmount ---
    def start_mount(self):
        img = self.mount_image_path_var.get()
        mnt = self.mount_point_var.get()

        if not img or not os.path.exists(img):
            messagebox.showerror("Error", "Invalid image file.")
            return
        if not mnt:
            messagebox.showerror("Error", "Mount point is required.")
            return

        threading.Thread(target=self._mount_worker, args=(img, mnt, "mount"), daemon=True).start()

    def start_unmount(self):
        mnt = self.mount_point_var.get()
        if not mnt:
             messagebox.showerror("Error", "Mount point is required.")
             return
        threading.Thread(target=self._mount_worker, args=(None, mnt, "unmount"), daemon=True).start()

    def _mount_worker(self, img_path, mount_point, action):
        self._toggle_ui(False)
        self.status_var.set(f"Performing {action}...")
        self.progress.start(10)

        try:
            # FIX 1: Expand ~ and resolve absolute path
            # This prevents creating a folder named "~" or relative path confusion
            mount_point = os.path.abspath(os.path.expanduser(mount_point))
            img_path = os.path.abspath(os.path.expanduser(img_path)) if img_path else None

            if action == "mount":
                erofsfuse = shutil.which("erofsfuse")
                if not erofsfuse:
                    raise Exception("erofsfuse not found. Please install 'erofs-utils' or 'erofsfuse'.")

                if not os.path.exists(mount_point):
                    os.makedirs(mount_point, exist_ok=True)

                # Check if non-empty (just a warning)
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
                raise Exception(f"{action} failed:\n{process.stderr}")

            # FIX 2: Verification Step
            # erofsfuse daemonizes (exits successfully), but might crash immediately in background.
            # We wait a moment and check if the path is actually a mount point.
            if action == "mount":
                time.sleep(0.5) # Give the filesystem a moment to initialize
                if not os.path.ismount(mount_point):
                    # Try to read stderr from a failed daemon if possible, or just generic error
                    raise Exception("Mount command finished, but the folder is not mounted.\nThe background process likely crashed (check permissions or FUSE version).")

            self.window.after(0, lambda: messagebox.showinfo("Success", f"Successfully {action}ed at:\n{mount_point}"))

        except Exception as e:
            err_msg = str(e)
            self.window.after(0, lambda: messagebox.showerror("Error", err_msg))
        finally:
            self.window.after(0, lambda: self._toggle_ui(True))
            self.window.after(0, self.progress.stop)
            self.window.after(0, lambda: self.status_var.set("Ready"))
