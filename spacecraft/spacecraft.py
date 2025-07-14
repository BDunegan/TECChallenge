# Justification for the use of these packages can be found in the ground_station.py documentation. The reasoning remains the same.
from flask import Flask, request, jsonify
import random
import time
import os

app = Flask(__name__)

# Here I set a root URL to display a very simple message. This is primarily just used to see health status (good/bad) in a local browser
@app.route("/")
def home():
    return "The Exploration Company: Telemetry Interface Placeholder"

@app.route("/health")
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy", 
        "service": "spacecraft",
        "timestamp": time.time(),
    })

# Here is the endpoint for all command-sender POSTs of Telecommands. 
# We can modify the JSON response to return telemetry data to the shared database via HTTP response to command-sender microservice
# Right now the only data being returned is the time.time() float for the executed timestamp.
@app.route("/commands", methods=["POST"])
def receive_command():
    """Receives a telecommand from the ground (telecommand) interface."""
    #Convert the command to JSON
    command_data = request.get_json()

    #Log command reception
    print("**SPACECRAFT: Received command: ", command_data, "**")

    #Simulate a random operation time before response (per instructions)
    time.sleep(random.uniform(0.1, 2.0))

    #The structure for the received status response
    response = {
        "status": "received",
        "command": command_data.get("command_name", "unknown"),
        "timestamp": time.time()
    }

    print("SPACECRAFT: Sent response: ", response)
    return jsonify(response)

if __name__ == "__main__":
    # Get port from environment variable (docker-friendly)
    port = int(os.environ.get("PORT", 8080))
    
    print(f"========= Starting Spacecraft Service on port {port} =========")
    print(f"Container ID: {os.environ.get('HOSTNAME', 'local')}")
    print("========= ======================================= =========")
    
    # Bind to all interfaces for docker networking
    app.run(debug=False, host="0.0.0.0", port=port)