#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import websocket
import ssl
import threading
import json
import time
import math
from datetime import datetime

class WebSocketReactClient:
    def __init__(self, root):
        self.root = root
        self.root.title("WebSocket React Client - sibl.online")
        self.root.geometry("900x900")
        
        # WebSocket connection
        self.ws = None
        self.connected = False
        self.connection_thread = None
        self.server_url = "wss://sibl.online/ws"
        self.connection_verified = False
        self.last_message = None
        self.error = None
        
        # Direction tracking
        self.last_lat = None
        self.last_lng = None
        self.current_direction = 0  # Direction in degrees (0 = North, 90 = East, etc.)
        self.manual_direction_set = False  # Flag to track if direction was manually set
        
        # SSL settings
        self.skip_ssl_verification = tk.BooleanVar(value=True)  # Default to True for development
        
        # Reconnection settings (matching React hook)
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_timeout = None
        
        # Auto-increment settings
        self.auto_increment_active = False
        self.auto_increment_thread = None
        self.increment_step = 0.0001  # Small step for smooth movement
        self.send_interval = 0.1  # Send every 100ms
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(6, weight=1)
        
        # Connection frame
        self.setup_connection_frame(main_frame)
        
        # Send data frame
        self.setup_send_data_frame(main_frame)
        
        # Direction indicator frame
        self.setup_direction_frame(main_frame)
        
        # Auto-increment frame
        self.setup_auto_increment_frame(main_frame)
        
        # Messages log frame
        self.setup_messages_log_frame(main_frame)
        
    def setup_connection_frame(self, parent):
        conn_frame = ttk.LabelFrame(parent, text="Connection Settings", padding="10")
        conn_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        conn_frame.columnconfigure(1, weight=1)
        
        # WebSocket URL input (single field for the full URL)
        ttk.Label(conn_frame, text="WebSocket URL:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=(0, 5))
        self.url_var = tk.StringVar(value="wss://sibl.online/ws")
        self.url_entry = ttk.Entry(conn_frame, textvariable=self.url_var, width=50)
        self.url_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # Update server URL when URL changes
        self.url_var.trace('w', self.update_server_url)
        
        # SSL verification checkbox
        ssl_frame = ttk.Frame(conn_frame)
        ssl_frame.grid(row=1, column=0, columnspan=2, pady=(5, 0))
        
        self.ssl_checkbox = ttk.Checkbutton(
            ssl_frame, 
            text="Skip SSL Certificate Verification (for development)", 
            variable=self.skip_ssl_verification
        )
        self.ssl_checkbox.pack(side=tk.LEFT)
        
        # Connection status
        status_frame = ttk.Frame(conn_frame)
        status_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0))
        
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
        
        # Quick URL buttons
        quick_url_frame = ttk.Frame(conn_frame)
        quick_url_frame.grid(row=3, column=0, columnspan=2, pady=(10, 0))
        
        ttk.Label(quick_url_frame, text="Quick URLs:").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(quick_url_frame, text="sibl.online (WSS)", command=lambda: self.set_url("wss://sibl.online/ws")).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(quick_url_frame, text="Localhost (WS)", command=lambda: self.set_url("ws://localhost:8000")).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(quick_url_frame, text="Localhost 3000", command=lambda: self.set_url("ws://localhost:3000")).pack(side=tk.LEFT, padx=(0, 5))
        
    def update_server_url(self, *args):
        """Update the server URL when URL field changes"""
        self.server_url = self.url_var.get().strip()
            
    def set_url(self, url):
        """Set WebSocket URL"""
        self.url_var.set(url)
        
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
        
        # Icon Type input
        ttk.Label(send_frame, text="Icon Type:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10), pady=(0, 5))
        self.icon_type_var = tk.StringVar(value="A")
        self.icon_type_entry = ttk.Entry(send_frame, textvariable=self.icon_type_var, width=15)
        self.icon_type_entry.grid(row=2, column=1, sticky=tk.W, pady=(0, 5))
        
        # Buttons frame
        buttons_frame = ttk.Frame(send_frame)
        buttons_frame.grid(row=3, column=0, columnspan=2, pady=(10, 0))
        
        # Send location button
        self.send_location_btn = ttk.Button(buttons_frame, text="Send Location", command=self.send_location, state=tk.DISABLED)
        self.send_location_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Send status button
        self.send_status_btn = ttk.Button(buttons_frame, text="Send Status", command=self.send_status, state=tk.DISABLED)
        self.send_status_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Send ping button
        self.send_ping_btn = ttk.Button(buttons_frame, text="Send Ping", command=self.send_ping, state=tk.DISABLED)
        self.send_ping_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Send route waypoints button
        self.send_route_btn = ttk.Button(buttons_frame, text="Send Route", command=self.send_route_waypoints, state=tk.DISABLED)
        self.send_route_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Send location update button
        self.send_location_update_btn = ttk.Button(buttons_frame, text="Send Location Update", command=self.send_location_update, state=tk.DISABLED)
        self.send_location_update_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Send icon pin button
        self.send_icon_pin_btn = ttk.Button(buttons_frame, text="Send Icon Pin", command=self.send_icon_pin, state=tk.DISABLED)
        self.send_icon_pin_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Quick location buttons
        quick_frame = ttk.Frame(send_frame)
        quick_frame.grid(row=4, column=0, columnspan=2, pady=(10, 0))
        
        ttk.Label(quick_frame, text="Quick Locations:").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(quick_frame, text="San Francisco", command=lambda: self.set_location(37.7749, -122.4194)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(quick_frame, text="New York", command=lambda: self.set_location(40.7128, -74.0060)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(quick_frame, text="London", command=lambda: self.set_location(51.5074, -0.1278)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(quick_frame, text="Tokyo", command=lambda: self.set_location(35.6762, 139.6503)).pack(side=tk.LEFT, padx=(0, 5))
        
    def setup_direction_frame(self, parent):
        """Setup direction indicator frame"""
        direction_frame = ttk.LabelFrame(parent, text="Direction Indicator", padding="10")
        direction_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        direction_frame.columnconfigure(1, weight=1)
        
        # Direction display
        ttk.Label(direction_frame, text="Direction:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=(0, 5))
        
        # Canvas for triangular direction indicator
        self.direction_canvas = tk.Canvas(direction_frame, width=100, height=100, bg="white", relief="sunken", bd=2)
        self.direction_canvas.grid(row=0, column=1, sticky=tk.W, pady=(0, 5))
        
        # Direction text display
        self.direction_label = ttk.Label(direction_frame, text="0° (North)", font=("Arial", 12, "bold"))
        self.direction_label.grid(row=0, column=2, sticky=tk.W, padx=(10, 0), pady=(0, 5))
        
        # Direction mode indicator
        self.direction_mode_label = ttk.Label(direction_frame, text="Auto", foreground="blue", font=("Arial", 10))
        self.direction_mode_label.grid(row=0, column=3, sticky=tk.W, padx=(10, 0), pady=(0, 5))
        
        # Direction controls
        controls_frame = ttk.Frame(direction_frame)
        controls_frame.grid(row=1, column=0, columnspan=4, pady=(10, 0))
        
        ttk.Label(controls_frame, text="Manual Direction:").pack(side=tk.LEFT, padx=(0, 10))
        self.manual_direction_var = tk.StringVar(value="0")
        direction_entry = ttk.Entry(controls_frame, textvariable=self.manual_direction_var, width=10)
        direction_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(controls_frame, text="Set Direction", command=self.set_manual_direction).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(controls_frame, text="Reset", command=self.reset_direction).pack(side=tk.LEFT, padx=(0, 10))
        
        # Initialize direction indicator
        self.update_direction_indicator()
        self.update_direction_label()
        
    def setup_auto_increment_frame(self, parent):
        auto_frame = ttk.LabelFrame(parent, text="Auto-Increment Latitude (Hold to Move North)", padding="10")
        auto_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        auto_frame.columnconfigure(1, weight=1)
        
        # Settings frame
        settings_frame = ttk.Frame(auto_frame)
        settings_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Increment step setting
        ttk.Label(settings_frame, text="Step Size:").pack(side=tk.LEFT, padx=(0, 5))
        self.step_var = tk.StringVar(value="0.0001")
        step_entry = ttk.Entry(settings_frame, textvariable=self.step_var, width=10)
        step_entry.pack(side=tk.LEFT, padx=(0, 20))
        
        # Send interval setting
        ttk.Label(settings_frame, text="Send Interval (ms):").pack(side=tk.LEFT, padx=(0, 5))
        self.interval_var = tk.StringVar(value="100")
        interval_entry = ttk.Entry(settings_frame, textvariable=self.interval_var, width=10)
        interval_entry.pack(side=tk.LEFT, padx=(0, 20))
        
        # Control buttons frame
        control_frame = ttk.Frame(auto_frame)
        control_frame.grid(row=1, column=0, columnspan=2, pady=(10, 0))
        
        # Hold to increment button
        self.hold_btn = ttk.Button(control_frame, text="Hold to Move North", command=self.start_auto_increment, state=tk.DISABLED)
        self.hold_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Stop button
        self.stop_btn = ttk.Button(control_frame, text="Stop", command=self.stop_auto_increment, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Status label
        self.auto_status_label = ttk.Label(control_frame, text="Stopped", foreground="red")
        self.auto_status_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # Bind mouse events for hold functionality
        self.hold_btn.bind("<Button-1>", self.on_hold_start)
        self.hold_btn.bind("<ButtonRelease-1>", self.on_hold_stop)
        
    def setup_messages_log_frame(self, parent):
        log_frame = ttk.LabelFrame(parent, text="WebSocket Messages (React Hook Behavior)", padding="10")
        log_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
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
        
    def calculate_direction(self, lat1, lng1, lat2, lng2):
        """Calculate direction between two points in degrees (0 = North, 90 = East)"""
        if lat1 is None or lng1 is None or lat2 is None or lng2 is None:
            return self.current_direction
            
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lng = math.radians(lng2 - lng1)
        
        # Calculate bearing
        y = math.sin(delta_lng) * math.cos(lat2_rad)
        x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lng)
        
        bearing = math.atan2(y, x)
        bearing_degrees = math.degrees(bearing)
        
        # Normalize to 0-360 degrees
        bearing_degrees = (bearing_degrees + 360) % 360
        
        return bearing_degrees
        
    def update_direction_indicator(self):
        """Update the triangular direction indicator on canvas"""
        self.direction_canvas.delete("all")
        
        # Canvas center
        center_x, center_y = 50, 50
        
        # Triangle size
        triangle_size = 25
        
        # Convert direction to radians (0 degrees = North, but canvas 0 degrees = East)
        # So we need to adjust: canvas_angle = (direction - 90) % 360
        canvas_angle = math.radians((self.current_direction - 90) % 360)
        
        # Draw center pin first (larger and more prominent)
        pin_size = 6
        self.direction_canvas.create_oval(center_x-pin_size, center_y-pin_size, center_x+pin_size, center_y+pin_size, fill="black", outline="darkgray", width=2)
        
        # Calculate triangle points starting from the center pin
        # Point 1: front of triangle (pointing in direction) - starts from center
        x1 = center_x + triangle_size * math.cos(canvas_angle)
        y1 = center_y + triangle_size * math.sin(canvas_angle)
        
        # Point 2: back left of triangle - starts from center
        x2 = center_x + (triangle_size * 0.7) * math.cos(canvas_angle + math.radians(120))
        y2 = center_y + (triangle_size * 0.7) * math.sin(canvas_angle + math.radians(120))
        
        # Point 3: back right of triangle - starts from center
        x3 = center_x + (triangle_size * 0.7) * math.cos(canvas_angle - math.radians(120))
        y3 = center_y + (triangle_size * 0.7) * math.sin(canvas_angle - math.radians(120))
        
        # Draw triangle starting from center pin
        self.direction_canvas.create_polygon(center_x, center_y, x1, y1, x2, y2, x3, y3, fill="red", outline="darkred", width=2)
        
        # Draw compass directions
        self.direction_canvas.create_text(50, 10, text="N", font=("Arial", 10, "bold"))
        self.direction_canvas.create_text(90, 50, text="E", font=("Arial", 10, "bold"))
        self.direction_canvas.create_text(50, 90, text="S", font=("Arial", 10, "bold"))
        self.direction_canvas.create_text(10, 50, text="W", font=("Arial", 10, "bold"))
        
    def set_manual_direction(self):
        """Set direction manually from input field"""
        try:
            direction = float(self.manual_direction_var.get())
            self.current_direction = direction % 360
            self.manual_direction_set = True  # Mark as manually set
            self.update_direction_indicator()
            self.update_direction_label()
            self.log_message("INFO", f"🧭 Direction manually set to {self.current_direction:.1f}° (will not auto-calculate)")
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid number for direction")
            
    def reset_direction(self):
        """Reset direction to 0 (North)"""
        self.current_direction = 0
        self.manual_direction_set = False  # Reset manual flag
        self.last_lat = None
        self.last_lng = None
        self.update_direction_indicator()
        self.update_direction_label()
        self.log_message("INFO", "🧭 Direction reset to North (0°) - auto-calculation enabled")
        
    def update_direction_label(self):
        """Update the direction text label and mode indicator"""
        direction_names = {
            0: "North", 45: "Northeast", 90: "East", 135: "Southeast",
            180: "South", 225: "Southwest", 270: "West", 315: "Northwest"
        }
        
        # Find closest cardinal direction
        closest_direction = min(direction_names.keys(), key=lambda x: abs(x - self.current_direction))
        direction_name = direction_names[closest_direction]
        
        self.direction_label.config(text=f"{self.current_direction:.1f}° ({direction_name})")
        
        # Update mode indicator
        if self.manual_direction_set:
            self.direction_mode_label.config(text="Manual", foreground="red")
        else:
            self.direction_mode_label.config(text="Auto", foreground="blue")
        
    def on_hold_start(self, event):
        """Start auto-increment when button is pressed"""
        self.start_auto_increment()
        
    def on_hold_stop(self, event):
        """Stop auto-increment when button is released"""
        self.stop_auto_increment()
        
    def start_auto_increment(self):
        """Start auto-incrementing latitude"""
        if not self.connected:
            self.log_message("WARNING", "⚠️ Not connected - cannot start auto-increment")
            return
            
        if self.auto_increment_active:
            return
            
        try:
            self.increment_step = float(self.step_var.get())
            self.send_interval = float(self.interval_var.get()) / 1000.0  # Convert to seconds
        except ValueError:
            self.log_message("ERROR", "❌ Invalid step size or interval")
            return
            
        self.auto_increment_active = True
        self.auto_status_label.config(text="Moving North", foreground="green")
        self.hold_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
        self.log_message("INFO", f"🚀 Started auto-increment: step={self.increment_step}, interval={self.send_interval}s")
        
        # Start auto-increment thread
        self.auto_increment_thread = threading.Thread(target=self.auto_increment_loop, daemon=True)
        self.auto_increment_thread.start()
        
    def stop_auto_increment(self):
        """Stop auto-incrementing latitude"""
        if not self.auto_increment_active:
            return
            
        self.auto_increment_active = False
        self.auto_status_label.config(text="Stopped", foreground="red")
        self.hold_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
        self.log_message("INFO", "🛑 Stopped auto-increment")
        
    def auto_increment_loop(self):
        """Auto-increment loop that runs in a separate thread"""
        while self.auto_increment_active and self.connected:
            try:
                # Get current latitude
                current_lat = float(self.lat_var.get())
                
                # Increment latitude
                new_lat = current_lat + self.increment_step
                
                # Update the UI
                self.root.after(0, lambda: self.lat_var.set(f"{new_lat:.6f}"))
                
                # Send location update
                self.send_location_auto()
                
                # Wait for next iteration
                time.sleep(self.send_interval)
                
            except ValueError:
                self.log_message("ERROR", "❌ Invalid latitude value")
                break
            except Exception as e:
                self.log_message("ERROR", f"❌ Auto-increment error: {e}")
                break
                
        # Clean up when loop ends
        self.root.after(0, self.stop_auto_increment)
        
    def send_location_auto(self):
        """Send location data automatically (without logging)"""
        try:
            lat = float(self.lat_var.get())
            lng = float(self.lng_var.get())
            
            # Calculate direction only if not manually set and we have previous location
            if not self.manual_direction_set and self.last_lat is not None and self.last_lng is not None:
                new_direction = self.calculate_direction(self.last_lat, self.last_lng, lat, lng)
                self.current_direction = new_direction
                self.root.after(0, self.update_direction_indicator)
                self.root.after(0, self.update_direction_label)
            
            location_message = {
                "type": "location",
                "data": {
                    "lat": lat,
                    "lng": lng,
                    "direction": self.current_direction,
                    "timestamp": datetime.now().isoformat() + "Z"
                }
            }
            
            if self.ws and self.connected:
                self.ws.send(json.dumps(location_message))
                
            # Store current location for next direction calculation
            self.last_lat = lat
            self.last_lng = lng
                
        except ValueError:
            pass  # Silently handle invalid values during auto-increment
        except Exception as e:
            self.root.after(0, lambda: self.log_message("ERROR", f"❌ Auto-send error: {e}"))
        
    def set_location(self, lat, lng):
        """Set latitude and longitude values and calculate direction"""
        # Calculate direction only if not manually set and we have previous location
        if not self.manual_direction_set and self.last_lat is not None and self.last_lng is not None:
            new_direction = self.calculate_direction(self.last_lat, self.last_lng, lat, lng)
            self.current_direction = new_direction
            self.update_direction_indicator()
            self.update_direction_label()
            self.log_message("INFO", f"🧭 Direction auto-calculated: {self.current_direction:.1f}°")
        
        # Update location
        self.lat_var.set(str(lat))
        self.lng_var.set(str(lng))
        
        # Store current location for next direction calculation
        self.last_lat = lat
        self.last_lng = lng
        
    def send_location(self):
        """Send location data to WebSocket server"""
        try:
            lat = float(self.lat_var.get())
            lng = float(self.lng_var.get())
            
            # Calculate direction only if not manually set and we have previous location
            if not self.manual_direction_set and self.last_lat is not None and self.last_lng is not None:
                new_direction = self.calculate_direction(self.last_lat, self.last_lng, lat, lng)
                self.current_direction = new_direction
                self.update_direction_indicator()
                self.update_direction_label()
                self.log_message("INFO", f"🧭 Direction auto-calculated: {self.current_direction:.1f}°")
            
            location_message = {
                "type": "location",
                "data": {
                    "lat": lat,
                    "lng": lng,
                    "direction": self.current_direction,
                    "timestamp": datetime.now().isoformat() + "Z"
                }
            }
            
            self.send_message(location_message)
            direction_source = "manual" if self.manual_direction_set else "auto-calculated"
            self.log_message("SENT", f"📍 Sent location: {lat}, {lng} (direction: {self.current_direction:.1f}° - {direction_source})")
            
            # Store current location for next direction calculation
            self.last_lat = lat
            self.last_lng = lng
            
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
        self.log_message("SENT", f"🏓 Sent ping")
        
    def send_route_waypoints(self):
        """Send route waypoints to WebSocket server"""
        route_message = {
            "type": "route_waypoints",
            "action": "send_route",
            "data": {
                "waypoints": [
                    { "lat": 37.7749, "lng": -122.4194 },
                    { "lat": 37.7755, "lng": -122.4200 },
                    { "lat": 37.7760, "lng": -122.4190 },
                    { "lat": 37.7750, "lng": -122.4180 },
                    { "lat": 37.7740, "lng": -122.4185 },
                    { "lat": 37.7735, "lng": -122.4195 },
                    { "lat": 37.7745, "lng": -122.4205 },
                    { "lat": 37.7755, "lng": -122.4210 },
                    { "lat": 37.7765, "lng": -122.4205 },
                    { "lat": 37.7770, "lng": -122.4195 }
                ],
                "routeName": "Robot Generated Route",
                "routeType": "delivery",
                "totalStops": 10,
                "startLocation": "Warehouse",
                "endLocation": "Final Destination"
            },
            "timestamp": datetime.now().isoformat() + "Z",
            "source": "robot"
        }
        
        self.send_message(route_message)
        self.log_message("SENT", f"🗺️ Sent route waypoints (10 stops)")
        
    def send_location_update(self):
        """Send location update in the specified format using current input values"""
        try:
            # Get values from input fields
            lat = float(self.lat_var.get())
            lng = float(self.lng_var.get())
            
            # Calculate direction only if not manually set and we have previous location
            if not self.manual_direction_set and self.last_lat is not None and self.last_lng is not None:
                new_direction = self.calculate_direction(self.last_lat, self.last_lng, lat, lng)
                self.current_direction = new_direction
                self.update_direction_indicator()
                self.update_direction_label()
                self.log_message("INFO", f"🧭 Direction auto-calculated: {self.current_direction:.1f}°")
            
            # Create location update message using current input values
            location_update_message = {
                "type": "location_track",
                "data": {
                    "lat": lat,                    # From latitude input field
                    "lng": lng,                    # From longitude input field
                    "direction": self.current_direction,  # Current direction value
                    "timestamp": datetime.now().isoformat() + "Z"
                }
            }
            
            self.send_message(location_update_message)
            direction_source = "manual" if self.manual_direction_set else "auto-calculated"
            self.log_message("SENT", f"📍 Sent location update: lat={lat}, lng={lng}, direction={self.current_direction:.1f}° ({direction_source})")
            
            # Store current location for next direction calculation
            self.last_lat = lat
            self.last_lng = lng
            
        except ValueError as e:
            self.log_message("ERROR", f"❌ Invalid input values - lat: '{self.lat_var.get()}', lng: '{self.lng_var.get()}'")
            messagebox.showerror("Invalid Input", "Please enter valid latitude and longitude numbers")
        except Exception as e:
            self.log_message("ERROR", f"❌ Error sending location update: {e}")
            messagebox.showerror("Error", f"Failed to send location update: {e}")
            
    def send_icon_pin(self):
        """Send icon pin message using current input values"""
        try:
            # Get values from input fields
            lat = float(self.lat_var.get())
            lng = float(self.lng_var.get())
            icon_type = self.icon_type_var.get().strip()
            
            # Validate icon type is not empty
            if not icon_type:
                self.log_message("ERROR", "❌ Icon Type cannot be empty")
                messagebox.showerror("Invalid Input", "Please enter an icon type")
                return
            
            # Create icon pin message using current input values
            icon_pin_message = {
                "type": "icon_pin",
                "data": {
                    "lat": lat,                    # From latitude input field
                    "lng": lng,                    # From longitude input field
                    "type": icon_type          # From icon type input field
                }
            }
            
            self.send_message(icon_pin_message)
            self.log_message("SENT", f"📍 Sent icon pin: lat={lat}, lng={lng}, iconType={icon_type}")
            
        except ValueError as e:
            self.log_message("ERROR", f"❌ Invalid input values - lat: '{self.lat_var.get()}', lng: '{self.lng_var.get()}'")
            messagebox.showerror("Invalid Input", "Please enter valid latitude and longitude numbers")
        except Exception as e:
            self.log_message("ERROR", f"❌ Error sending icon pin: {e}")
            messagebox.showerror("Error", f"Failed to send icon pin: {e}")
        
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
        
        
    def connect(self):
        """Connect to WebSocket server (matching React hook behavior)"""
        # Update server URL before connecting
        self.update_server_url()
        
        self.log_message("DIAGNOSTIC", f"🔍 Connecting to: {self.server_url}")
        self.log_message("INFO", "📡 Starting WebSocket connection (React hook behavior)...")
        self.log_message("INFO", "🌐 This connects as a web client, not a robot")
        self.log_message("INFO", "📱 Will receive broadcasted messages from the server")
        
        try:
            # Create SSL context for WSS connections
            ssl_context = None
            if self.server_url.startswith('wss://'):
                ssl_context = ssl.create_default_context()
                if self.skip_ssl_verification.get():
                    self.log_message("WARNING", "⚠️ SSL certificate verification disabled (development mode)")
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE
                else:
                    self.log_message("INFO", "🔒 SSL certificate verification enabled")
            
            # Create WebSocket connection
            self.ws = websocket.WebSocketApp(
                self.server_url,
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )
            
            # Start connection in a separate thread with SSL context
            self.connection_thread = threading.Thread(
                target=lambda: self.ws.run_forever(sslopt={"context": ssl_context} if ssl_context else {})
            )
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
        self.root.after(0, lambda: self.log_message("CONNECTED", f"🔗 WebSocket connected to {self.server_url}"))
        self.root.after(0, lambda: self.log_message("INFO", "🌐 Connected as web client (like React hook)"))
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
            
            if msg_type == 'robot_location':
                robot_id = message.get('robotId', 'unknown')
                data = message.get('data', {})
                self.root.after(0, lambda: self.log_message("ROBOT_LOCATION", f"📍 Robot {robot_id} location: {json.dumps(data, indent=2)}"))
            elif msg_type == 'robot_status':
                robot_id = message.get('robotId', 'unknown')
                data = message.get('data', {})
                self.root.after(0, lambda: self.log_message("ROBOT_STATUS", f"📊 Robot {robot_id} status: {json.dumps(data, indent=2)}"))  
            else:
                self.root.after(0, lambda: self.log_message("INFO", f"📨 Other message type '{msg_type}': {json.dumps(message, indent=2)}"))
                if message.get('command') == 'sendlocation':
                    self.send_location()
                
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
        
        # Stop auto-increment if running
        self.root.after(0, self.stop_auto_increment)
        
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
            self.send_route_btn.config(state=tk.NORMAL)
            self.send_location_update_btn.config(state=tk.NORMAL)
            self.send_icon_pin_btn.config(state=tk.NORMAL)
            self.hold_btn.config(state=tk.NORMAL)
        else:
            self.status_label.config(text="Not Connected", foreground="red")
            self.connect_btn.config(state=tk.NORMAL)
            self.disconnect_btn.config(state=tk.DISABLED)
            # Disable send buttons when disconnected
            self.send_location_btn.config(state=tk.DISABLED)
            self.send_status_btn.config(state=tk.DISABLED)
            self.send_ping_btn.config(state=tk.DISABLED)
            self.send_route_btn.config(state=tk.DISABLED)
            self.send_location_update_btn.config(state=tk.DISABLED)
            self.send_icon_pin_btn.config(state=tk.DISABLED)
            self.hold_btn.config(state=tk.DISABLED)
            # Stop auto-increment if running
            self.stop_auto_increment()
            
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
        if app.auto_increment_active:
            app.stop_auto_increment()
        if app.connected and app.ws:
            app.disconnect()
        if app.reconnect_timeout:
            root.after_cancel(app.reconnect_timeout)
        root.destroy()
        
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
