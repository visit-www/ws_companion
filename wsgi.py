# * Import and instantiate app;
from app import create_app
app = create_app()

# Imports for threading, webbrowser, and socket to open the browser automatically
import threading
import webbrowser
import socket
import os

# Function to open the default web browser
def open_browser():
    # Find the free port on localhost to open in the web browser
    port=5001
    url = f"http://127.0.0.1:{port}"
    webbrowser.open_new(url)

# Start the application
if __name__ == "__main__":
    # Retrieve the port from environment variables for Heroku compatibility
    port =int(os.environ.get("PORT",5001))
    app.run(host='0.0.0.0', port=port, debug=True, use_reloader=True)
