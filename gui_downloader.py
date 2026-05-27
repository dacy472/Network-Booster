import os
import sys
import time
import threading
import tempfile
import concurrent.futures
import requests

try:
    import customtkinter as ctk
except ImportError:
    print("Error: 'customtkinter' is not installed. Please install it using: pip install customtkinter")
    sys.exit(1)

# Set the appearance mode and color theme
ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class DownloadManagerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Concurrent Download Manager")
        self.geometry("600x380")
        self.resizable(False, False)

        # Title Label
        self.title_label = ctk.CTkLabel(self, text="Download Manager", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.pack(pady=(20, 10))

        # URL Input
        self.url_label = ctk.CTkLabel(self, text="File URL:", font=ctk.CTkFont(size=14, weight="bold"))
        self.url_label.pack(pady=(10, 0), padx=20, anchor="w")

        self.url_entry = ctk.CTkEntry(self, placeholder_text="https://example.com/largefile.zip", width=560)
        self.url_entry.pack(pady=(5, 10), padx=20)

        # Thread Control Frame
        self.threads_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.threads_frame.pack(fill="x", pady=10, padx=20)

        self.threads_label = ctk.CTkLabel(self.threads_frame, text="Threads (1-16):", font=ctk.CTkFont(size=14, weight="bold"))
        self.threads_label.pack(side="left")

        # Slider for threads
        self.thread_slider = ctk.CTkSlider(self.threads_frame, from_=1, to=16, number_of_steps=15, command=self.update_thread_label)
        self.thread_slider.set(4)
        self.thread_slider.pack(side="left", padx=20, expand=True, fill="x")

        # Label to show the selected thread count
        self.thread_count_label = ctk.CTkLabel(self.threads_frame, text="4", font=ctk.CTkFont(size=14))
        self.thread_count_label.pack(side="right")

        # Start Button
        self.start_button = ctk.CTkButton(self, text="Start Download", command=self.start_download, font=ctk.CTkFont(size=14, weight="bold"))
        self.start_button.pack(pady=15)

        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(self, width=560)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10, padx=20)

        # Status Label
        self.status_label = ctk.CTkLabel(self, text="Ready", font=ctk.CTkFont(size=12))
        self.status_label.pack(pady=5)

        # Shared state variables for threading
        self.total_size = 0
        self.downloaded_bytes = 0
        self.lock = threading.Lock()
        self.is_downloading = False

    def update_thread_label(self, value):
        """Callback to update the label when slider is moved."""
        self.thread_count_label.configure(text=str(int(value)))

    def start_download(self):
        """Triggered when Start Download button is clicked."""
        if self.is_downloading:
            return

        url = self.url_entry.get().strip()
        if not url:
            self.status_label.configure(text="Error: Please enter a valid URL.", text_color="#ff5555")
            return

        threads = int(self.thread_slider.get())
        
        self.is_downloading = True
        self.start_button.configure(state="disabled")
        self.progress_bar.set(0)
        self.status_label.configure(text="Checking server...", text_color="white")
        self.downloaded_bytes = 0
        self.total_size = 0

        # Start download process in a separate background thread
        # This keeps the tkinter UI responsive!
        threading.Thread(target=self.download_process, args=(url, threads), daemon=True).start()

    def download_chunk(self, url, start_byte, end_byte, chunk_index):
        """Worker function for downloading a specific byte range."""
        headers = {'Range': f'bytes={start_byte}-{end_byte}'}
        try:
            response = requests.get(url, headers=headers, stream=True, timeout=15)
            response.raise_for_status()
            
            # Create a temporary file
            fd, temp_path = tempfile.mkstemp(prefix=f"chunk_{chunk_index}_")
            with os.fdopen(fd, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        # Safely update the shared downloaded_bytes counter
                        with self.lock:
                            self.downloaded_bytes += len(chunk)
            return temp_path
        except Exception as e:
            print(f"Error in chunk {chunk_index}: {e}")
            return None

    def merge_chunks(self, target_filename, chunk_files):
        """Merges all temporary chunks into the final file."""
        self.status_label.configure(text=f"Merging {len(chunk_files)} chunks...", text_color="yellow")
        try:
            with open(target_filename, 'wb') as outfile:
                for chunk_file in chunk_files:
                    with open(chunk_file, 'rb') as infile:
                        while True:
                            data = infile.read(8192)
                            if not data:
                                break
                            outfile.write(data)
                    # Delete temp file after successful read
                    os.remove(chunk_file)
            return True
        except Exception as e:
            print(f"Merge error: {e}")
            return False

    def update_progress_ui(self):
        """Updates the progress bar and status text dynamically."""
        while self.is_downloading:
            if self.total_size > 0:
                with self.lock:
                    current_downloaded = self.downloaded_bytes
                    
                progress = current_downloaded / self.total_size
                # Bound the progress between 0 and 1
                progress = min(1.0, max(0.0, progress))
                
                # Update progress bar safely using after() to queue UI changes
                self.after(0, self.progress_bar.set, progress)
                
                percentage = int(progress * 100)
                mb_downloaded = current_downloaded / (1024 * 1024)
                mb_total = self.total_size / (1024 * 1024)
                
                status_text = f"Downloading... {percentage}% ({mb_downloaded:.2f} MB / {mb_total:.2f} MB)"
                self.after(0, self.status_label.configure, {"text": status_text, "text_color": "white"})
                
            time.sleep(0.1)

    def download_process(self, url, thread_count):
        """The main download orchestrator (runs in background thread)."""
        try:
            # 1. Fetch headers to get content length
            head_response = requests.head(url, timeout=10, allow_redirects=True)
            head_response.raise_for_status()

            accept_ranges = head_response.headers.get('Accept-Ranges', '').lower()
            content_length_str = head_response.headers.get('Content-Length')

            if accept_ranges != 'bytes' or not content_length_str:
                self.after(0, self.status_label.configure, {"text": "Error: Server does not support range requests.", "text_color": "#ff5555"})
                return

            self.total_size = int(content_length_str)
            chunk_size = self.total_size // thread_count
            ranges = []

            # 2. Calculate byte ranges
            for i in range(thread_count):
                start_byte = i * chunk_size
                end_byte = start_byte + chunk_size - 1 if i < thread_count - 1 else self.total_size - 1
                ranges.append((start_byte, end_byte, i))

            temp_files = []
            
            # Start the UI progress updater loop in another thread
            threading.Thread(target=self.update_progress_ui, daemon=True).start()

            # 3. Download concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count) as executor:
                future_to_chunk = {
                    executor.submit(self.download_chunk, url, start, end, index): index 
                    for start, end, index in ranges
                }
                
                for future in concurrent.futures.as_completed(future_to_chunk):
                    index = future_to_chunk[future]
                    temp_path = future.result()
                    if temp_path:
                        temp_files.append((index, temp_path))

            # Stop the progress updater loop
            self.is_downloading = False 
            self.after(0, self.progress_bar.set, 1.0)

            # 4. Verification and Merging
            if len(temp_files) == thread_count:
                temp_files.sort(key=lambda x: x[0])
                chunk_paths = [path for _, path in temp_files]
                
                target_filename = os.path.basename(url.split("?")[0])
                if not target_filename:
                    target_filename = "downloaded_file"
                    
                if self.merge_chunks(target_filename, chunk_paths):
                    self.after(0, self.status_label.configure, {"text": f"Download complete! Saved: {target_filename}", "text_color": "#55ff55"})
                else:
                    self.after(0, self.status_label.configure, {"text": "Error occurred while merging chunks.", "text_color": "#ff5555"})
            else:
                self.after(0, self.status_label.configure, {"text": "Error: Some download chunks failed.", "text_color": "#ff5555"})

        except Exception as e:
            self.is_downloading = False
            self.after(0, self.status_label.configure, {"text": f"Error: {str(e)}", "text_color": "#ff5555"})
        finally:
            self.is_downloading = False
            self.after(0, self.start_button.configure, {"state": "normal"})

if __name__ == "__main__":
    app = DownloadManagerApp()
    app.mainloop()
