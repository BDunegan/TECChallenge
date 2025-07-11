from flask import Flask, request, jsonify
import random
import time

app = Flask(__name__)

@app.route("/")
def home():
    return "The Exploration Company: Telecommand Interface Demo"

@app.route("/health")
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy", 
        "service": "spacecraft",
        "timestamp": time.time(),
    })

@app.route("/position")
def position():
    """Get spacecraft position (simulated)"""
    return jsonify({
        "x": round(random.uniform(-1000, 1000), 2),
        "y": round(random.uniform(-1000, 1000), 2), 
        "z": round(random.uniform(-1000, 1000), 2),
        "timestamp": time.time(),
        "unit": "km"
    })

@app.route("/commands", methods=["POST"])
def receive_command():
    """Receives a telecommand from the ground (telecommand) interface."""
    #Convert the command to JSON
    command_data = request.get_json()

    #Log command reception
    print("SPACECRAFT: Received command: ", command_data)

    #Simulate a random operation time before response (per instructions)
    time.sleep(random.uniform(0.1, 2.0))

    #The structure for the received status response
    response = {
        "status": "received",
        "command": command_data.get("command_name", "unknown"),
        "message": "Command received by spacecraft",
        "timestamp": time.time()
    }

    print("SPACECRAFT: Sent response: ", response)
    return jsonify(response)

if __name__ == "__main__":
    # Get port from environment variable (Docker-friendly)
    app.run(debug=True, host="localhost", port=8080)
    
    print(f"Starting Spacecraft Simulator on port 8080")