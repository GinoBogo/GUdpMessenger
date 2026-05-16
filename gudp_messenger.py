#!/usr/bin/env python3

# A simple UDP Hexadecimal Messenger Application
# by Gino Bogo

import json
import os
import platform
import re
import socket
import threading

import tkinter as tk
import tkinter.filedialog as tkFileDialog
import tkinter.font as tkfont

from datetime import datetime
from tkinter import ttk, scrolledtext, messagebox


class GUdpMessenger:
    def __init__(self, root):
        self.root = root
        self.root.title("gUDP Messenger")
        self.root.geometry("984x680")
        self.root.minsize(984, 680)
        self.root.resizable(True, True)

        # Dark theme colors
        self.colors = {
            "bg_dark": "#0a0a0f",  # Black
            "bg_panel": "#0d1117",  # Dark Gray
            "bg_input": "#161b22",  # Darker Gray
            "border": "#30363d",  # Dark Blue
            "text": "#c9d1d9",  # Light Gray
            "text_dim": "#8b949e",  # Dimmed Text
            "accent": "#00ff41",  # Bright Green
            "accent_cyan": "#58a6ff",  # Terminal Cyan
            "accent_orange": "#f0883e",  # Warning Orange
            "accent_red": "#f85149",  # Error Red
            "accent_yellow": "#e3b341",  # Yellow
            "terminal_green": "#00cc33",  # Terminal Green
            "sb_thumb": "#30363d",  # Dark Blue (draggable thumb)
            "sb_trough": "#0a0a0f",  # Black (groove - matches bg_dark)
            "sb_active": "#70767d",  # Lighter Dark Blue (thumb on hover)
        }

        # Select best available monospace font
        self.fonts = self._get_system_fonts()

        # Configure ttk styles
        self._setup_styles()

        # UDP socket state
        self.sock = None
        self.is_listening = False
        self.listen_thread = None

        # Build UI
        self._create_widgets()

        # Style scrollbars after widgets exist
        self._style_scrollbars()

        # Restore saved settings
        self.load_config()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    # ------------------------------------------------------------------
    # Font detection
    # ------------------------------------------------------------------

    def _get_system_fonts(self):
        """Return a dict with font candidates and sizes for the current OS."""
        system = platform.system()

        if system == "Linux":
            candidates = (
                "JetBrains Mono",
                "Fira Code",
                "FiraCode Nerd Font",
                "Cascadia Code",
                "DejaVu Sans Mono",
                "Ubuntu Mono",
                "Liberation Mono",
                "Noto Mono",
                "Courier New",
            )
        elif system == "Darwin":
            candidates = (
                "SF Mono",
                "Menlo",
                "Monaco",
                "JetBrains Mono",
                "Fira Code",
                "Courier New",
            )
        else:  # Windows and others
            candidates = ("Cascadia Code", "Consolas", "Courier New")

        available = tkfont.families()
        selected = next((f for f in candidates if f in available), "Courier New")

        return {
            "selected": selected,
            "size_normal": 10,
            "size_small": 9,
            "size_large": 10,
        }

    # ------------------------------------------------------------------
    # Style setup
    # ------------------------------------------------------------------

    def _setup_styles(self):
        """Configure ttk styles for the dark industrial look."""
        style = ttk.Style()
        style.theme_use("clam")

        sel = self.fonts["selected"]
        self.main_font = (sel, self.fonts["size_normal"])
        self.small_font = (sel, self.fonts["size_small"])
        self.large_font = (sel, self.fonts["size_large"])
        self.bold_font = (sel, self.fonts["size_large"], "bold")

        c = self.colors

        style.configure("Dark.TFrame", background=c["bg_dark"])
        style.configure(
            "Dark.TLabelframe",
            background=c["bg_dark"],
            foreground=c["accent"],
            borderwidth=1,
            relief="solid",
        )
        style.configure(
            "Dark.TLabelframe.Label",
            background=c["bg_dark"],
            foreground=c["accent"],
            font=self.bold_font,
        )
        style.configure(
            "Dark.TButton",
            background=c["bg_input"],
            foreground=c["accent"],
            borderwidth=1,
            relief="solid",
            font=self.small_font,
            padding=(10, 5),
        )
        style.map(
            "Dark.TButton",
            background=[("active", "#1a3320"), ("pressed", "#0d2818")],
            foreground=[("active", "#00ff41"), ("pressed", "#00dd33")],
            borderwidth=[("active", 1)],
            relief=[("pressed", "sunken")],
        )
        style.configure(
            "Dark.TLabel",
            background=c["bg_dark"],
            foreground=c["text"],
            font=self.small_font,
        )
        style.configure(
            "Dark.TCheckbutton",
            background=c["bg_dark"],
            foreground=c["text_dim"],
            font=self.small_font,
        )
        style.map(
            "Dark.TCheckbutton",
            background=[("active", c["bg_dark"])],
            foreground=[("active", c["accent"])],
        )

        self.root.configure(bg=c["bg_dark"])

    # ------------------------------------------------------------------
    # Widget helpers
    # ------------------------------------------------------------------

    def _create_entry(self, parent, width, initial_value=""):
        """Return a styled tk.Entry with centred cyan text."""
        c = self.colors
        entry = tk.Entry(
            parent,
            width=width,
            justify="center",
            font=self.small_font,
            bg=c["bg_input"],
            fg=c["accent_cyan"],
            insertbackground=c["accent_yellow"],
            relief="flat",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground=c["border"],
            highlightcolor=c["accent"],
            selectbackground="#3a2a1a",
            selectforeground=c["accent_yellow"],
        )
        if initial_value:
            entry.insert(0, initial_value)
        return entry

    def _make_scrolled_text(self, parent, height, fg_color):
        """Return a styled ScrolledText widget."""
        c = self.colors
        widget = scrolledtext.ScrolledText(
            parent,
            height=height,
            wrap=tk.WORD,
            font=self.main_font,
            bg=c["bg_input"],
            fg=fg_color,
            insertbackground=fg_color,
            relief="flat",
            borderwidth=1,
            highlightthickness=0,
        )
        return widget

    def _style_scrollbars(self):
        """Apply near-black colours to every ScrolledText vertical scrollbar."""
        c = self.colors
        sb_cfg = dict(
            bg=c["sb_thumb"],
            troughcolor=c["sb_trough"],
            activebackground=c["sb_active"],
            relief="flat",
            bd="0",
            width="10",
        )
        for widget in (self.send_text, self.recv_text, self.sys_log):
            widget.vbar.config(**sb_cfg)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _create_widgets(self):
        self.root.grid_rowconfigure(2, weight=1)
        self.root.grid_rowconfigure(3, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        self._create_settings_frame()
        self._create_control_bar()
        self._create_transmit_frame()
        self._create_receive_frame()
        self._create_log_frame()
        self._apply_hand_cursor()

    def _create_settings_frame(self):
        frame = ttk.LabelFrame(
            self.root,
            text="[ CONNECTION SETTINGS ]",
            padding="10",
            style="Dark.TLabelframe",
        )
        frame.grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="ew")

        # Local IP
        ttk.Label(frame, text="Local IP:", style="Dark.TLabel").grid(
            row=0, column=0, sticky="w", padx=(0, 5)
        )
        self.local_ip = self._create_entry(frame, width=16, initial_value="0.0.0.0")
        self.local_ip.grid(row=0, column=1, padx=(0, 10))

        # Local Port
        ttk.Label(frame, text="Local Port:", style="Dark.TLabel").grid(
            row=0, column=2, sticky="w", padx=(0, 5)
        )
        self.local_port = self._create_entry(frame, width=9, initial_value="8888")
        self.local_port.grid(row=0, column=3, padx=(0, 20))

        # Remote IP
        ttk.Label(frame, text="Remote IP:", style="Dark.TLabel").grid(
            row=0, column=4, sticky="w", padx=(0, 5)
        )
        self.remote_ip = self._create_entry(frame, width=16, initial_value="127.0.0.1")
        self.remote_ip.grid(row=0, column=5, padx=(0, 10))

        # Remote Port
        ttk.Label(frame, text="Remote Port:", style="Dark.TLabel").grid(
            row=0, column=6, sticky="w", padx=(0, 5)
        )
        self.remote_port = self._create_entry(frame, width=9, initial_value="9999")
        self.remote_port.grid(row=0, column=7)

    def _create_control_bar(self):
        c = self.colors
        bar = ttk.Frame(self.root, style="Dark.TFrame")
        bar.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        w = 13  # primary button width

        self.bind_button = ttk.Button(
            bar,
            text="[ START ]",
            command=self.toggle_listening,
            width=w,
            style="Dark.TButton",
        )
        self.bind_button.pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            bar,
            text="[ CLEAR TX ]",
            command=self.clear_send,
            width=w,
            style="Dark.TButton",
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            bar,
            text="[ CLEAR RX ]",
            command=self.clear_received,
            width=w,
            style="Dark.TButton",
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            bar,
            text="[ CLEAR LOG ]",
            command=self.clear_sys_log,
            width=w,
            style="Dark.TButton",
        ).pack(side=tk.LEFT, padx=(0, 5))

        self.status_label = tk.Label(
            bar,
            text="● DISCONNECTED",
            fg=c["accent_red"],
            bg=c["bg_dark"],
            font=self.bold_font,
        )
        self.status_label.pack(side=tk.RIGHT)

    def _create_transmit_frame(self):
        c = self.colors
        frame = ttk.LabelFrame(
            self.root, text="[ TRANSMIT ]", padding="10", style="Dark.TLabelframe"
        )
        frame.grid(row=2, column=0, padx=(10, 5), pady=5, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        self.send_text = self._make_scrolled_text(frame, height=8, fg_color=c["accent"])
        self.send_text.config(
            selectbackground="#1a3a2a",
            selectforeground=c["accent"],
        )
        self.send_text.grid(row=0, column=0, sticky="nsew", pady=(0, 5))

        # Context menu (right-click)
        self.file_menu = tk.Menu(self.root, tearoff=0)
        self.file_menu.add_command(label="Open File", command=self.load_task_file)
        self.file_menu.add_command(label="Save File", command=self.save_task_file)
        self.send_text.bind("<Button-3>", self._show_context_menu)
        self.send_text.bind("<Escape>", self.file_menu.grab_release())

        # Button row
        btn_frame = ttk.Frame(frame, style="Dark.TFrame")
        btn_frame.grid(row=1, column=0, sticky="ew")

        w = 12  # secondary button width

        ttk.Button(
            btn_frame,
            text="[ SEND ]",
            command=self.send_data,
            width=w,
            style="Dark.TButton",
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            btn_frame,
            text="[ CR ]",
            command=lambda: self.send_special("\r"),
            width=w,
            style="Dark.TButton",
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            btn_frame,
            text="[ LF ]",
            command=lambda: self.send_special("\n"),
            width=w,
            style="Dark.TButton",
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            btn_frame,
            text="[ CR+LF ]",
            command=lambda: self.send_special("\r\n"),
            width=w,
            style="Dark.TButton",
        ).pack(side=tk.LEFT)

    def _create_receive_frame(self):
        c = self.colors
        frame = ttk.LabelFrame(
            self.root, text="[ RECEIVE ]", padding="10", style="Dark.TLabelframe"
        )
        frame.grid(row=2, column=1, padx=(5, 10), pady=5, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        self.recv_text = self._make_scrolled_text(
            frame, height=8, fg_color=c["accent_cyan"]
        )
        self.recv_text.config(
            selectbackground="#1a2a3a",
            selectforeground=c["accent_cyan"],
        )
        self.recv_text.grid(row=0, column=0, sticky="nsew", pady=(0, 5))

        self.recv_text.tag_configure("source", foreground=c["accent_yellow"])
        self.recv_text.tag_configure("data", foreground=c["accent_cyan"])

        fmt_frame = ttk.Frame(frame, style="Dark.TFrame")
        fmt_frame.grid(row=1, column=0, sticky="ew")

        self.show_ascii = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            fmt_frame,
            text="Show ASCII",
            variable=self.show_ascii,
            style="Dark.TCheckbutton",
        ).pack(side=tk.LEFT)

    def _create_log_frame(self):
        c = self.colors
        frame = ttk.LabelFrame(
            self.root, text="[ SYSTEM LOG ]", padding="10", style="Dark.TLabelframe"
        )
        frame.grid(row=3, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        self.sys_log = self._make_scrolled_text(frame, height=4, fg_color=c["text_dim"])
        self.sys_log.config(
            selectbackground="#1a2a2a",
            selectforeground=c["text"],
        )
        self.sys_log.grid(row=0, column=0, sticky="nsew")

        self.sys_log.tag_configure("timestamp", foreground=c["text_dim"])
        self.sys_log.tag_configure("error", foreground=c["accent_red"])
        self.sys_log.tag_configure("sent", foreground=c["accent_orange"])
        self.sys_log.tag_configure("received", foreground=c["accent_cyan"])
        self.sys_log.tag_configure("success", foreground=c["accent"])
        self.sys_log.tag_configure("warning", foreground=c["accent_yellow"])
        self.sys_log.tag_configure("info", foreground=c["text"])

        self.log(f"Using font: {self.fonts['selected']}")

    # ------------------------------------------------------------------
    # Context menu
    # ------------------------------------------------------------------

    def _show_context_menu(self, event):
        self.file_menu.tk_popup(event.x_root, event.y_root)
        self.file_menu.grab_release()

    # ------------------------------------------------------------------
    # Cursor helper
    # ------------------------------------------------------------------

    def _apply_hand_cursor(self):
        """Recursively set the hand cursor on every ttk.Button."""

        def _walk(widget):
            try:
                if isinstance(widget, ttk.Button):
                    widget.configure(cursor="hand2")
            except TypeError:
                pass
            try:
                for child in widget.winfo_children():
                    _walk(child)
            except tk.TclError:
                pass

        _walk(self.root)

    # ------------------------------------------------------------------
    # File I/O helpers
    # ------------------------------------------------------------------

    def load_task_file(self):
        """Load a hex file into the transmit text box."""
        init_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = tkFileDialog.askopenfilename(
            title="Select a file to load",
            filetypes=(("Text files", "*.txt"), ("All files", "*.*")),
            initialdir=init_dir,
        )
        if file_path:
            with open(file_path, "r") as fh:
                self.send_text.delete("1.0", tk.END)
                self.send_text.insert(tk.END, fh.read())

    def save_task_file(self):
        """Save the transmit text box contents to a file."""
        init_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = tkFileDialog.asksaveasfilename(
            title="Specify a file to save",
            filetypes=(("Text files", "*.txt"), ("All files", "*.*")),
            initialdir=init_dir,
        )
        if file_path:
            with open(file_path, "w") as fh:
                fh.write(self.send_text.get("1.0", tk.END))

    # ------------------------------------------------------------------
    # Clear actions
    # ------------------------------------------------------------------

    def clear_send(self):
        self.send_text.delete("1.0", tk.END)

    def clear_received(self):
        self.recv_text.delete("1.0", tk.END)

    def clear_sys_log(self):
        self.sys_log.delete("1.0", tk.END)

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def log(self, message):
        """Append a colour-coded timestamped entry to the system log."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        if "Error" in message or "Failed" in message:
            tag = "error"
        elif "Sent" in message:
            tag = "sent"
        elif "Received" in message:
            tag = "received"
        elif "Started" in message:
            tag = "success"
        elif "Stopped" in message:
            tag = "warning"
        else:
            tag = "info"

        self.sys_log.insert(tk.END, f"[{timestamp}] ", "timestamp")
        self.sys_log.insert(tk.END, f"{message}\n", tag)
        self.sys_log.see(tk.END)

    # ------------------------------------------------------------------
    # UDP – listen / stop
    # ------------------------------------------------------------------

    def toggle_listening(self):
        if self.is_listening:
            self.stop_listening()
        else:
            self.start_listening()

    def start_listening(self):
        try:
            local_ip = self.local_ip.get().strip()
            local_port = int(self.local_port.get().strip())

            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((local_ip, local_port))
            self.sock.settimeout(0.5)

            self.is_listening = True
            self.bind_button.config(text="[ STOP ]")
            self.status_label.config(text="● LISTENING", fg=self.colors["accent"])

            self.listen_thread = threading.Thread(
                target=self._receive_loop, daemon=True
            )
            self.listen_thread.start()

            self.log(f"Started listening on {local_ip}:{local_port}")

        except Exception as exc:
            self.stop_listening()
            messagebox.showerror("Error", f"Failed to bind socket: {exc}")
            self.log(f"Error: Failed to bind - {exc}")

    def stop_listening(self):
        self.is_listening = False

        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None

        self.bind_button.config(text="[ START ]")
        self.status_label.config(text="● DISCONNECTED", fg=self.colors["accent_red"])
        self.log("Stopped listening")

    # ------------------------------------------------------------------
    # UDP – receive loop (runs in background thread)
    # ------------------------------------------------------------------

    def _receive_loop(self):
        while self.is_listening:
            try:
                if self.sock:
                    data, addr = self.sock.recvfrom(65535)
                    self.root.after(0, self._display_received, data, addr)
            except socket.timeout:
                continue
            except Exception as exc:
                if self.is_listening:
                    self.root.after(0, self.log, f"Error receiving data: {exc}")
                break

    def _display_received(self, data, addr):
        """Called on the main thread to render incoming data."""
        formatted = (
            self._format_ascii(data)
            if self.show_ascii.get()
            else self._format_hex(data)
        )
        self.recv_text.insert(tk.END, f"From {addr[0]}:{addr[1]}:\n", "source")
        self.recv_text.insert(tk.END, f"{formatted}\n\n", "data")
        self.recv_text.see(tk.END)

        self.log(f"Received {len(data)} bytes from {addr[0]}:{addr[1]}")

    # ------------------------------------------------------------------
    # UDP – send
    # ------------------------------------------------------------------

    def send_data(self):
        if not self.sock:
            messagebox.showwarning(
                "Warning", "Socket not bound. Please start listening first."
            )
            return

        try:
            hex_string = self.send_text.get("1.0", tk.END).strip()

            if not hex_string:
                messagebox.showwarning(
                    "Warning", "Please enter hexadecimal data to send."
                )
                return

            if not self._validate_hex(hex_string):
                messagebox.showerror(
                    "Error", "Invalid hexadecimal data. Use only 0-9, A-F characters."
                )
                return

            hex_clean = hex_string.replace(" ", "").replace("\n", "").replace("\r", "")
            data = bytes.fromhex(hex_clean)

            remote_ip = self.remote_ip.get().strip()
            remote_port = int(self.remote_port.get().strip())

            bytes_sent = self.sock.sendto(data, (remote_ip, remote_port))
            sent_display = (
                self._format_ascii(data)
                if self.show_ascii.get()
                else self._format_hex(data)
            )
            self.log(
                f"Sent {bytes_sent} bytes to {remote_ip}:{remote_port}: {sent_display}"
            )

        except ValueError as exc:
            messagebox.showerror("Error", f"Invalid hex data: {exc}")
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to send data: {exc}")
            self.log(f"Error sending: {exc}")

    def send_special(self, char):
        """Append the hex encoding of a special character to the TX box."""
        hex_val = " ".join(f"{ord(c):02X}" for c in char)
        current = self.send_text.get("1.0", tk.END).strip()
        self.send_text.insert(tk.END, f" {hex_val}" if current else hex_val)

    # ------------------------------------------------------------------
    # Data formatting
    # ------------------------------------------------------------------

    @staticmethod
    def _format_hex(data):
        return " ".join(f"{b:02X}" for b in data)

    @staticmethod
    def _format_ascii(data):
        hex_part = " ".join(f"{b:02X}" for b in data)
        ascii_part = "".join(chr(b) if 32 <= b <= 126 else "." for b in data)
        return f"{hex_part}  [{ascii_part}]"

    @staticmethod
    def _validate_hex(data):
        cleaned = data.replace(" ", "").replace("\n", "").replace("\r", "")
        return bool(cleaned and re.match(r"^[0-9A-Fa-f]+$", cleaned))

    # ------------------------------------------------------------------
    # Configuration persistence
    # ------------------------------------------------------------------

    def _config_path(self):
        return os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "gudp_messenger.json"
        )

    def load_config(self):
        path = self._config_path()
        if not os.path.exists(path):
            self.log("Config file not found, using defaults")
            return
        try:
            with open(path, "r") as fh:
                config = json.load(fh)

            conn = config.get("connection", {})
            for widget, key, default in (
                (self.local_ip, "local_ip", "0.0.0.0"),
                (self.local_port, "local_port", "8888"),
                (self.remote_ip, "remote_ip", "127.0.0.1"),
                (self.remote_port, "remote_port", "9999"),
            ):
                widget.delete(0, tk.END)
                widget.insert(0, str(conn.get(key, default)))

            self.log("Configuration loaded successfully")

        except Exception as exc:
            self.log(f"Error loading config: {exc}, using defaults")

    def save_config(self):
        path = self._config_path()
        try:
            config = {
                "connection": {
                    "local_ip": self.local_ip.get().strip(),
                    "local_port": int(self.local_port.get().strip()),
                    "remote_ip": self.remote_ip.get().strip(),
                    "remote_port": int(self.remote_port.get().strip()),
                }
            }
            with open(path, "w") as fh:
                json.dump(config, fh, indent=2)
            self.log("Configuration saved successfully")

        except Exception as exc:
            self.log(f"Error saving config: {exc}")

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def on_closing(self):
        self.save_config()
        self.stop_listening()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = GUdpMessenger(root)
    root.mainloop()
