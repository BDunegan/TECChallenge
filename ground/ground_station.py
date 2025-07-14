from flask import Flask, request, jsonify, render_template, redirect, url_for # Flask is used as the web app framework
# request is needed to facilitate json communication
# jsonify convert python to generalize json
# render_template allows us to have an interactive flask page to post telecommands (rather than commandline)
# redirect is required for page loading / operation flow
# url_for recaptures where to redirect to (the dashboard page)
import time # allows us to attach timestamps to telecommands
import sys # Allows manipulation of system process
import os # Allows relative file pathing (useful for operating inside Docker containers)

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))

# I chose to use Flask as opposed to fastAPI because it allows for a lightweight microservice while also leveraging the full python toolkit
# I was not as focused on the frontend design (which is my main hesitation with flask) so it seemed a logical choice.
app = Flask(__name__)

# Database configuration uses environment variable for shared database
database_url = os.environ.get('DATABASE_URL', 'sqlite:////shared/TECChallenge.db')
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# The imports for models must come after the path append or it will not be recognized
from models import db, Telecommand, TelecommandStatus

# Initialize database in ground. I chose to initialize the DB here instead of in command_sender because it is less dependent on external health for the docker build
# I.E. if command_sender fails to load, the DB could be partially loaded and cause data corruption. Ground has less dependency.
db.init_app(app)

# The home route to render the web app at http://127.0.0.1:5000/ and display a basic web interface (dashboard.html template)
@app.route("/")
def dashboard():
    """Main Mission Control dashboard"""
    return render_template('dashboard.html')

# This route allows for the cancelation of a command using its uuid as a dynamic URL.
@app.route("/web/cancel/<command_id>", methods=["POST"])
def web_cancel_command(command_id):
    """Web interface route to cancel command based on dynamic UUID4"""
    telecommand = Telecommand.query.get(command_id)
    
    if telecommand and telecommand.cancel():
        db.session.commit()
        print(f"GROUND: Cancelled telecommand {telecommand.command_name} [{telecommand.id}] in TECChallenge.db database")
    
    return redirect(url_for('dashboard'))

# Checks for the health of the ground station microservice. This is used by the docker healthcheck and others to monitor status.
# Knowing the health of the ground microservice is crucial. If the ground goes down, no commands can be sent to the telemetry microservice.
@app.route("/health")
def health():
    """Check if ground service is healthy"""
    return jsonify({
        "status": "healthy", 
        "service": "ground",
        "database": database_url,
        "timestamp": time.time(),
        "container_id": os.environ.get("HOSTNAME", "unknown")
    })

# Accept new telecommands to be added to the shared database TECChallenge.db and executed by the telemetry microservice (spacecraft)
# This function meets the RESTful api requirements by providing an end point for the web app to post new commands to the shared database.
# Notably, I chose to use a database-mediated communication system here to ensure no direct communication between ground_service and command_sender.
# This choice is to ensure a decoupled relationship between each microservice which allows for flexibility and seperation of concerns.
# Additionally, database mediated communication allows for multiple command_senders to operate on the shared database and work asynchronously from the ground_station
@app.route("/api/telecommands", methods=["POST"])
def create_telecommand():
    """Accept new telecommands from mission operators - DATABASE-MEDIATED"""
    data = request.get_json()
    
    if not data or 'command_name' not in data: #Simple error validation to ensure we dont send empty commands or unnamed commands
        return jsonify({"error": "Missing command_name"}), 400
    
    # Create new telecommand in SHARED database
    telecommand = Telecommand(
        command_name=data['command_name'],
    )
    
    # The use of a Flask database here ensures ACID properties of database consistency
    db.session.add(telecommand)
    db.session.commit()
    
    print(f"GROUND: Created telecommand {telecommand.command_name} [{telecommand.id}] - Status: {telecommand.status.value}")
    print(f"GROUND: Command available for command-sender via shared database")
    
    return jsonify(telecommand.to_dict()), 201

# Return status of a selected telecommand based on a dynamic URL again using the uuid4 primary key stored in TECCHallenge.db
@app.route("/api/telecommands/<command_id>", methods=["GET"])
def get_telecommand(command_id):
    """Return status of specific telecommand from shared database"""
    telecommand = Telecommand.query.get(command_id)
    
    if not telecommand:
        return jsonify({"error": "Telecommand not found"}), 404
    
    return jsonify(telecommand.to_dict())

# Cancel queued telecommands (only in "Ready" state)
@app.route("/api/telecommands/<command_id>/cancel", methods=["PUT"])
def cancel_telecommand(command_id):
    """Cancel telecommand if in Ready state"""
    telecommand = Telecommand.query.get(command_id)
    
    #Basic error validation to prevent removing a non-existing telecommand and causing errors with referential integrity.
    if not telecommand:
        return jsonify({"error": "Telecommand not found"}), 404
    
    # I check here to ensure the TelecommandStatus is in the READY state and ONLY the READY state, returnning an error otherwise.
    if telecommand.status != TelecommandStatus.READY:
        return jsonify({
            "error": f"Cannot cancel telecommand in {telecommand.status.value} state"
        }), 400
    
    # Cancelation is validated again on the model level (abstraction for seperation of concerns in a shared database architecture).
    # Although this is redundant, I felt it nessisary to showcase both approaches to ensure rigorous following of the project requirements.
    # This level of validation I can imagine is also crucial for more sensetive state consistency in spaceflight.
    # telecommand.cancel returns a boolean TRUE only if the self.status == TelecommandStatus.READY
    if telecommand.cancel():
        db.session.commit()
        print(f"GROUND: Cancelled telecommand {telecommand.command_name} [{telecommand.id}] in shared database")
        return jsonify({
            "message": "Telecommand cancelled successfully",
            "telecommand": telecommand.to_dict()
        })
    else:
        return jsonify({
            "error": f"Cannot cancel telecommand in {telecommand.status.value} state"
        }), 400

# List all telecommands for convienence. This route already existed from previously designed structures so it seemed appropriate to add functional logic.
@app.route("/api/telecommands", methods=["GET"])
def list_telecommands():
    """List all telecommands with optional filtering from shared database"""
    status_filter = request.args.get('status')
    
    query = Telecommand.query
    if status_filter:
        query = query.filter(Telecommand.status == TelecommandStatus(status_filter))
    
    telecommands = query.order_by(Telecommand.created_at.desc()).all()
    
    return jsonify([tc.to_dict() for tc in telecommands])

# This is the main entrance for the program upon file execution.
if __name__ == "__main__":
    # Get port from environment variable
    port = int(os.environ.get("PORT", 5000)) #5000 is default but the Docker definition overrides this. (although I have docker also exposing 5000 but the redundancy is nice)
    
    # Create database tables in SHARED database for command-sender to use
    with app.app_context(): # We use the process context of the Flask app initialized at the top of the file to create the database. (we imported this context by appending the path with shared)
        try:
            db.create_all()
            print("GROUND: Database tables created in shared database")
            print("GROUND: Database ready for command-sender access")
        except Exception as e:
            print(f"GROUND: Error creating database: {e}")
    
    print(f"========= Starting Ground Service on port {port} =========")
    print(f"Database: {database_url}")
    print(f"Web Interface: http://localhost:{port}")
    print(f"Container ID: {os.environ.get('HOSTNAME', 'local')}") # Useful for debugging Docker / Shared context interactions
    print("========= ======================================= =========")
    
    # Bind to all interfaces for Docker networking
    app.run(debug=False, host="0.0.0.0", port=port) # This generalizes the docker networking to allow us access to the hosted web interface.