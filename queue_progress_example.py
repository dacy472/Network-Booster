import tkinter as tk
from tkinter import ttk
import threading
import queue
import time
import random

class QueueProgressApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Queue Progress Example")
        self.root.geometry("400x200")
        
        # 1. Create a thread-safe queue for progress updates
        self.progress_queue = queue.Queue()
        
        # Tracking variables
        self.total_bytes = 100 * 1024 * 1024  # Simulating a 100 MB file
        self.downloaded_bytes = 0
        self.last_update_time = 0
        self.bytes_since_last_update = 0
        
        # UI Elements
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(root, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(pady=20, padx=20, fill="x")
        
        self.status_label = tk.Label(root, text="Ready to download", font=("Arial", 10))
        self.status_label.pack(pady=5)
        
        self.speed_label = tk.Label(root, text="", font=("Arial", 10, "bold"), fg="green")
        self.speed_label.pack(pady=5)
        
        self.start_button = tk.Button(root, text="Start Simulated Download", command=self.start_download)
        self.start_button.pack(pady=10)

    def start_download(self):
        self.start_button.config(state=tk.DISABLED)
        
        # Reset counters
        self.downloaded_bytes = 0
        self.bytes_since_last_update = 0
        self.last_update_time = time.time()
        self.progress_var.set(0)
        
        # Start the background download threads
        num_threads = 4
        bytes_per_thread = self.total_bytes // num_threads
        for i in range(num_threads):
            threading.Thread(target=self.download_chunk_worker, args=(bytes_per_thread, i), daemon=True).start()
            
        # 3. Start the queue consumer loop in the main GUI thread
        # This will run process_queue every 100 milliseconds
        self.root.after(100, self.process_queue)

    def download_chunk_worker(self, total_bytes_to_download, thread_id):
        """Simulates a background thread downloading a chunk and writing to disk."""
        bytes_downloaded = 0
        chunk_size = 8192
        
        while bytes_downloaded < total_bytes_to_download:
            # Simulate the network delay for downloading a chunk
            time.sleep(random.uniform(0.001, 0.005)) 
            
            # We ensure we don't write more bytes than we need to
            actual_chunk_len = min(chunk_size, total_bytes_to_download - bytes_downloaded)
            
            # (In a real app, you would do outfile.write(data) here)
            bytes_downloaded += actual_chunk_len
            
            # 2. Thread-safe: Put the downloaded byte count into the queue
            self.progress_queue.put(actual_chunk_len)
            

    def process_queue(self):
        """Runs in the main Tkinter thread, processing the queue and updating the UI."""
        try:
            # Process everything currently in the queue without blocking.
            # We loop until the queue is empty.
            while True:
                # get_nowait() throws queue.Empty if the queue is currently empty
                chunk_bytes = self.progress_queue.get_nowait()
                
                # Tally up the total downloaded bytes
                self.downloaded_bytes += chunk_bytes
                self.bytes_since_last_update += chunk_bytes
                
                # Tell the queue that the item was processed
                self.progress_queue.task_done()
        except queue.Empty:
            # The queue is currently empty, which is completely fine.
            # We break out of the loop and move on to updating the UI.
            pass
            
        # A) Calculate percentage and smoothly update the Progress Bar
        percentage = (self.downloaded_bytes / self.total_bytes) * 100
        self.progress_var.set(percentage)
        
        mb_downloaded = self.downloaded_bytes / (1024 * 1024)
        mb_total = self.total_bytes / (1024 * 1024)
        self.status_label.config(text=f"Downloaded: {mb_downloaded:.2f} MB / {mb_total:.2f} MB ({percentage:.1f}%)")
        
        # B) Calculate Current Download Speed (MB/s)
        current_time = time.time()
        time_diff = current_time - self.last_update_time
        
        # Update the speed label every ~0.5 seconds to make the text readable
        if time_diff >= 0.5:
            # Bytes per second = bytes / time
            bytes_per_sec = self.bytes_since_last_update / time_diff
            mb_per_sec = bytes_per_sec / (1024 * 1024)
            
            self.speed_label.config(text=f"Speed: {mb_per_sec:.2f} MB/s")
            
            # Reset the speed counters for the next speed calculation interval
            self.bytes_since_last_update = 0
            self.last_update_time = current_time

        # C) Check if we are done, otherwise loop again
        if self.downloaded_bytes < self.total_bytes:
            # Re-queue this function to run again in 100 milliseconds
            self.root.after(100, self.process_queue)
        else:
            self.status_label.config(text="Download Complete!")
            self.speed_label.config(text="Speed: 0.00 MB/s")
            self.start_button.config(state=tk.NORMAL)


if __name__ == "__main__":
    root = tk.Tk()
    app = QueueProgressApp(root)
    root.mainloop()
