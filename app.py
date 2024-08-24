from app import create_app
import threading
import webbrowser
import socket

app = create_app()

def get_local_ip():
    """Get the local IP address of the machine."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.254.254.254', 1))
        ip_address = s.getsockname()[0]
    except Exception:
        ip_address = '127.0.0.1'
    finally:
        s.close()
    return ip_address

def open_browser():
    """Open the web browser after the server starts."""
    local_ip = get_local_ip()
    webbrowser.open_new(f"http://{local_ip}:5001")

if __name__ == "__main__":
    # Start a thread to open the browser after the Flask app starts
    threading.Timer(1, open_browser).start()
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)