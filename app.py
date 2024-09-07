# * Import and instantiate app;
from app import create_app
app = create_app()

# Start server;
import threading
import webbrowser
import socket

# Start the application
if __name__ == "__main__":
    # Start a thread to open the browser after the Flask app starts
    threading.Timer(1, open_browser).start()
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=True)


