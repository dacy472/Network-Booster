import queue
import threading
import time
import random
import customtkinter as ctk

# Matplotlib integration
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class RealTimeGraphApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Real-Time Network Throughput Graph")
        self.geometry("800x500")
        
        # This queue mocks your download threads sending chunks
        self.progress_queue = queue.Queue()
        
        # Data storage for the graph
        self.x_data = []
        self.y_data = []
        self.start_time = time.time()
        self.bytes_since_last_update = 0
        self.last_update_time = time.time()
        
        # ==========================================
        # 1. Setup UI
        # ==========================================
        self.title_label = ctk.CTkLabel(self, text="Live Download Speed (MB/s)", font=ctk.CTkFont(size=22, weight="bold"))
        self.title_label.pack(pady=(20, 10))
        
        # ==========================================
        # 2. Setup Matplotlib Figure for Dark Mode
        # ==========================================
        self.figure = Figure(figsize=(8, 4), dpi=100)
        # Set figure background to match CustomTkinter's dark mode
        self.figure.patch.set_facecolor('#2b2b2b') 
        
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor('#2b2b2b')
        self.ax.tick_params(colors='white')
        self.ax.xaxis.label.set_color('white')
        self.ax.yaxis.label.set_color('white')
        
        # Whiten the borders
        for spine in self.ax.spines.values():
            spine.set_color('white')
            
        self.ax.set_xlabel("Time (Seconds)")
        self.ax.set_ylabel("Speed (MB/s)")
        self.ax.grid(True, linestyle='--', alpha=0.3, color='white')
        
        # Initialize an empty line with neon cyan color
        self.line, = self.ax.plot([], [], color="#00e5ff", linewidth=2)
        
        # ==========================================
        # 3. Embed Matplotlib into Tkinter
        # ==========================================
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Start background thread to mock downloads
        self.is_downloading = True
        threading.Thread(target=self.mock_download_worker, daemon=True).start()
        
        # Start the Tkinter UI polling loop (checks queue every 100ms)
        self.after(100, self.process_queue)
        
    def mock_download_worker(self):
        """Mocks a download thread rapidly firing 8192 byte chunks into the queue."""
        while self.is_downloading:
            # Simulate variable network speeds
            time.sleep(random.uniform(0.001, 0.05))
            # Push 8KB chunk to queue (same as your downloader)
            self.progress_queue.put(8192)
            
    def process_queue(self):
        """Drains the queue and plots a new point on the graph every 500ms."""
        # 1. Drain the queue completely
        while not self.progress_queue.empty():
            try:
                chunk = self.progress_queue.get_nowait()
                self.bytes_since_last_update += chunk
                self.progress_queue.task_done()
            except queue.Empty:
                break
                
        # 2. Check if 500ms has elapsed to plot a new point
        curr_time = time.time()
        dt = curr_time - self.last_update_time
        
        if dt >= 0.5:
            # Calculate MB/s
            speed_mbps = (self.bytes_since_last_update / dt) / (1024 * 1024)
            elapsed_seconds = curr_time - self.start_time
            
            # Append data
            self.x_data.append(elapsed_seconds)
            self.y_data.append(speed_mbps)
            
            # Keep only the last 60 seconds (120 points at 500ms intervals) to avoid memory leaks/lag
            if len(self.x_data) > 120:
                self.x_data.pop(0)
                self.y_data.pop(0)
                
            # Update graph line data natively (much faster than clearing and redrawing the whole plot)
            self.line.set_data(self.x_data, self.y_data)
            
            # Dynamically scroll the X-axis as time moves forward
            self.ax.set_xlim(max(0, elapsed_seconds - 60), max(10, elapsed_seconds + 2))
            
            # Auto-scale Y-axis if speed exceeds default limits
            current_max_y = max(self.y_data) if self.y_data else 10
            self.ax.set_ylim(0, max(10, current_max_y * 1.2))
            
            # Render changes to the Tkinter canvas
            self.canvas.draw()
            
            # Reset speed counter for the next interval
            self.bytes_since_last_update = 0
            self.last_update_time = curr_time
            
        # Re-run loop indefinitely
        self.after(100, self.process_queue)
        
if __name__ == "__main__":
    app = RealTimeGraphApp()
    app.mainloop()
