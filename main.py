import os
import sys
import time
import subprocess
import ctypes
import threading
import queue
import tempfile
import shutil
import json
import concurrent.futures
import requests
from requests.adapters import HTTPAdapter

try:
    import customtkinter as ctk
    from tkinter import filedialog
except ImportError:
    print("Error: 'customtkinter' is not installed. Please install it using: pip install customtkinter")
    sys.exit(1)

# ==========================================
# 1. Network Binder Component
# ==========================================
class BoundHTTPAdapter(HTTPAdapter):
    """Binds outbound traffic to a specific local IP address interface."""
    def __init__(self, source_ip, *args, **kwargs):
        self.source_ip = source_ip
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        if self.source_ip:
            # Bind to specific IP, letting OS choose the port (0)
            pool_kwargs['source_address'] = (self.source_ip, 0)
        super().init_poolmanager(connections, maxsize, block=block, **pool_kwargs)


# ==========================================
# 2. Print Redirection Component
# ==========================================
class PrintRedirector:
    """Redirects sys.stdout and sys.stderr natively into the GUI Log Queue."""
    def __init__(self, log_queue, prefix=""):
        self.log_queue = log_queue
        self.prefix = prefix
        self.terminal = sys.stdout

    def write(self, message):
        if message.strip():
            timestamp = time.strftime("%H:%M:%S")
            self.log_queue.put(f"[{timestamp}] {self.prefix}{message.strip()}\n")
        if hasattr(self.terminal, 'write'):
            self.terminal.write(message)

    def flush(self):
        if hasattr(self.terminal, 'flush'):
            self.terminal.flush()


# ==========================================
# 3. Main GUI and Controller Component
# ==========================================
# Setup modern UI theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class NetworkBoosterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Network Booster - Pro Downloader")
        self.geometry("750x650")
        self.minsize(700, 600)

        # Queues for thread-safe UI updates
        self.progress_queue = queue.Queue()
        self.log_queue = queue.Queue()

        # Download tracking states
        self.is_downloading = False
        self.total_size = 0
        self.downloaded_bytes = 0
        self.bytes_since_last_update = 0
        self.last_update_time = 0
        
        self.chunk_states = {}
        self.state_file = None
        self.state_changed = False
        self.last_save_time = 0

        self.setup_ui()
        
        # Globally redirect all print() statements to the GUI live console
        sys.stdout = PrintRedirector(self.log_queue, prefix="[SYS] ")
        sys.stderr = PrintRedirector(self.log_queue, prefix="[ERR] ")
        
        # Start the background loop that continuously checks queues and updates UI
        self.after(100, self.process_queues)

    def setup_ui(self):
        # Grid weight for window responsiveness
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1) # Makes the bottom frame (console) expand dynamically

        # 1. Header
        self.title_label = ctk.CTkLabel(self, text="Network Booster", font=ctk.CTkFont(size=26, weight="bold"))
        self.title_label.grid(row=0, column=0, pady=(15, 10), sticky="ew")

        # 2. Configuration Frame (Labeled Settings Group)
        self.config_frame = ctk.CTkFrame(self)
        self.config_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.config_frame.grid_columnconfigure(1, weight=1)

        self.config_title = ctk.CTkLabel(self.config_frame, text="Download Settings", font=ctk.CTkFont(weight="bold", size=14))
        self.config_title.grid(row=0, column=0, columnspan=2, pady=(10, 5), sticky="w", padx=10)

        # URL Input
        self.url_label = ctk.CTkLabel(self.config_frame, text="File URL:", width=80, anchor="w")
        self.url_label.grid(row=1, column=0, padx=(10, 5), pady=5, sticky="w")
        self.url_entry = ctk.CTkEntry(self.config_frame, placeholder_text="https://example.com/large_file.zip")
        self.url_entry.grid(row=1, column=1, padx=(0, 10), pady=5, sticky="ew")

        # Bind IP Input
        self.bind_label = ctk.CTkLabel(self.config_frame, text="Bind IP:", width=80, anchor="w")
        self.bind_label.grid(row=2, column=0, padx=(10, 5), pady=5, sticky="w")
        self.bind_entry = ctk.CTkEntry(self.config_frame, placeholder_text="e.g. 192.168.1.5, 192.168.1.10 (Comma separated)")
        self.bind_entry.grid(row=2, column=1, padx=(0, 10), pady=5, sticky="ew")

        # Threads Slider
        self.threads_label = ctk.CTkLabel(self.config_frame, text="Threads:", width=80, anchor="w")
        self.threads_label.grid(row=3, column=0, padx=(10, 5), pady=(5, 15), sticky="w")
        
        self.slider_frame = ctk.CTkFrame(self.config_frame, fg_color="transparent")
        self.slider_frame.grid(row=3, column=1, padx=(0, 10), pady=(5, 15), sticky="ew")
        self.slider_frame.grid_columnconfigure(0, weight=1)
        
        self.thread_slider = ctk.CTkSlider(self.slider_frame, from_=1, to=16, number_of_steps=15, command=self.update_thread_label)
        self.thread_slider.set(8)
        self.thread_slider.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        self.thread_count_label = ctk.CTkLabel(self.slider_frame, text="8", font=ctk.CTkFont(weight="bold"))
        self.thread_count_label.grid(row=0, column=1)

        # 3. Action Buttons (Side-by-side in center)
        self.action_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.action_frame.grid(row=2, column=0, pady=15)
        
        self.optimize_button = ctk.CTkButton(self.action_frame, text="DEEP OPTIMIZE", fg_color="#ff5555", hover_color="#cc0000", font=ctk.CTkFont(size=14, weight="bold"), height=40, command=self.deep_system_optimize)
        self.optimize_button.pack(side="left", padx=10)

        self.start_button = ctk.CTkButton(self.action_frame, text="ACTIVATE BOOST", font=ctk.CTkFont(size=14, weight="bold"), height=40, command=self.start_download)
        self.start_button.pack(side="left", padx=10)

        # 4. Progress and Live Feed Frame
        self.bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_frame.grid(row=3, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.bottom_frame.grid_columnconfigure(0, weight=1)
        self.bottom_frame.grid_rowconfigure(3, weight=1) # Allow console textbox to expand vertically

        # Progress Bar & Stats
        self.progress_bar = ctk.CTkProgressBar(self.bottom_frame, height=15, progress_color="#00e5ff") # Neon blue progress bar
        self.progress_bar.set(0)
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        self.stats_frame = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
        self.stats_frame.grid(row=1, column=0, sticky="ew")
        self.stats_frame.grid_columnconfigure(1, weight=1)
        
        self.status_label = ctk.CTkLabel(self.stats_frame, text="Ready", font=ctk.CTkFont(size=13))
        self.status_label.grid(row=0, column=0, sticky="w")
        self.speed_label = ctk.CTkLabel(self.stats_frame, text="0.00 MB/s", font=ctk.CTkFont(size=13, weight="bold"), text_color="#55ff55")
        self.speed_label.grid(row=0, column=1, sticky="e")

        # Live Logs
        self.log_label = ctk.CTkLabel(self.bottom_frame, text="Live System Console:", font=ctk.CTkFont(weight="bold"))
        self.log_label.grid(row=2, column=0, sticky="w", pady=(10, 0))
        
        self.log_box = ctk.CTkTextbox(
            self.bottom_frame, state="disabled", 
            fg_color="#0c0c0c", text_color="#00e5ff",
            font=ctk.CTkFont(family="Consolas", size=13)
        )
        self.log_box.grid(row=3, column=0, sticky="nsew", pady=(5, 0))

    def update_thread_label(self, value):
        self.thread_count_label.configure(text=str(int(value)))

    def log_message(self, msg):
        """Thread-safe logging helper."""
        timestamp = time.strftime("%H:%M:%S")
        self.log_queue.put(f"[{timestamp}] {msg}\n")

    def process_queues(self):
        """Main UI thread processor for queues."""
        # 1. Process Logs Queue
        logs_to_write = ""
        while not self.log_queue.empty():
            try:
                logs_to_write += self.log_queue.get_nowait()
                self.log_queue.task_done()
            except queue.Empty:
                break
        
        if logs_to_write:
            self.log_box.configure(state="normal")
            self.log_box.insert("end", logs_to_write)
            self.log_box.see("end")  # Auto-scroll to bottom
            self.log_box.configure(state="disabled")

        # 2. Process Progress Queue
        if self.is_downloading:
            while not self.progress_queue.empty():
                try:
                    index, chunk_bytes = self.progress_queue.get_nowait()
                    self.downloaded_bytes += chunk_bytes
                    self.bytes_since_last_update += chunk_bytes
                    
                    if index is not None:
                        self.chunk_states[str(index)]["current_start"] += chunk_bytes
                        self.state_changed = True
                        
                    self.progress_queue.task_done()
                except queue.Empty:
                    break

            # 3. Save State to JSON (Throttled to every 2 seconds)
            curr_time = time.time()
            if self.state_changed and self.state_file and (curr_time - self.last_save_time > 2.0):
                try:
                    with open(self.state_file, 'w') as f:
                        json.dump(self.chunk_states, f)
                    self.last_save_time = curr_time
                    self.state_changed = False
                except Exception as e:
                    pass

            # Update Progress UI
            if self.total_size > 0:
                progress = min(1.0, self.downloaded_bytes / self.total_size)
                self.progress_bar.set(progress)
                
                mb_down = self.downloaded_bytes / (1024*1024)
                mb_tot = self.total_size / (1024*1024)
                pct = progress * 100
                self.status_label.configure(text=f"Downloading... {mb_down:.2f} MB / {mb_tot:.2f} MB ({pct:.1f}%)")

            # Calculate and update speed every 0.5 seconds
            curr_time = time.time()
            dt = curr_time - self.last_update_time
            if dt >= 0.5:
                speed_bps = self.bytes_since_last_update / dt
                self.speed_label.configure(text=f"{(speed_bps / (1024*1024)):.2f} MB/s")
                # Reset speed counter for the next interval
                self.bytes_since_last_update = 0
                self.last_update_time = curr_time

        # Re-run this loop constantly
        self.after(100, self.process_queues)

    def start_download(self):
        """Validates input and launches the workflow."""
        if self.is_downloading: return
        
        url = self.url_entry.get().strip()
        if not url:
            self.log_message("ERROR: URL cannot be empty.")
            return

        bind_ip = self.bind_entry.get().strip()
        threads = int(self.thread_slider.get())

        # Prompt user for save location
        default_name = os.path.basename(url.split("?")[0]) or "downloaded_file.out"
        save_path = filedialog.asksaveasfilename(
            initialfile=default_name,
            title="Save Download As...",
            defaultextension=".*"
        )
        
        if not save_path:
            self.log_message("Download cancelled by user.")
            return

        # Reset states
        self.is_downloading = True
        self.start_button.configure(state="disabled")
        self.progress_bar.set(0)
        self.downloaded_bytes = 0
        self.bytes_since_last_update = 0
        self.total_size = 0
        self.last_update_time = time.time()
        self.speed_label.configure(text="0.00 MB/s")

        # Clear logs
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

        self.log_message(f"Initialize workflow... Targeting: {save_path}")
        
        # Launch background orchestrator
        threading.Thread(target=self.download_workflow, args=(url, threads, bind_ip, save_path), daemon=True).start()

    def deep_system_optimize(self):
        """Checks for admin privileges and executes Windows netsh optimization commands."""
        if sys.platform != "win32":
            self.log_message("OPTIMIZE FAILED: This feature is only supported on Windows.")
            return
            
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        except Exception:
            is_admin = False
            
        if not is_admin:
            self.log_message("OPTIMIZE FAILED: Administrator privileges required.")
            self.log_message("Please restart the application as Administrator to use this feature.")
            return
            
        self.log_message("Running Deep System Optimization...")
        self.optimize_button.configure(state="disabled")
        
        commands = [
            'netsh int tcp set global autotuninglevel=normal',
            'netsh interface tcp set global rss=enabled'
        ]
        
        def run_cmds():
            for cmd in commands:
                try:
                    subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    self.log_message(f"✓ Optimized: {cmd.split('=')[-1].upper()}")
                except subprocess.CalledProcessError:
                    self.log_message(f"❌ Failed: {cmd}")
                    
            self.log_message("Deep System Optimization Complete!")
            self.optimize_button.configure(state="normal")
            
        threading.Thread(target=run_cmds, daemon=True).start()

    # ==========================================
    # 4. Multi-Threaded Downloader Engine
    # ==========================================
    def download_workflow(self, url, thread_count, bind_ip, target_filename):
        """Runs in background thread to orchestrate the entire process."""
        try:
            # Step A: Parse Bind IPs
            bind_ips = [ip.strip() for ip in bind_ip.split(',') if ip.strip()]
            if bind_ips:
                self.log_message(f"Parsed Bind IPs: {', '.join(bind_ips)}")
            else:
                self.log_message("No Bind IP provided. Using default network interface.")

            # Step B: Get file metadata using a temporary session
            temp_session = requests.Session()
            if bind_ips:
                # Bind the initial HEAD request to the first provided IP
                temp_adapter = BoundHTTPAdapter(source_ip=bind_ips[0])
                temp_session.mount("http://", temp_adapter)
                temp_session.mount("https://", temp_adapter)

            self.log_message(f"Contacting server for: {url}")
            head = temp_session.head(url, timeout=10, allow_redirects=True)
            head.raise_for_status()

            if head.headers.get('Accept-Ranges', '').lower() != 'bytes' or not head.headers.get('Content-Length'):
                self.log_message("CRITICAL: Server does not support range requests.")
                return

            self.total_size = int(head.headers.get('Content-Length'))
            self.log_message(f"Success! Remote file size: {self.total_size / (1024*1024):.2f} MB")

            # Check available disk space before proceeding
            total_disk, used_disk, free_disk = shutil.disk_usage(os.getcwd())
            if free_disk < self.total_size:
                self.log_message(f"CRITICAL ERROR: Not enough disk space. Requires {self.total_size / (1024*1024):.2f} MB, but only {free_disk / (1024*1024):.2f} MB is free.")
                return

            # Set up State Saver using the user's chosen path
            self.state_file = target_filename + ".state.json"
            
            saved_state = {}
            if os.path.exists(self.state_file):
                try:
                    with open(self.state_file, 'r') as f:
                        saved_state = json.load(f)
                    self.log_message("Found saved JSON state. Resuming download...")
                except Exception as e:
                    self.log_message(f"Failed to load state: {e}")

            # Calculate chunk ranges and offsets
            ranges = []
            self.chunk_states = {}
            
            if saved_state:
                # Load EXACT dynamic sub-chunks from saved state
                for str_i, state in saved_state.items():
                    start = state.get("start_byte", 0)
                    current = state.get("current_start")
                    end = state.get("end_byte", 0)
                    temp_path = state.get("temp_path")
                    
                    self.downloaded_bytes += (current - start)
                    self.chunk_states[str_i] = {"start_byte": start, "current_start": current, "end_byte": end, "temp_path": temp_path}
                    ranges.append((start, current, end, str_i, temp_path))
            else:
                chunk_size = self.total_size // thread_count
                for i in range(thread_count):
                    start = i * chunk_size
                    end = start + chunk_size - 1 if i < thread_count - 1 else self.total_size - 1
                    
                    str_i = str(i)
                    current = start
                    temp_path = f"{target_filename}.part{i}"
                    
                    self.chunk_states[str_i] = {"start_byte": start, "current_start": current, "end_byte": end, "temp_path": temp_path}
                    ranges.append((start, current, end, str_i, temp_path))
                
            self.state_changed = True # Force initial save

            # Step C: Execute Concurrent Download Workers
            self.log_message(f"Launching {thread_count} concurrent download threads...")
            temp_files = []
            
            # Allow triple the thread count for dynamically spawned adaptive chunks
            with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count * 3) as executor:
                futures = set()
                
                for start, current, end, index, temp_path in ranges:
                    # Assign IPs in a round-robin fashion based on root index
                    root_idx = int(str(index).split('.')[0])
                    thread_bind_ip = bind_ips[root_idx % len(bind_ips)] if bind_ips else None
                    future = executor.submit(self.download_chunk_worker, thread_bind_ip, url, start, current, end, index, temp_path)
                    futures.add(future)
                
                # Await completion dynamically to allow injecting new futures
                while futures:
                    done, futures = concurrent.futures.wait(futures, return_when=concurrent.futures.FIRST_COMPLETED)
                    
                    for future in done:
                        try:
                            status = future.result()
                            if not status: continue
                            
                            state, idx, *data = status
                            
                            if state == "SUCCESS":
                                temp_path = data[0]
                                temp_files.append((idx, temp_path))
                                self.log_message(f"✓ Thread {idx} finished.")
                                
                            elif state == "SLOW":
                                current_start, end_byte, temp_path = data
                                # Save the partial progress of the slow thread
                                temp_files.append((idx, temp_path))
                                
                                # Split the remaining range precisely in half
                                remaining_bytes = end_byte - current_start
                                midpoint = current_start + (remaining_bytes // 2)
                                
                                idx_a = f"{idx}.1"
                                idx_b = f"{idx}.2"
                                
                                path_a = f"{target_filename}.part{idx_a}"
                                path_b = f"{target_filename}.part{idx_b}"
                                
                                # Update states for persistent recovery!
                                self.chunk_states[str(idx)]["end_byte"] = current_start - 1 # Original chunk ends exactly where it stopped
                                self.chunk_states[idx_a] = {"start_byte": current_start, "current_start": current_start, "end_byte": midpoint, "temp_path": path_a}
                                self.chunk_states[idx_b] = {"start_byte": midpoint + 1, "current_start": midpoint + 1, "end_byte": end_byte, "temp_path": path_b}
                                self.state_changed = True
                                
                                # Spawn Thread A
                                ip_a = bind_ips[len(futures) % len(bind_ips)] if bind_ips else None
                                future_a = executor.submit(self.download_chunk_worker, ip_a, url, current_start, current_start, midpoint, idx_a, path_a)
                                futures.add(future_a)
                                
                                # Spawn Thread B
                                ip_b = bind_ips[(len(futures) + 1) % len(bind_ips)] if bind_ips else None
                                future_b = executor.submit(self.download_chunk_worker, ip_b, url, midpoint + 1, midpoint + 1, end_byte, idx_b, path_b)
                                futures.add(future_b)
                                
                                self.log_message(f"➔ 🚀 Adaptive Chunking: Splitting slow Thread {idx} into Sub-Threads {idx_a} and {idx_b}")
                                
                            elif state == "FAILED":
                                self.log_message(f"❌ Thread {idx} failed permanently.")
                                
                        except Exception as e:
                            self.log_message(f"❌ A thread generated an exception: {e}")

            # Step D: File Stitcher Module
            if len(temp_files) == thread_count:
                self.log_message("All threads completed perfectly. Triggering File Stitcher...")
                # Stitch dynamically split chunks precisely by their hierarchical index string (e.g. '3.1' comes before '3.10')
                temp_files.sort(key=lambda x: tuple(map(int, str(x[0]).split('.'))))
                chunk_paths = [p for _, p in temp_files]
                
                if self.stitch_files(chunk_paths, target_filename):
                    self.log_message(f"SUCCESS: Master file assembled as '{target_filename}'")
                    self.status_label.configure(text="Download Complete!")
                    # Delete the state file once fully complete!
                    if os.path.exists(self.state_file):
                        os.remove(self.state_file)
                        self.log_message("State JSON file deleted.")
                else:
                    self.log_message("ERROR: Stitcher failed to assemble the final file.")
            else:
                self.log_message("ERROR: Incomplete chunk downloads. Aborting stitcher.")

        except Exception as e:
            self.log_message(f"FATAL WORKFLOW ERROR: {str(e)}")
            self.status_label.configure(text="Download Failed.")
        finally:
            self.is_downloading = False
            self.start_button.configure(state="normal")
            self.speed_label.configure(text="0.00 MB/s")

    def download_chunk_worker(self, bind_ip, url, start_byte, current_start, end_byte, index, temp_path):
        """Worker thread that downloads a specific byte range, monitors its own speed, and handles retries."""
        session = requests.Session()
        if bind_ip:
            bound_adapter = BoundHTTPAdapter(source_ip=bind_ip)
            session.mount("http://", bound_adapter)
            session.mount("https://", bound_adapter)

        max_retries = 3
        
        if current_start > end_byte:
            self.log_message(f"➔ Thread {index} chunk already complete. Skipping.")
            return ("SUCCESS", index, temp_path)
            
        for attempt in range(max_retries):
            ip_log = f" [IP: {bind_ip}]" if bind_ip else ""
            self.log_message(f"➔ Thread {index}{ip_log} started [bytes {current_start}-{end_byte}] (Attempt {attempt+1}/{max_retries})")
            headers = {'Range': f'bytes={current_start}-{end_byte}'}
            
            try:
                # CONNECTION TIMEOUT: If no data received for 10s, throws a ReadTimeout catching in the Exception block
                response = session.get(url, headers=headers, stream=True, timeout=10)
                response.raise_for_status()
                
                mode = 'wb' if current_start == start_byte else 'ab'
                
                with open(temp_path, mode) as f:
                    chunk_speed_start_time = time.time()
                    chunk_bytes_downloaded = 0
                    
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            chunk_len = len(chunk)
                            current_start += chunk_len
                            chunk_bytes_downloaded += chunk_len
                            
                            self.progress_queue.put((index, chunk_len))
                            
                            # REAL-TIME ADAPTIVE CHUNKING LOGIC
                            curr_time = time.time()
                            dt = curr_time - chunk_speed_start_time
                            if dt >= 5.0: # Audit speed every 5 seconds
                                speed_bps = chunk_bytes_downloaded / dt
                                remaining_bytes = end_byte - current_start
                                
                                # If downloading under 500 KB/s and there's more than 1MB remaining
                                if speed_bps < 512000 and remaining_bytes > 1048576:
                                    self.log_message(f"⚠️ Thread {index} is too slow ({(speed_bps/1024):.0f} KB/s). Triggering Adaptive Chunking!")
                                    return ("SLOW", index, current_start, end_byte, temp_path)
                                
                                # Reset speed tracker for the next audit
                                chunk_speed_start_time = curr_time
                                chunk_bytes_downloaded = 0
                                
                return ("SUCCESS", index, temp_path)
                
            except Exception as e:
                self.log_message(f"Thread {index} Network Error: {e}")
                
                if attempt < max_retries - 1:
                    self.log_message(f"Thread {index} waiting 5 seconds before retrying...")
                    time.sleep(5)
                else:
                    self.log_message(f"Thread {index} failed completely after {max_retries} attempts.")
                    if temp_path and os.path.exists(temp_path):
                        os.remove(temp_path)
                    return ("FAILED", index, None)

    # ==========================================
    # 5. File Stitcher Component
    # ==========================================
    def stitch_files(self, chunk_files, target_filename):
        """Merges all downloaded temporary chunks sequentially into the final file."""
        try:
            with open(target_filename, 'wb') as outfile:
                for idx, chunk_file in enumerate(chunk_files):
                    self.log_message(f"Stitching block {idx+1}/{len(chunk_files)}...")
                    with open(chunk_file, 'rb') as infile:
                        while True:
                            # Read larger blocks for faster merging
                            data = infile.read(65536)
                            if not data:
                                break
                            outfile.write(data)
                    # Clean up temp file immediately after merging
                    os.remove(chunk_file)
            return True
        except Exception as e:
            self.log_message(f"Stitcher Error: {e}")
            return False


if __name__ == "__main__":
    app = NetworkBoosterApp()
    app.mainloop()
