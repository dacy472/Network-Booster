import socket
import requests
from requests.adapters import HTTPAdapter

class BoundHTTPAdapter(HTTPAdapter):
    """
    A custom HTTP Adapter that binds to a specific local IP address.
    This is useful for routing traffic through a specific network interface 
    (like a specific Wi-Fi adapter, Ethernet, or VPN) by providing its IP.
    """
    def __init__(self, source_ip, *args, **kwargs):
        self.source_ip = source_ip
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        """
        Overrides the default pool manager initialization.
        We instruct urllib3 to use our specific IP when opening sockets.
        The tuple is (IP_ADDRESS, PORT). Using port 0 lets the OS pick an available ephemeral port.
        """
        # Under the hood, urllib3's HTTPConnection uses socket.create_connection,
        # which will call socket.bind(source_address) before connecting.
        pool_kwargs['source_address'] = (self.source_ip, 0)
        super().init_poolmanager(connections, maxsize, block=block, **pool_kwargs)


def main():
    # Replace this with the actual IP address of the interface you want to use.
    # You can find your IPs using `ifconfig` (macOS/Linux) or `ipconfig` (Windows).
    TARGET_INTERFACE_IP = "192.168.1.100"  # Example IP
    
    print(f"Creating a session bound to local IP: {TARGET_INTERFACE_IP}")
    
    # Create the session
    session = requests.Session()
    
    # Instantiate our custom adapter
    bound_adapter = BoundHTTPAdapter(source_ip=TARGET_INTERFACE_IP)
    
    # Mount the adapter to specific protocols (or both HTTP and HTTPS)
    session.mount("http://", bound_adapter)
    session.mount("https://", bound_adapter)
    
    try:
        # Now, any request made through this session will originate from TARGET_INTERFACE_IP
        print("Testing connection...")
        
        # httpbin.org/ip echoes back the IP address from which it received the request
        response = session.get("https://httpbin.org/ip", timeout=10)
        response.raise_for_status()
        
        print("\nSuccess! Server sees our IP as:")
        print(response.json())
        
    except requests.exceptions.ConnectionError as e:
        print("\nFailed to connect.")
        print(f"Error: Make sure the IP '{TARGET_INTERFACE_IP}' actually belongs to an active network interface on your machine.")
        print(f"Details: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
