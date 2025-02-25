import json
import requests
import uvicorn
import os
import signal
import subprocess
import time
from app.core.logger import logger
from app.main import app

def kill_process_on_port(port):
    """Kill any process running on the specified port"""
    try:
        # Use a more reliable approach to kill processes on the port
        if os.name == 'nt':  # Windows
            subprocess.run(f"taskkill /F /PID $(netstat -ano | findstr :{port} | awk '{{print $5}}')", shell=True)
        else:  # Unix/Linux/Mac
            # Get all PIDs using the port and kill them individually
            result = subprocess.run(f"lsof -ti:{port}", shell=True, text=True, capture_output=True)
            if result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid:
                        subprocess.run(f"kill -9 {pid}", shell=True)
                        logger.info(f"Killing process with PID {pid} on port {port}")
            logger.info(f"No process found running on port {port} or process was killed successfully")
        # Add a small delay to ensure the port is released
        time.sleep(1)
    except Exception as e:
        logger.error(f"Error killing process on port {port}: {str(e)}")

def create_room():
    """Simple function to call the API route to create a room"""
    # Load interview config from JSON file
    with open("interview_config.json") as f:
        config = json.load(f)
    
    try:
        # Make POST request to the API endpoint
        response = requests.post("http://localhost:8000/api/rooms", json=config)
        
        # Check if request was successful
        if response.status_code == 200:
            response_data = response.json()
            logger.info(f"Room created successfully!")
            logger.info(f"Room URL: {response_data['room_url']}")
            logger.info(f"Token: {response_data['token']}")
            return response_data
        else:
            logger.error(f"Failed to create room: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error during room creation: {str(e)}")
        return None

if __name__ == "__main__":
    # Kill any process running on port 8000
    kill_process_on_port(8000)
    
    # Start the FastAPI application in a separate process
    api_process = subprocess.Popen(["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"])
    
    # Wait a moment for the server to start
    time.sleep(3)
    
    # Create a room
    result = create_room()
    if result:
        print(f"\nRoom URL: {result['room_url']}")
        print(f"Token: {result['token']}")
    
    # Keep the main process running
    try:
        api_process.wait()
    except KeyboardInterrupt:
        api_process.terminate()
        print("Server stopped")