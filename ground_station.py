from flask import Flask, request, jsonify, render_template, redirect, url_for
import json
import time
import sys
import os

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))
from models import db, Telecommand, TelecommandStatus

app = Flask(__name__)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///TECChallenge.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# Configuration
SPACECRAFT_URL = "http://localhost:8080"
EARTH_CIRCUMFERENCE_KM = 40075  # Earth's circumference in kilometers

@app.route("/")
def dashboard():
    """Main TECChallenge dashboard"""
    return render_template('dashboard.html')


@app.route("/web/commands")
def web_commands():
    """Web interface for commands (same data as API)"""
    telecommands = Telecommand.query.order_by(Telecommand.created_at.desc()).all()
    return render_template('commands.html', commands=telecommands)

@app.route("/web/create", methods=["GET", "POST"])
def web_create_command():
    """Web form to create new telecommand"""
    if request.method == "POST":
        # Handle form submission
        command_name = request.form.get('command_name')
        parameters = request.form.get('parameters', '{}')
        priority = int(request.form.get('priority', 5))
        description = request.form.get('description', '')
        
        if command_name:
            telecommand = Telecommand(
                command_name=command_name,
                parameters=parameters,
                priority=priority,
                operator_id='web_operator',
                description=description
            )
            
            db.session.add(telecommand)
            db.session.commit()
            
            print(f"📡 WEB: Created telecommand {telecommand.command_name} [{telecommand.id}]")
            return redirect(url_for('dashboard'))
    
    return render_template('create_command.html')

@app.route("/web/cancel/<command_id>", methods=["POST"])
def web_cancel_command(command_id):
    """Web interface to cancel command"""
    telecommand = Telecommand.query.get(command_id)
    
    if telecommand and telecommand.cancel():
        db.session.commit()
        print(f"📡 WEB: Cancelled telecommand {telecommand.command_name} [{telecommand.id}]")
    
    return redirect(url_for('dashboard'))

@app.route("/health")
def health():
    """Check if ground station is healthy"""
    return jsonify({
        "status": "healthy", 
        "service": "ground_station",
        "timestamp": time.time()
    })

# ✅ REQUIREMENT: Accept new telecommands
@app.route("/api/telecommands", methods=["POST"])
def create_telecommand():
    """Accept new telecommands from mission operators"""
    data = request.get_json()
    
    if not data or 'command_name' not in data:
        return jsonify({"error": "Missing command_name"}), 400
    
    # Create new telecommand
    telecommand = Telecommand(
        command_name=data['command_name'],
        parameters=json.dumps(data.get('parameters', {})),
        priority=data.get('priority', 5),
        operator_id=data.get('operator_id'),
        description=data.get('description')
    )
    
    db.session.add(telecommand)
    db.session.commit()
    
    print(f"📡 API: Created telecommand {telecommand.command_name} [{telecommand.id}] - Status: {telecommand.status.value}")
    
    return jsonify(telecommand.to_dict()), 201

# ✅ REQUIREMENT: Return status of a selected telecommand  
@app.route("/api/telecommands/<command_id>", methods=["GET"])
def get_telecommand(command_id):
    """Return status of specific telecommand"""
    telecommand = Telecommand.query.get(command_id)
    
    if not telecommand:
        return jsonify({"error": "Telecommand not found"}), 404
    
    return jsonify(telecommand.to_dict())

# ✅ REQUIREMENT: Cancel queued telecommands (only in "Ready" state)
@app.route("/api/telecommands/<command_id>/cancel", methods=["DELETE"])
def cancel_telecommand(command_id):
    """Cancel telecommand if in Ready state"""
    telecommand = Telecommand.query.get(command_id)
    
    if not telecommand:
        return jsonify({"error": "Telecommand not found"}), 404
    
    if telecommand.cancel():
        db.session.commit()
        print(f"📡 API: Cancelled telecommand {telecommand.command_name} [{telecommand.id}]")
        return jsonify({
            "message": "Telecommand cancelled successfully",
            "telecommand": telecommand.to_dict()
        })
    else:
        return jsonify({
            "error": f"Cannot cancel telecommand in {telecommand.status.value} state"
        }), 400

# Additional endpoint: List all telecommands
@app.route("/api/telecommands", methods=["GET"])
def list_telecommands():
    """List all telecommands with optional filtering"""
    status_filter = request.args.get('status')
    
    query = Telecommand.query
    if status_filter:
        query = query.filter(Telecommand.status == TelecommandStatus(status_filter))
    
    telecommands = query.order_by(Telecommand.created_at.desc()).all()
    
    return jsonify([tc.to_dict() for tc in telecommands])

if __name__ == "__main__":
    # Create database tables
    with app.app_context():
        db.create_all()
        print("📡 Database tables created")
    
    print("📡 Starting Telecommand API Service with Web Interface on port 5000...")
    print("📡 Web Interface: http://localhost:5000")
    print("📡 API Endpoints: http://localhost:5000/api/telecommands")
    app.run(debug=True, host="localhost", port=5000)