import sys
import requests
import concurrent.futures
import tempfile
import os

def download_chunk(url, start_byte, end_byte, chunk_index):
    """Downloads a specific byte range of a file and saves it to a temporary file."""
    headers = {'Range': f'bytes={start_byte}-{end_byte}'}
    try:
        # Use stream=True to handle large chunks efficiently
        response = requests.get(url, headers=headers, stream=True, timeout=15)
        response.raise_for_status()
        
        # Create a temporary file for this chunk
        fd, temp_path = tempfile.mkstemp(prefix=f"chunk_{chunk_index}_")
        with os.fdopen(fd, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return temp_path
    except requests.exceptions.Timeout:
        print(f"Error: Timeout while downloading chunk {chunk_index}.")
        return None
    except requests.exceptions.ConnectionError:
        print(f"Error: Connection dropped while downloading chunk {chunk_index}.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error downloading chunk {chunk_index}: {e}")
        return None

def merge_chunks(target_filename, chunk_files):
    """Merges temporary chunk files into a single target file and deletes the chunks."""
    print(f"\nMerging {len(chunk_files)} chunks into {target_filename}...")
    try:
        with open(target_filename, 'wb') as outfile:
            for chunk_file in chunk_files:
                try:
                    with open(chunk_file, 'rb') as infile:
                        while True:
                            data = infile.read(8192)
                            if not data:
                                break
                            outfile.write(data)
                    # Delete the chunk file after successfully merging
                    os.remove(chunk_file)
                    print(f"Merged and deleted: {chunk_file}")
                except Exception as e:
                    print(f"Error processing chunk {chunk_file}: {e}")
                    return False
        print(f"Successfully merged all chunks into {target_filename}")
        return True
    except Exception as e:
        print(f"Error opening target file {target_filename}: {e}")
        return False

def main():
    if len(sys.argv) != 3:
        print("Usage: python concurrent_downloader.py <URL> <THREAD_COUNT>")
        sys.exit(1)

    url = sys.argv[1]
    try:
        thread_count = int(sys.argv[2])
    except ValueError:
        print("Error: THREAD_COUNT must be an integer.")
        sys.exit(1)

    if thread_count <= 0:
        print("Error: THREAD_COUNT must be at least 1.")
        sys.exit(1)

    try:
        # Check if the server supports range requests
        print(f"Checking URL: {url}...")
        head_response = requests.head(url, timeout=10, allow_redirects=True)
        head_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error checking URL: {e}")
        sys.exit(1)

    accept_ranges = head_response.headers.get('Accept-Ranges', '').lower()
    content_length_str = head_response.headers.get('Content-Length')

    if accept_ranges != 'bytes' or not content_length_str:
        print("Error: Server does not support ranged requests ('Accept-Ranges: bytes') or 'Content-Length' is missing.")
        print("Cannot perform concurrent chunk downloading.")
        sys.exit(1)

    content_length = int(content_length_str)
    print(f"File size: {content_length} bytes")
    print(f"Starting download with {thread_count} threads...")

    # Calculate byte ranges
    chunk_size = content_length // thread_count
    ranges = []
    
    for i in range(thread_count):
        start_byte = i * chunk_size
        # The last chunk gets any remaining bytes
        end_byte = start_byte + chunk_size - 1 if i < thread_count - 1 else content_length - 1
        ranges.append((start_byte, end_byte, i))

    temp_files = []
    
    # Download chunks concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count) as executor:
        # Submit all download tasks
        future_to_chunk = {
            executor.submit(download_chunk, url, start, end, index): index 
            for start, end, index in ranges
        }
        
        for future in concurrent.futures.as_completed(future_to_chunk):
            index = future_to_chunk[future]
            try:
                temp_path = future.result()
                if temp_path:
                    temp_files.append((index, temp_path))
                    print(f"Chunk {index} downloaded successfully to: {temp_path}")
                else:
                    print(f"Chunk {index} failed.")
            except Exception as e:
                print(f"Chunk {index} generated an exception: {e}")

    # Verification and merging
    if len(temp_files) == thread_count:
        print("\nAll chunks downloaded successfully!")
        temp_files.sort(key=lambda x: x[0])
        chunk_paths = [path for _, path in temp_files]
        
        # Determine a target filename from the URL
        target_filename = os.path.basename(url.split("?")[0])
        if not target_filename:
            target_filename = "downloaded_file"
            
        merge_chunks(target_filename, chunk_paths)
    else:
        print("\nSome chunks failed to download. The downloaded temporary files have not been cleaned up.")

if __name__ == "__main__":
    main()
