import subprocess
import ctypes
import sys

def is_admin():
    """Check if the script is running with elevated Administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_command(command, description):
    """Executes a terminal command and gracefully handles the output/errors."""
    print(f"[*] {description}...")
    try:
        # Run the command, blocking until complete, and capture the text output
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True
        )
        print(f"    [SUCCESS] {result.stdout.strip() or 'Command executed successfully.'}")
    except subprocess.CalledProcessError as e:
        print(f"    [FAILED] Command returned error code: {e.returncode}")
        # Print whichever stream caught the error message
        error_msg = e.stderr.strip() if e.stderr else e.stdout.strip()
        print(f"    [DETAILS] {error_msg}")
    except Exception as e:
        print(f"    [FATAL ERROR] {str(e)}")

def optimize_network():
    print("=== Windows Network Performance Optimizer ===\n")
    
    # OS Check
    if sys.platform != "win32":
        print("[!] ERROR: This script executes 'netsh' and 'reg' commands and is exclusively for Windows systems.")
        return

    # Admin Check
    if not is_admin():
        print("[!] CRITICAL: Administrator privileges are required to modify the Registry and global TCP/IP parameters.")
        print("    Please right-click the script (or your command prompt) and select 'Run as Administrator'.")
        return

    # 1. Set Global Autotuning Level to Normal
    # This ensures the TCP Receive Window scales dynamically for high-bandwidth connections.
    run_command(
        'netsh int tcp set global autotuninglevel=normal',
        "Setting TCP Global Autotuning Level to 'normal'"
    )

    # 2. Disable Task Offload
    # This prevents the CPU from offloading network tasks to the NIC, 
    # which can sometimes cause severe bottlenecking on cheap/unstable network cards.
    run_command(
        'netsh int ip set global taskoffload=disabled',
        "Disabling Network Task Offload (IP Level)"
    )

    # 3. Disable Network Throttling in the Registry
    # By default, Windows throttles non-multimedia network traffic to prioritize media playback.
    # Setting this DWORD to 0xFFFFFFFF totally disables that throttling.
    reg_command = (
        'reg add "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Multimedia\\SystemProfile" '
        '/v NetworkThrottlingIndex /t REG_DWORD /d 0xffffffff /f'
    )
    run_command(
        reg_command,
        "Disabling Windows Network Throttling Index via Registry (0xFFFFFFFF)"
    )

    print("\n[+] Optimization routines finished! You may need to restart the computer for Registry changes to take full effect.")

if __name__ == "__main__":
    optimize_network()
