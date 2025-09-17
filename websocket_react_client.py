#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import websocket
import threading
import json
import time
from datetime import datetime

class WebSocketReactClient:
    def __init__(self, root):
        self.root = root
        self.root.title("WebSocket React Client - Port 8000")
        self.root.geometry("900x800")
        
        # WebSocket connection
        self.ws = None
        self.connected = False
        self.connection_thread = None
        self.server_url = "ws://localhost:8000"
        self.connection_verified = False
        self.connected_robots = []
        self.last_message = None
        self.error = None
        
        # Reconnection settings (matching React hook)
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_timeout = None
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # Connection frame
        self.setup_connection_frame(main_frame)
        
        # Send data frame
        self.setup_send_data_frame(main_frame)
        
        # Connected robots frame
        self.setup_robots_frame(main_frame)
        
        # Messages log frame
        self.setup_messages_log_frame(main_frame)
        
    def setup_connection_frame(self, parent):
        conn_frame = ttk.LabelFrame(parent, text="Connection Status", padding="10")
        conn_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        conn_frame.columnconfigure(1, weight=1)
        
        # Server URL
        ttk.Label(conn_frame, text="WebSocket Server:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.url_label = ttk.Label(conn_frame, text=self.server_url, foreground="blue", font=("Arial", 10, "bold"))
        self.url_label.grid(row=0, column=1, sticky=tk.W)
        
        # Connection status
        status_frame = ttk.Frame(conn_frame)
        status_frame.grid(row=1, column=0, columnspan=2, pady=(10, 0))
        
        self.connect_btn = ttk.Button(status_frame, text="Connect", command=self.connect)
        self.connect_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.disconnect_btn = ttk.Button(status_frame, text="Disconnect", command=self.disconnect, state=tk.DISABLED)
        self.disconnect_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Status
        self.status_label = ttk.Label(status_frame, text="Not Connected", foreground="red")
        self.status_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # Error display
        self.error_label = ttk.Label(status_frame, text="", foreground="red")
        self.error_label.pack(side=tk.LEFT, padx=(20, 0))
        
    def setup_send_data_frame(self, parent):
        send_frame = ttk.LabelFrame(parent, text="Send Location Data", padding="10")
        send_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        send_frame.columnconfigure(1, weight=1)
        
        # Latitude input
        ttk.Label(send_frame, text="Latitude:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=(0, 5))
        self.lat_var = tk.StringVar(value="37.7749")
        self.lat_entry = ttk.Entry(send_frame, textvariable=self.lat_var, width=15)
        self.lat_entry.grid(row=0, column=1, sticky=tk.W, pady=(0, 5))
        
        # Longitude input
        ttk.Label(send_frame, text="Longitude:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(0, 5))
        self.lng_var = tk.StringVar(value="-122.4194")
        self.lng_entry = ttk.Entry(send_frame, textvariable=self.lng_var, width=15)
        self.lng_entry.grid(row=1, column=1, sticky=tk.W, pady=(0, 5))
        
        # Buttons frame
        buttons_frame = ttk.Frame(send_frame)
        buttons_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0))
        
        # Send location button
        self.send_location_btn = ttk.Button(buttons_frame, text="Send Location", command=self.send_location, state=tk.DISABLED)
        self.send_location_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Send status button
        self.send_status_btn = ttk.Button(buttons_frame, text="Send Status", command=self.send_status, state=tk.DISABLED)
        self.send_status_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Send ping button
        self.send_ping_btn = ttk.Button(buttons_frame, text="Send Ping", command=self.send_ping, state=tk.DISABLED)
        self.send_ping_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Quick location buttons
        quick_frame = ttk.Frame(send_frame)
        quick_frame.grid(row=3, column=0, columnspan=2, pady=(10, 0))
        
        ttk.Label(quick_frame, text="Quick Locations:").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(quick_frame, text="San Francisco", command=lambda: self.set_location(37.7749, -122.4194)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(quick_frame, text="New York", command=lambda: self.set_location(40.7128, -74.0060)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(quick_frame, text="London", command=lambda: self.set_location(51.5074, -0.1278)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(quick_frame, text="Tokyo", command=lambda: self.set_location(35.6762, 139.6503)).pack(side=tk.LEFT, padx=(0, 5))
        
    def setup_robots_frame(self, parent):
        robots_frame = ttk.LabelFrame(parent, text="Connected Robots (React State)", padding="10")
        robots_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        robots_frame.columnconfigure(0, weight=1)
        
        # Robots list
        self.robots_text = tk.Text(robots_frame, height=3, state=tk.DISABLED, wrap=tk.WORD)
        self.robots_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # Scrollbar for robots
        robots_scrollbar = ttk.Scrollbar(robots_frame, orient=tk.VERTICAL, command=self.robots_text.yview)
        robots_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.robots_text.config(yscrollcommand=robots_scrollbar.set)
        
    def setup_messages_log_frame(self, parent):
        log_frame = ttk.LabelFrame(parent, text="WebSocket Messages (React Hook Behavior)", padding="10")
        log_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Messages text area
        self.messages_text = scrolledtext.ScrolledText(log_frame, height=20, state=tk.DISABLED)
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
        
    def set_location(self, lat, lng):
        """Set latitude and longitude values"""
        self.lat_var.set(str(lat))
        self.lng_var.set(str(lng))
        
    def send_location(self):
        """Send location data to WebSocket server"""
        try:
            lat = float(self.lat_var.get())
            lng = float(self.lng_var.get())
            
            location_message = {
                "type": "location",
                "data": {
                    "lat": lat,
                    "lng": lng,
                    "timestamp": datetime.now().isoformat() + "Z"
                }
            }
            
            self.send_message(location_message)
            self.log_message("SENT", f"📍 Sent location: {lat}, {lng}")
            
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid latitude and longitude numbers")
            
    def send_status(self):
        """Send status data to WebSocket server"""
        status_message = {
            "type": "status",
            "data": {
                "battery": 85,
                "speed": 2.5,
                "mode": "autonomous",
                "timestamp": datetime.now().isoformat() + "Z"
            }
        }
        
        self.send_message(status_message)
        self.log_message("SENT", f"📊 Sent status update")
        
    def send_ping(self):
        """Send ping to WebSocket server"""
        ping_message = {
            "type": "ping",
            "timestamp": datetime.now().isoformat() + "Z"
        }
        
        self.send_message(ping_message)
        self.log_message("SENT", f"�� Sent ping")
        
    def send_message(self, message):
        """Send message to WebSocket server"""
        if self.ws and self.connected:
            try:
                self.ws.send(json.dumps(message))
                self.log_message("SENT", f"⬆️ Sent: {json.dumps(message, indent=2)}")
            except Exception as e:
                self.log_message("ERROR", f"❌ Failed to send message: {e}")
        else:
            self.log_message("WARNING", "⚠️ Not connected - cannot send message")
        
    def log_message(self, message_type, content):
        """Log a message to the text area with timestamp and color coding"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Color coding
        colors = {
            "SUCCESS": "darkgreen",
            "ERROR": "red",
            "INFO": "purple",
            "WARNING": "orange",
            "DIAGNOSTIC": "darkblue",
            "CONNECTED": "darkgreen",
            "DISCONNECTED": "red",
            "RECEIVED": "green",
            "CONNECTED_ROBOTS": "darkcyan",
            "ROBOT_CONNECTED": "darkgreen",
            "ROBOT_DISCONNECTED": "red",
            "ROBOT_LOCATION": "green",
            "ROBOT_STATUS": "darkgreen",
            "SENT": "blue",
            "RAW_MESSAGE": "black",
            "PARSED_MESSAGE": "darkblue"
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
        
    def update_robots_display(self):
        """Update the connected robots display (matching React state)"""
        self.robots_text.config(state=tk.NORMAL)
        self.robots_text.delete(1.0, tk.END)
        
        if self.connected_robots:
            robots_text = f"Connected Robots ({len(self.connected_robots)}):\n"
            for i, robot_id in enumerate(self.connected_robots, 1):
                robots_text += f"{i}. {robot_id}\n"
        else:
            robots_text = "No robots connected"
            
        self.robots_text.insert(1.0, robots_text)
        self.robots_text.config(state=tk.DISABLED)
        
    def connect(self):
        """Connect to WebSocket server (matching React hook behavior)"""
        self.log_message("DIAGNOSTIC", f"🔍 Connecting to: {self.server_url}")
        self.log_message("INFO", "📡 Starting WebSocket connection (React hook behavior)...")
        self.log_message("INFO", "🌐 This connects as a web client, not a robot")
        self.log_message("INFO", "📱 Will receive broadcasted messages from the server")
        
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
            
        except Exception as e:
            self.log_message("ERROR", f"❌ Connection failed: {str(e)}")
            self.error = str(e)
            self.update_error_display()
            messagebox.showerror("Connection Error", f"Failed to connect: {str(e)}")
            
    def disconnect(self):
        """Disconnect from WebSocket server"""
        if self.ws:
            self.ws.close()
            self.log_message("INFO", "🔌 Disconnection requested")
            
    def on_open(self, ws):
        """WebSocket connection opened (matching React hook)"""
        self.connected = True
        self.error = None
        self.reconnect_attempts = 0
        self.root.after(0, self.update_connection_ui)
        self.root.after(0, lambda: self.log_message("CONNECTED", "🔗 WebSocket connected to ws://localhost:8000"))
        self.root.after(0, lambda: self.log_message("INFO", "📱 Connected as web client (like React hook)"))
        self.root.after(0, lambda: self.log_message("INFO", "👂 Listening for broadcasted messages..."))
        
    def on_message(self, ws, event_data):
        """WebSocket message received (matching React hook behavior)"""
        try:
            # Parse the message (matching React hook)
            message = json.loads(event_data)
            self.last_message = message
            
            # Log the message once (like React hook console.log)
            self.root.after(0, lambda: self.log_message("RECEIVED", f"📨 Received WebSocket message: {json.dumps(message, indent=2)}"))
            
            # Handle different message types (matching React hook switch statement)
            msg_type = message.get('type', 'unknown')
            
            if msg_type == 'connected_robots':
                if message.get('robots'):
                    self.connected_robots = message['robots']
                    self.root.after(0, lambda: self.log_message("CONNECTED_ROBOTS", f"�� Connected robots updated: {len(self.connected_robots)} robots"))
                    self.root.after(0, self.update_robots_display)
                    
            elif msg_type == 'robot_connected':
                robot_id = message.get('robotId', '')
                if robot_id and robot_id not in self.connected_robots:
                    self.connected_robots.append(robot_id)
                    self.root.after(0, lambda: self.log_message("ROBOT_CONNECTED", f"🤖 New robot connected: {robot_id}"))
                    self.root.after(0, self.update_robots_display)
                    
            elif msg_type == 'robot_disconnected':
                robot_id = message.get('robotId', '')
                if robot_id in self.connected_robots:
                    self.connected_robots.remove(robot_id)
                    self.root.after(0, lambda: self.log_message("ROBOT_DISCONNECTED", f"❌ Robot disconnected: {robot_id}"))
                    self.root.after(0, self.update_robots_display)
                    
            elif msg_type == 'robot_location':
                robot_id = message.get('robotId', 'unknown')
                data = message.get('data', {})
                self.root.after(0, lambda: self.log_message("ROBOT_LOCATION", f"📍 Robot {robot_id} location: {json.dumps(data, indent=2)}"))
                
            elif msg_type == 'robot_status':
                robot_id = message.get('robotId', 'unknown')
                data = message.get('data', {})
                self.root.after(0, lambda: self.log_message("ROBOT_STATUS", f"📊 Robot {robot_id} status: {json.dumps(data, indent=2)}"))
                
            else:
                self.root.after(0, lambda: self.log_message("INFO", f"📨 Other message type '{msg_type}': {json.dumps(message, indent=2)}"))
                
        except json.JSONDecodeError as err:
            self.root.after(0, lambda: self.log_message("ERROR", f"❌ Error parsing WebSocket message: {err}"))
            self.root.after(0, lambda: self.log_message("ERROR", f"❌ Raw data: {event_data}"))
        
    def on_error(self, ws, error):
        """WebSocket error occurred (matching React hook)"""
        self.root.after(0, lambda: self.log_message("ERROR", f"❌ WebSocket error: {error}"))
        self.error = "WebSocket connection error"
        self.root.after(0, self.update_error_display)
        
    def on_close(self, ws, close_status_code, close_msg):
        """WebSocket connection closed (matching React hook with reconnection)"""
        self.connected = False
        self.root.after(0, self.update_connection_ui)
        self.root.after(0, lambda: self.log_message("DISCONNECTED", "🔌 WebSocket disconnected"))
        
        # Attempt to reconnect (matching React hook behavior)
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            delay = min(1000 * (2 ** self.reconnect_attempts), 30000)  # Exponential backoff
            self.root.after(0, lambda: self.log_message("INFO", f"🔄 Attempting to reconnect in {delay}ms (attempt {self.reconnect_attempts})"))
            
            # Schedule reconnection
            self.reconnect_timeout = self.root.after(delay, self.connect)
        else:
            self.error = "Failed to reconnect to WebSocket server"
            self.root.after(0, lambda: self.log_message("ERROR", f"❌ {self.error}"))
            self.root.after(0, self.update_error_display)
        
    def update_connection_ui(self):
        """Update UI based on connection status"""
        if self.connected:
            self.status_label.config(text="Connected", foreground="green")
            self.connect_btn.config(state=tk.DISABLED)
            self.disconnect_btn.config(state=tk.NORMAL)
            # Enable send buttons when connected
            self.send_location_btn.config(state=tk.NORMAL)
            self.send_status_btn.config(state=tk.NORMAL)
            self.send_ping_btn.config(state=tk.NORMAL)
        else:
            self.status_label.config(text="Not Connected", foreground="red")
            self.connect_btn.config(state=tk.NORMAL)
            self.disconnect_btn.config(state=tk.DISABLED)
            # Disable send buttons when disconnected
            self.send_location_btn.config(state=tk.DISABLED)
            self.send_status_btn.config(state=tk.DISABLED)
            self.send_ping_btn.config(state=tk.DISABLED)
            
    def update_error_display(self):
        """Update error display"""
        if self.error:
            self.error_label.config(text=f"Error: {self.error}", foreground="red")
        else:
            self.error_label.config(text="", foreground="red")
            
    def clear_messages(self):
        """Clear the messages log"""
        self.messages_text.config(state=tk.NORMAL)
        self.messages_text.delete(1.0, tk.END)
        self.messages_text.config(state=tk.DISABLED)
        self.message_count = 0
        self.message_count_label.config(text="Messages: 0")

def main():
    root = tk.Tk()
    app = WebSocketReactClient(root)
    
    # Handle window closing
    def on_closing():
        if app.connected and app.ws:
            app.disconnect()
        if app.reconnect_timeout:
            root.after_cancel(app.reconnect_timeout)
        root.destroy()
        
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
