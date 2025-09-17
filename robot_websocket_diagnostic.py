#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import websocket
import threading
import json
import time
from datetime import datetime

class RobotWebSocketDiagnostic:
    def __init__(self, root):
        self.root = root
        self.root.title("Robot WebSocket Diagnostic - Port 8000")
        self.root.geometry("700x600")
        
        # WebSocket connection
        self.ws = None
        self.connected = False
        self.connection_thread = None
        self.server_url = "ws://localhost:8000"
        self.connection_verified = False
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # Connection frame
        self.setup_connection_frame(main_frame)
        
        # Test frame
        self.setup_test_frame(main_frame)
        
        # Messages log frame
        self.setup_messages_log_frame(main_frame)
        
    def setup_connection_frame(self, parent):
        conn_frame = ttk.LabelFrame(parent, text="Connection Diagnostic", padding="10")
        conn_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        conn_frame.columnconfigure(1, weight=1)
        
        # Server URL
        ttk.Label(conn_frame, text="Robot Controller Server:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.url_label = ttk.Label(conn_frame, text=self.server_url, foreground="blue", font=("Arial", 10, "bold"))
        self.url_label.grid(row=0, column=1, sticky=tk.W)
        
        # Connection buttons
        button_frame = ttk.Frame(conn_frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=(10, 0))
        
        self.connect_btn = ttk.Button(button_frame, text="Test Connection", command=self.test_connection)
        self.connect_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.disconnect_btn = ttk.Button(button_frame, text="Disconnect", command=self.disconnect, state=tk.DISABLED)
        self.disconnect_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Status
        self.status_label = ttk.Label(button_frame, text="Not Connected", foreground="red")
        self.status_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # Connection verification
        self.verify_label = ttk.Label(button_frame, text="❌ Not Verified", foreground="red")
        self.verify_label.pack(side=tk.LEFT, padx=(20, 0))
        
    def setup_test_frame(self, parent):
        test_frame = ttk.LabelFrame(parent, text="Connection Tests", padding="10")
        test_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Test buttons
        button_frame = ttk.Frame(test_frame)
        button_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        ttk.Button(button_frame, text="Send Ping", command=self.send_ping, state=tk.DISABLED).pack(side=tk.LEFT, padx=(0, 5))
        setattr(self, "ping_btn", ttk.Button(button_frame, text="Send Ping", command=self.send_ping, state=tk.DISABLED))
        self.ping_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(button_frame, text="Send Location", command=self.send_location, state=tk.DISABLED).pack(side=tk.LEFT, padx=(0, 5))
        setattr(self, "location_btn", ttk.Button(button_frame, text="Send Location", command=self.send_location, state=tk.DISABLED))
        self.location_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(button_frame, text="Send Status", command=self.send_status, state=tk.DISABLED).pack(side=tk.LEFT, padx=(0, 5))
        setattr(self, "status_btn", ttk.Button(button_frame, text="Send Status", command=self.send_status, state=tk.DISABLED))
        self.status_btn.pack(side=tk.LEFT, padx=(0, 5))
        
    def setup_messages_log_frame(self, parent):
        log_frame = ttk.LabelFrame(parent, text="Diagnostic Log", padding="10")
        log_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Messages text area
        self.messages_text = scrolledtext.ScrolledText(log_frame, height=15, state=tk.DISABLED)
        self.messages_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Control buttons
        control_frame = ttk.Frame(log_frame)
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.clear_btn = ttk.Button(control_frame, text="Clear Log", command=self.clear_messages)
        self.clear_btn.pack(side=tk.LEFT)
        
        # Message counter
        self.message_count_label = ttk.Label(control_frame, text="Messages: 0")
        self.message_count_label.pack(side=tk.RIGHT)
        
        self.message_count = 0
        
    def log_message(self, message_type, content):
        """Log a message to the text area with timestamp and color coding"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Color coding
        colors = {
            "SENT": "blue",
            "RECEIVED": "green", 
            "SUCCESS": "darkgreen",
            "ERROR": "red",
            "INFO": "purple",
            "WARNING": "orange",
            "DIAGNOSTIC": "darkblue"
        }
        
        log_entry = f"[{timestamp}] {message_type}: {content}\n"
        
        self.messages_text.config(state=tk.NORMAL)
        self.messages_text.insert(tk.END, log_entry)
        
        # Apply color
        if message_type in colors:
            start = self.messages_text.index(tk.END + "-2l")
            end = self.messages_text.index(tk.END + "-1l")
            self.messages_text.tag_add(message_type, start, end)
            self.messages_text.tag_config(message_type, foreground=colors[message_type])
        
        self.messages_text.config(state=tk.DISABLED)
        self.messages_text.see(tk.END)
        
        # Update counter
        self.message_count += 1
        self.message_count_label.config(text=f"Messages: {self.message_count}")
        
    def test_connection(self):
        """Test connection with detailed diagnostics"""
        self.log_message("DIAGNOSTIC", f"🔍 Starting connection test to: {self.server_url}")
        self.log_message("INFO", "📡 Attempting WebSocket connection...")
        
        try:
            # Create WebSocket connection
            self.ws = websocket.WebSocketApp(
                self.server_url,
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )
            
            # Start connection in a separate thread
            self.connection_thread = threading.Thread(target=self.ws.run_forever)
            self.connection_thread.daemon = True
            self.connection_thread.start()
            
            # Wait a moment then verify connection
            self.root.after(2000, self.verify_connection)
            
        except Exception as e:
            self.log_message("ERROR", f"❌ Connection failed: {str(e)}")
            messagebox.showerror("Connection Error", f"Failed to connect: {str(e)}")
            
    def verify_connection(self):
        """Verify if connection is actually working"""
        if self.connected:
            self.log_message("DIAGNOSTIC", "🔍 Verifying connection...")
            self.log_message("WARNING", "⚠️  Connection reported as 'open' - testing with ping...")
            
            # Send a ping to verify
            self.send_ping()
            
            # Wait 3 seconds to see if we get a response
            self.root.after(3000, self.check_verification)
        else:
            self.log_message("ERROR", "❌ Connection failed - no 'open' event received")
            
    def check_verification(self):
        """Check if connection verification was successful"""
        if self.connection_verified:
            self.log_message("SUCCESS", "✅ Connection verified - server is responding!")
            self.verify_label.config(text="✅ Verified", foreground="green")
        else:
            self.log_message("ERROR", "❌ Connection NOT verified - server not responding")
            self.log_message("WARNING", "⚠️  This usually means the WebSocket server is not running")
            self.verify_label.config(text="❌ Not Verified", foreground="red")
            self.connected = False
            self.update_connection_ui()
            
    def disconnect(self):
        """Disconnect from WebSocket server"""
        if self.ws:
            self.ws.close()
            self.log_message("INFO", "🔌 Disconnection requested")
            
    def on_open(self, ws):
        """WebSocket connection opened"""
        self.connected = True
        self.connection_verified = False
        self.root.after(0, self.update_connection_ui)
        self.root.after(0, lambda: self.log_message("SUCCESS", "🔗 WebSocket connection opened"))
        self.root.after(0, lambda: self.log_message("WARNING", "⚠️  Note: 'Open' event doesn't guarantee server is running"))
        
    def on_message(self, ws, message):
        """WebSocket message received"""
        self.connection_verified = True
        try:
            # Try to parse as JSON
            parsed = json.loads(message)
            self.root.after(0, lambda: self.log_message("RECEIVED", f"📨 Server response: {json.dumps(parsed, indent=2)}"))
        except json.JSONDecodeError:
            # If not JSON, log as plain text
            self.root.after(0, lambda: self.log_message("RECEIVED", f"📨 Server response: {message}"))
        
    def on_error(self, ws, error):
        """WebSocket error occurred"""
        self.root.after(0, lambda: self.log_message("ERROR", f"❌ WebSocket error: {str(error)}"))
        self.connected = False
        self.connection_verified = False
        self.root.after(0, self.update_connection_ui)
        
    def on_close(self, ws, close_status_code, close_msg):
        """WebSocket connection closed"""
        self.connected = False
        self.connection_verified = False
        self.root.after(0, self.update_connection_ui)
        self.log_message("INFO", f"🔌 Connection closed (Code: {close_status_code}, Message: {close_msg})")
        
    def update_connection_ui(self):
        """Update UI based on connection status"""
        if self.connected:
            self.status_label.config(text="Connected", foreground="green")
            self.connect_btn.config(state=tk.DISABLED)
            self.disconnect_btn.config(state=tk.NORMAL)
            
            # Enable test buttons
            self.ping_btn.config(state=tk.NORMAL)
            self.location_btn.config(state=tk.NORMAL)
            self.status_btn.config(state=tk.NORMAL)
        else:
            self.status_label.config(text="Not Connected", foreground="red")
            self.connect_btn.config(state=tk.NORMAL)
            self.disconnect_btn.config(state=tk.DISABLED)
            
            # Disable test buttons
            self.ping_btn.config(state=tk.DISABLED)
            self.location_btn.config(state=tk.DISABLED)
            self.status_btn.config(state=tk.DISABLED)
            
            self.verify_label.config(text="❌ Not Verified", foreground="red")
                
    def send_ping(self):
        """Send ping message to verify connection"""
        if self.connected and self.ws:
            try:
                ping_message = {
                    "type": "ping",
                    "timestamp": datetime.now().isoformat()
                }
                self.ws.send(json.dumps(ping_message))
                self.log_message("SENT", f"🏓 Ping sent: {json.dumps(ping_message, indent=2)}")
                self.log_message("DIAGNOSTIC", "⏳ Waiting for server response...")
            except Exception as e:
                self.log_message("ERROR", f"❌ Failed to send ping: {str(e)}")
        else:
            messagebox.showwarning("Warning", "Not connected to WebSocket server")
            
    def send_location(self):
        """Send location update"""
        if self.connected and self.ws:
            try:
                location_message = {
                    "type": "location",
                    "data": {
                        "lat": 37.7749,
                        "lng": -122.4194,
                        "timestamp": datetime.now().isoformat()
                    }
                }
                self.ws.send(json.dumps(location_message))
                self.log_message("SENT", f"📡 Location sent: {json.dumps(location_message, indent=2)}")
            except Exception as e:
                self.log_message("ERROR", f"❌ Failed to send location: {str(e)}")
        else:
            messagebox.showwarning("Warning", "Not connected to WebSocket server")
            
    def send_status(self):
        """Send status update"""
        if self.connected and self.ws:
            try:
                status_message = {
                    "type": "status",
                    "data": {
                        "battery": 85,
                        "speed": 2.5,
                        "mode": "autonomous",
                        "timestamp": datetime.now().isoformat()
                    }
                }
                self.ws.send(json.dumps(status_message))
                self.log_message("SENT", f"📊 Status sent: {json.dumps(status_message, indent=2)}")
            except Exception as e:
                self.log_message("ERROR", f"❌ Failed to send status: {str(e)}")
        else:
            messagebox.showwarning("Warning", "Not connected to WebSocket server")
            
    def clear_messages(self):
        """Clear the messages log"""
        self.messages_text.config(state=tk.NORMAL)
        self.messages_text.delete(1.0, tk.END)
        self.messages_text.config(state=tk.DISABLED)
        self.message_count = 0
        self.message_count_label.config(text="Messages: 0")

def main():
    root = tk.Tk()
    app = RobotWebSocketDiagnostic(root)
    
    # Handle window closing
    def on_closing():
        if app.connected and app.ws:
            app.disconnect()
        root.destroy()
        
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
