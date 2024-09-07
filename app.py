# * Import and instantiate app;
from app import create_app
app = create_app()

# Imports for threading, webbrowser, and socket to open the browser automatically
import threading
import webbrowser
import socket

# Function to open the default web browser
def open_browser():
    # Find the free port on localhost to open in the web browser
    port = 5001  # Make sure this matches the port in app.run()
    url = f"http://127.0.0.1:{port}"
    webbrowser.open_new(url)

# Start the application
if __name__ == "__main__":
    # Start a thread to open the browser after the Flask app starts
    threading.Timer(1, open_browser).start()  # Wait 1 second before opening the browser
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=True)
