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
            "bg_dark": "#0a0a0f",
            "bg_panel": "#0d1117",
            "bg_input": "#161b22",
            "border": "#30363d",
            "text": "#c9d1d9",
            "text_dim": "#8b949e",
            "accent": "#00ff41",  # Matrix green
            "accent_cyan": "#58a6ff",  # Terminal cyan
            "accent_orange": "#f0883e",  # Warning orange
            "accent_red": "#f85149",  # Error red
            "accent_yellow": "#e3b341",  # Yellow
            "terminal_green": "#00cc33",
        }

        # Select best available monospace font
        self.fonts = self.get_system_fonts()

        # Configure ttk styles
        self.setup_styles()

        # UDP Socket variables
        self.sock = None
        self.is_listening = False
        self.listen_thread = None

        # Create UI
        self.create_widgets()

        # Load configuration
        self.load_config()

        # Bind close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def get_system_fonts(self):
        """Select best available monospace fonts based on OS"""
        system = platform.system()

        if system == "Linux":
            # Best Linux monospace fonts in order of preference
            fonts = {
                "main": (
                    "JetBrains Mono",
                    "Fira Code",
                    "FiraCode Nerd Font",
                    "Cascadia Code",
                    "DejaVu Sans Mono",
                    "Ubuntu Mono",
                    "Liberation Mono",
                    "Noto Mono",
                    "Courier New",
                ),
                "size_normal": 10,
                "size_small": 9,
                "size_large": 10,
            }
        elif system == "Darwin":  # macOS
            fonts = {
                "main": (
                    "SF Mono",
                    "Menlo",
                    "Monaco",
                    "JetBrains Mono",
                    "Fira Code",
                    "Courier New",
                ),
                "size_normal": 10,
                "size_small": 9,
                "size_large": 10,
            }
        else:  # Windows and others
            fonts = {
                "main": ("Cascadia Code", "Consolas", "Courier New"),
                "size_normal": 10,
                "size_small": 9,
                "size_large": 10,
            }

        # Find first available font
        available_fonts = tkfont.families()
        for font in fonts["main"]:
            if font in available_fonts:
                fonts["selected"] = font
                break
        else:
            # Ultimate fallback
            fonts["selected"] = "Courier New"

        return fonts

    def setup_styles(self):
        """Configure custom ttk styles for dark industrial look"""
        style = ttk.Style()

        # Configure the theme
        style.theme_use("clam")

        # Create font tuples
        self.main_font = (self.fonts["selected"], self.fonts["size_normal"])
        self.small_font = (self.fonts["selected"], self.fonts["size_small"])
        self.large_font = (self.fonts["selected"], self.fonts["size_large"])
        self.bold_font = (self.fonts["selected"], self.fonts["size_large"], "bold")

        # Frame styles
        style.configure("Dark.TFrame", background=self.colors["bg_dark"])
        style.configure(
            "Dark.TLabelframe",
            background=self.colors["bg_dark"],
            foreground=self.colors["accent"],
            borderwidth=1,
            relief="solid",
        )
        style.configure(
            "Dark.TLabelframe.Label",
            background=self.colors["bg_dark"],
            foreground=self.colors["accent"],
            font=self.bold_font,
        )

        # Button styles
        style.configure(
            "Dark.TButton",
            background=self.colors["bg_input"],
            foreground=self.colors["accent"],
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

        # Label styles
        style.configure(
            "Dark.TLabel",
            background=self.colors["bg_dark"],
            foreground=self.colors["text"],
            font=self.small_font,
        )

        # Checkbutton styles
        style.configure(
            "Dark.TCheckbutton",
            background=self.colors["bg_dark"],
            foreground=self.colors["text_dim"],
            font=self.small_font,
        )
        style.map(
            "Dark.TCheckbutton",
            background=[("active", self.colors["bg_dark"])],
            foreground=[("active", self.colors["accent"])],
        )

        # Configure root window
        self.root.configure(bg=self.colors["bg_dark"])

    def create_entry(self, parent, width, initial_value=""):
        """Create a styled tk.Entry with centered text and yellow text color"""
        entry = tk.Entry(
            parent,
            width=width,
            justify="center",
            font=self.small_font,
            bg=self.colors["bg_input"],
            fg=self.colors["accent_cyan"],
            insertbackground=self.colors["accent_yellow"],
            relief="flat",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            highlightcolor=self.colors["accent"],
            selectbackground="#3a2a1a",
            selectforeground=self.colors["accent_yellow"],
        )
        if initial_value:
            entry.insert(0, initial_value)
        return entry

    def create_widgets(self):
        # Configure grid weights
        self.root.grid_rowconfigure(2, weight=1)
        self.root.grid_rowconfigure(3, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        # Connection Settings Frame
        settings_frame = ttk.LabelFrame(
            self.root,
            text="[ CONNECTION SETTINGS ]",
            padding="10",
            style="Dark.TLabelframe",
        )
        settings_frame.grid(
            row=0, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="ew"
        )

        # Local settings
        ttk.Label(settings_frame, text="Local IP:", style="Dark.TLabel").grid(
            row=0, column=0, sticky="w", padx=(0, 5)
        )
        self.local_ip = self.create_entry(
            settings_frame, width=16, initial_value="0.0.0.0"
        )
        self.local_ip.grid(row=0, column=1, padx=(0, 10))

        ttk.Label(settings_frame, text="Local Port:", style="Dark.TLabel").grid(
            row=0, column=2, sticky="w", padx=(0, 5)
        )
        self.local_port = self.create_entry(
            settings_frame, width=9, initial_value="8888"
        )
        self.local_port.grid(row=0, column=3, padx=(0, 20))

        # Remote settings
        ttk.Label(settings_frame, text="Remote IP:", style="Dark.TLabel").grid(
            row=0, column=4, sticky="w", padx=(0, 5)
        )
        self.remote_ip = self.create_entry(
            settings_frame, width=16, initial_value="127.0.0.1"
        )
        self.remote_ip.grid(row=0, column=5, padx=(0, 10))

        ttk.Label(settings_frame, text="Remote Port:", style="Dark.TLabel").grid(
            row=0, column=6, sticky="w", padx=(0, 5)
        )
        self.remote_port = self.create_entry(
            settings_frame, width=9, initial_value="9999"
        )
        self.remote_port.grid(row=0, column=7, padx=(0, 0))

        # Control buttons
        control_frame = ttk.Frame(self.root, style="Dark.TFrame")
        control_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        # Standard button width for primary buttons
        button_width = 13

        self.bind_button = ttk.Button(
            control_frame,
            text="[ START ]",
            command=self.toggle_listening,
            width=button_width,
            style="Dark.TButton",
        )
        self.bind_button.pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            control_frame,
            text="[ CLEAR TX ]",
            command=self.clear_send,
            width=button_width,
            style="Dark.TButton",
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            control_frame,
            text="[ CLEAR RX ]",
            command=self.clear_received,
            width=button_width,
            style="Dark.TButton",
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            control_frame,
            text="[ CLEAR LOG ]",
            command=self.clear_sys_log,
            width=button_width,
            style="Dark.TButton",
        ).pack(side=tk.LEFT, padx=(0, 5))

        # Custom status label with tk.Label for more styling options
        self.status_label = tk.Label(
            control_frame,
            text="● DISCONNECTED",
            fg=self.colors["accent_red"],
            bg=self.colors["bg_dark"],
            font=self.bold_font,
        )
        self.status_label.pack(side=tk.RIGHT)

        # Send Frame
        send_frame = ttk.LabelFrame(
            self.root, text="[ TRANSMIT ]", padding="10", style="Dark.TLabelframe"
        )
        send_frame.grid(row=2, column=0, padx=(10, 5), pady=5, sticky="nsew")
        send_frame.grid_columnconfigure(0, weight=1)
        send_frame.grid_rowconfigure(0, weight=1)

        # Send text box
        self.send_text = scrolledtext.ScrolledText(
            send_frame,
            height=8,
            wrap=tk.WORD,
            font=self.main_font,
            bg=self.colors["bg_input"],
            fg=self.colors["accent"],
            insertbackground=self.colors["accent"],
            selectbackground="#1a3a2a",
            selectforeground=self.colors["accent"],
            relief="flat",
            borderwidth=1,
            highlightthickness=0,
        )
        self.send_text.grid(row=0, column=0, sticky="nsew", pady=(0, 5))

        # Create the context menu
        self.file_menu = tk.Menu(self.root, tearoff=0)
        self.file_menu.add_command(label="Open File", command=self.load_task_file)
        self.file_menu.add_command(label="Save File", command=self.save_task_file)

        # Bind the context menu to the send_text widget
        self.send_text.bind("<Button-3>", self.show_context_menu)

        # Bind the context menu to the ESCAPE click
        self.send_text.bind("<Escape>", self.file_menu.grab_release())

        # Send button frame
        send_btn_frame = ttk.Frame(send_frame, style="Dark.TFrame")
        send_btn_frame.grid(row=1, column=0, sticky="ew")

        # Standard button width for secondary buttons
        button_width = 12

        ttk.Button(
            send_btn_frame,
            text="[ SEND ]",
            command=self.send_data,
            width=button_width,
            style="Dark.TButton",
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            send_btn_frame,
            text="[ CR ]",
            command=lambda: self.send_special("\r"),
            width=button_width,
            style="Dark.TButton",
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            send_btn_frame,
            text="[ LF ]",
            command=lambda: self.send_special("\n"),
            width=button_width,
            style="Dark.TButton",
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            send_btn_frame,
            text="[ CR+LF ]",
            command=lambda: self.send_special("\r\n"),
            width=button_width,
            style="Dark.TButton",
        ).pack(side=tk.LEFT)

        # Received Frame
        recv_frame = ttk.LabelFrame(
            self.root, text="[ RECEIVE ]", padding="10", style="Dark.TLabelframe"
        )
        recv_frame.grid(row=2, column=1, padx=(5, 10), pady=5, sticky="nsew")
        recv_frame.grid_columnconfigure(0, weight=1)
        recv_frame.grid_rowconfigure(0, weight=1)

        # Receive text box (read-only)
        self.recv_text = scrolledtext.ScrolledText(
            recv_frame,
            height=8,
            wrap=tk.WORD,
            font=self.main_font,
            bg=self.colors["bg_input"],
            fg=self.colors["accent_cyan"],
            insertbackground=self.colors["accent_cyan"],
            selectbackground="#1a2a3a",
            selectforeground=self.colors["accent_cyan"],
            relief="flat",
            borderwidth=1,
            highlightthickness=0,
        )
        self.recv_text.grid(row=0, column=0, sticky="nsew", pady=(0, 5))

        # Display format checkbox
        format_frame = ttk.Frame(recv_frame, style="Dark.TFrame")
        format_frame.grid(row=1, column=0, sticky="ew")

        self.show_ascii = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            format_frame,
            text="Show ASCII",
            variable=self.show_ascii,
            style="Dark.TCheckbutton",
        ).pack(side=tk.LEFT)

        # System Log Frame
        log_frame = ttk.LabelFrame(
            self.root, text="[ SYSTEM LOG ]", padding="10", style="Dark.TLabelframe"
        )
        log_frame.grid(
            row=3, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="nsew"
        )
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)

        self.sys_log = scrolledtext.ScrolledText(
            log_frame,
            height=4,
            wrap=tk.WORD,
            font=self.small_font,
            bg=self.colors["bg_input"],
            fg=self.colors["text_dim"],
            insertbackground=self.colors["text_dim"],
            selectbackground="#1a2a2a",
            selectforeground=self.colors["text"],
            relief="flat",
            borderwidth=1,
            highlightthickness=0,
        )
        self.sys_log.grid(row=0, column=0, sticky="nsew")

        # Log font info
        self.log(f"Using font: {self.fonts['selected']}")

        # Apply hand cursor to all buttons
        self.apply_hand_cursor_to_buttons()

    def show_context_menu(self, event):
        """Show the context menu at the cursor position"""
        self.file_menu.tk_popup(event.x_root, event.y_root)
        self.file_menu.grab_release()

    def load_task_file(self):
        """Load a hexadecimal file into the send_text widget"""
        # Use the script path as initial directory
        init_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = tkFileDialog.askopenfilename(
            title="Select a file to load",
            filetypes=(("Text files", "*.txt"), ("All files", "*.*")),
            initialdir=init_dir,
        )
        if file_path:
            with open(file_path, "r") as file:
                content = file.read()
                self.send_text.delete("1.0", tk.END)
                self.send_text.insert(tk.END, content)

    def save_task_file(self):
        """Save the hexadecimal content of send_text widget to a file"""
        # Use the script path as initial directory
        init_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = tkFileDialog.asksaveasfilename(
            title="Specify a file to save",
            filetypes=(("Text files", "*.txt"), ("All files", "*.*")),
            initialdir=init_dir,
        )
        if file_path:
            with open(file_path, "w") as file:
                content = self.send_text.get("1.0", tk.END)
                file.write(content)

    def clear_send(self):
        """Clear send text box"""
        self.send_text.delete("1.0", tk.END)

    def clear_received(self):
        """Clear received text box"""
        self.recv_text.delete("1.0", tk.END)

    def clear_sys_log(self):
        """Clear system log text box"""
        self.sys_log.delete("1.0", tk.END)

    def apply_hand_cursor_to_buttons(self):
        """Apply hand cursor to all ttk buttons in the application"""
        for widget in self.root.winfo_children():
            self._set_cursor_recursive(widget)

    def _set_cursor_recursive(self, widget):
        """Recursively set hand cursor on all button widgets"""
        try:
            if isinstance(widget, ttk.Button):
                widget.configure(cursor="hand2")
        except TypeError:
            pass

        # Process children
        try:
            for child in widget.winfo_children():
                self._set_cursor_recursive(child)
        except tk.TclError:
            # Handle specific error related to Tkinter widgets
            pass

    def validate_hex(self, data):
        """Validate if string contains valid hex characters"""
        # Remove spaces and newlines for validation
        cleaned = data.replace(" ", "").replace("\n", "").replace("\r", "")
        if not cleaned:
            return False
        return bool(re.match(r"^[0-9A-Fa-f]+$", cleaned))

    def format_hex_output(self, data):
        """Format bytes as hex string with spaces"""
        return " ".join(f"{b:02X}" for b in data)

    def format_ascii_output(self, data):
        """Format bytes showing both hex and ASCII"""
        hex_part = self.format_hex_output(data)
        ascii_part = "".join(chr(b) if 32 <= b <= 126 else "." for b in data)
        return f"{hex_part}  [{ascii_part}]"

    def toggle_listening(self):
        """Start or stop UDP listening"""
        if not self.is_listening:
            self.start_listening()
        else:
            self.stop_listening()

    def start_listening(self):
        """Start UDP listener"""
        try:
            local_ip = self.local_ip.get().strip()
            local_port = int(self.local_port.get().strip())

            # Create UDP socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((local_ip, local_port))
            self.sock.settimeout(0.5)  # 0.5 second timeout

            self.is_listening = True
            self.bind_button.config(text="[ STOP ]")
            self.status_label.config(text="● LISTENING", fg=self.colors["accent"])

            # Start listening thread
            self.listen_thread = threading.Thread(target=self.receive_data, daemon=True)
            self.listen_thread.start()

            self.log(f"Started listening on {local_ip}:{local_port}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to bind socket: {str(e)}")
            self.log(f"Error: Failed to bind - {str(e)}")

    def stop_listening(self):
        """Stop UDP listener"""
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

    def receive_data(self):
        """Receive data in a separate thread"""
        while self.is_listening:
            try:
                if self.sock:
                    data, addr = self.sock.recvfrom(65535)

                    # Update UI in main thread
                    self.root.after(0, self.display_received_data, data, addr)

            except socket.timeout:
                continue
            except Exception as e:
                if self.is_listening:
                    self.root.after(0, self.log, f"Error receiving data: {str(e)}")
                break

    def display_received_data(self, data, addr):
        """Display received data in the receive text box"""
        if self.show_ascii.get():
            formatted_data = self.format_ascii_output(data)
        else:
            formatted_data = self.format_hex_output(data)

        # Insert received data with styling
        self.recv_text.insert(tk.END, f"From {addr[0]}:{addr[1]}:\n", "source")
        self.recv_text.insert(tk.END, f"{formatted_data}\n\n", "data")
        self.recv_text.see(tk.END)

        # Configure tags for colored text
        self.recv_text.tag_configure("source", foreground=self.colors["accent_yellow"])
        self.recv_text.tag_configure("data", foreground=self.colors["accent_cyan"])

        self.log(f"Received {len(data)} bytes from {addr[0]}:{addr[1]}")

    def send_data(self):
        """Send hex data to remote address"""
        if not self.sock:
            messagebox.showwarning(
                "Warning", "Socket not bound. Please start listening first."
            )
            return

        try:
            # Get data from send text box
            hex_string = self.send_text.get("1.0", tk.END).strip()

            if not hex_string:
                messagebox.showwarning(
                    "Warning", "Please enter hexadecimal data to send."
                )
                return

            # Validate hex
            if not self.validate_hex(hex_string):
                messagebox.showerror(
                    "Error", "Invalid hexadecimal data. Use only 0-9, A-F characters."
                )
                return

            # Remove spaces and convert to bytes
            hex_string = hex_string.replace(" ", "").replace("\n", "").replace("\r", "")
            data = bytes.fromhex(hex_string)

            # Get remote address
            remote_ip = self.remote_ip.get().strip()
            remote_port = int(self.remote_port.get().strip())

            # Send data
            bytes_sent = self.sock.sendto(data, (remote_ip, remote_port))

            # Log the sent data
            if self.show_ascii.get():
                sent_display = self.format_ascii_output(data)
            else:
                sent_display = self.format_hex_output(data)

            self.log(
                f"Sent {bytes_sent} bytes to {remote_ip}:{remote_port}: {sent_display}"
            )

        except ValueError as e:
            messagebox.showerror("Error", f"Invalid hex data: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send data: {str(e)}")
            self.log(f"Error sending: {str(e)}")

    def send_special(self, char):
        """Send special characters (CR, LF)"""
        # Insert the hex representation into the send box
        hex_val = " ".join(f"{ord(c):02X}" for c in char)

        current = self.send_text.get("1.0", tk.END).strip()
        if current:
            self.send_text.insert(tk.END, f" {hex_val}")
        else:
            self.send_text.insert(tk.END, hex_val)

    def log(self, message):
        """Add message to log with color coding"""
        from datetime import datetime

        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        # Color code different message types
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

        # Configure log tags
        self.sys_log.tag_configure("timestamp", foreground=self.colors["text_dim"])
        self.sys_log.tag_configure("error", foreground=self.colors["accent_red"])
        self.sys_log.tag_configure("sent", foreground=self.colors["accent_orange"])
        self.sys_log.tag_configure("received", foreground=self.colors["accent_cyan"])
        self.sys_log.tag_configure("success", foreground=self.colors["accent"])
        self.sys_log.tag_configure("warning", foreground=self.colors["accent_yellow"])
        self.sys_log.tag_configure("info", foreground=self.colors["text"])

    def get_config_path(self):
        """Get the path to the configuration file"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(script_dir, "gudp_messenger.json")

    def load_config(self):
        """Load configuration from JSON file"""
        config_path = self.get_config_path()

        if not os.path.exists(config_path):
            self.log("Config file not found, using defaults")
            return

        try:
            with open(config_path, "r") as f:
                config = json.load(f)

            connection = config.get("connection", {})

            local_ip = connection.get("local_ip", "0.0.0.0")
            local_port = connection.get("local_port", 8888)
            remote_ip = connection.get("remote_ip", "127.0.0.1")
            remote_port = connection.get("remote_port", 9999)

            self.local_ip.delete(0, tk.END)
            self.local_ip.insert(0, local_ip)

            self.local_port.delete(0, tk.END)
            self.local_port.insert(0, str(local_port))

            self.remote_ip.delete(0, tk.END)
            self.remote_ip.insert(0, remote_ip)

            self.remote_port.delete(0, tk.END)
            self.remote_port.insert(0, str(remote_port))

            self.log("Configuration loaded successfully")

        except Exception as e:
            self.log(f"Error loading config: {str(e)}, using defaults")

    def save_config(self):
        """Save configuration to JSON file"""
        config_path = self.get_config_path()

        try:
            config = {
                "connection": {
                    "local_ip": self.local_ip.get().strip(),
                    "local_port": int(self.local_port.get().strip()),
                    "remote_ip": self.remote_ip.get().strip(),
                    "remote_port": int(self.remote_port.get().strip()),
                }
            }

            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)

            self.log("Configuration saved successfully")

        except Exception as e:
            self.log(f"Error saving config: {str(e)}")

    def on_closing(self):
        """Handle window closing"""
        self.save_config()
        self.stop_listening()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = GUdpMessenger(root)
    root.mainloop()
