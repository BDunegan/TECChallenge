import time
import random
import requests
import json
import sys
import os
from datetime import datetime

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))
# The imports from shared/models must come after the sys.path.append to be recognized.
from models import db, Telecommand, TelecommandStatus

# Again we use a Flask framework
from flask import Flask

# Create Flask app for database context
app = Flask(__name__)

# Database configuration - use environment variable for shared database
database_url = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Configuration from environment variables
SPACECRAFT_URL = os.environ.get('SPACECRAFT_URL', 'http://spacecraft:8080/commands')
POLL_INTERVAL = int(os.environ.get('POLL_INTERVAL', 1)) # Polls the database for new commands posted

# Here we make a crucial pivot. I chose to use an Object-Oriented class architecture to make use of encapsulation.
# This allows us to operate on the commands much easier. By taking advantage of a class attribute self.running we can better interact with the realtime updates and have a clean exit to the program.
# OOP also allows us to be more flexible with the way commands are polled, modified, and sent between the telecommand interface and the telemetry interface (spacecraft receiver)
# The CommandSender class serves as a sort of middleware microseervice between the ground and satilite.
class CommandSender:
    def __init__(self):
        self.running = True # Boolean flag attribute for CommandSender class heatlh
    
    def wait_for_database(self):
        """Wait for ground service to create database schema"""
        # I was having issues with command_sender loading faster than ground_station. Since ground_station builds the databae, we msut wait for it to finish then check access to the shared TECChallenge.db
        max_retries = 60  # Wait up to 5 minutes
        for attempt in range(max_retries):
            try:
                print(f"🚀 SENDER: Database connection attempt {attempt + 1}/{max_retries}")
                
                with app.app_context():
                    # Try to query the database
                    count = Telecommand.query.count()
                    print(f"🚀 SENDER: Database connection established - {count} commands in database")
                    return True
                    
            except Exception as e:
                print(f"🚀 SENDER: Database not ready: {e}")
                time.sleep(5)
        
        print("🚀 SENDER: Could not connect to database after waiting")
        return False
    
    def pick_up_ready_commands(self):
        """Pick up issued telecommands via DATABASE-MEDIATED communication"""
        with app.app_context():
            try:
                # Get ready commands
                ready_commands = Telecommand.query.filter_by(
                    status=TelecommandStatus.READY
                ).order_by(
                    Telecommand.created_at.asc()
                ).all()
                
                if ready_commands: # An array of Telecommands... part of me dislikes non explicit datatypes but they are easier to work with in theory
                    print(f"SENDER: Found {len(ready_commands)} ready commands via database")
                    for cmd in ready_commands:
                        print(f"SENDER: Ready command: {cmd.command_name} [{cmd.id}]")
                
                return ready_commands
                
            except Exception as e:
                print(f"SENDER: Error querying database: {e}")
                return []
    
    def update_command_status(self, command_id, new_status, error_message=None):
        """Update command status in shared database"""
        with app.app_context(): # Pulling in DB as context to the process
            try:
                cmd = Telecommand.query.get(command_id)
                if cmd:
                    old_status = cmd.status.value
                    cmd.status = new_status
                    
                    # Update timestamps based on status
                    now = datetime.utcnow()
                    if new_status == TelecommandStatus.TRANSMITTED:
                        cmd.transmitted_at = now
                    elif new_status == TelecommandStatus.ACKNOWLEDGED:
                        cmd.acknowledged_at = now
                    elif new_status in [TelecommandStatus.EXECUTED, TelecommandStatus.FAILED]:
                        cmd.executed_at = now
                        if error_message:
                            cmd.error_message = error_message
                    
                    db.session.commit() # Agaian, Flask databases allow for ACID db properties (Atomic, Consistent, Isolated, Durable)
                    print(f"SENDER: Updated command {command_id} status: {old_status} → {new_status.value}")
                    return True
                else:
                    print(f"SENDER: Command {command_id} not found for status update")
                    
            except Exception as e:
                print(f"SENDER: Error updating command status: {e}")
                import traceback
                traceback.print_exc()
                return False
        return False
    
    def process_command(self, command_id):
        """Process single command through complete pipeline - ALL DATABASE-MEDIATED"""
        print(f"SENDER: Starting processing for command {command_id}")
        
        # Random delay to simulate real world latency
        delay = random.uniform(3, 8)  # Reduced for faster demo
        print(f"SENDER: Waiting {delay:.1f}s before transmission...")
        time.sleep(delay)
        
        # Get command details from database for transmission
        with app.app_context():
            cmd = Telecommand.query.get(command_id)
            if not cmd:
                print(f"SENDER: Command {command_id} not found in database")
                return
            
            # Send to spacecraft
            try:
                payload = {
                    'command_name': cmd.command_name,
                    'command_id': cmd.id
                }
                
                print(f"SENDER: Transmitting {cmd.command_name} to spacecraft...")
                # ===== PHASE 1: Ready -> Transmitted =====
                # We send the Telecommand to the spacecraft and can instantly switch to the TRANSMITTED Telecommand
                response = requests.post(SPACECRAFT_URL, json=payload, timeout=10)
                if not self.update_command_status(command_id, TelecommandStatus.TRANSMITTED):
                    return
                
                if response.status_code != 200:
                    raise Exception(f"HTTP {response.status_code}")
                
                time.sleep(delay)
                # Here we wait for a successful response from SPACECRAFT to advance Telecommand stage to Acknowledged
                # ===== PHASE 2: Transmitted -> Acknowledged =====
                self.update_command_status(command_id, TelecommandStatus.ACKNOWLEDGED)
                print(f"SENDER: Transmission successful")
                
            except Exception as e:
                print(f"SENDER: Transmission failed: {e}")
                self.update_command_status(command_id, TelecommandStatus.FAILED, str(e))
                return
        
        # ===== PHASE 3: Acknowledged → Executed/Failed =====
        # Advance status until Executed or Failed
        # We do not do much processing in the SPACECRAFT so as soon as we receive a response (which could carry a package back as well such as telemetry data)
        print(f"🚀 SENDER: Waiting {delay:.1f}s for execution...")
        time.sleep(delay)
        # 85% success rate
        success = random.random() < 0.85
        
        if success:
            self.update_command_status(command_id, TelecommandStatus.EXECUTED)
            print(f"SENDER: Command {command_id} -> EXECUTED")
        else:
            self.update_command_status(command_id, TelecommandStatus.FAILED)
            print(f"SENDER: Command {command_id} -> FAILED")
        
        print(f"SENDER: Command {command_id} processing complete!")
    
    def run(self):
        """Main command sender loop - database mediated communication w/ ground_station through shared TECChallenge.db"""
        print("========= Starting Command Sender Service =========")
        print(f"Database: {database_url}")
        print(f"Spacecraft URL: {SPACECRAFT_URL}")
        print(f"Container ID: {os.environ.get('HOSTNAME', 'local')}")
        print(f"Polling database every {POLL_INTERVAL} seconds...")
        
        # Wait for ground service to initialize database
        if not self.wait_for_database():
            print("SENDER: Exiting due to database connection failure")
            return
        
        print("SENDER: Entering main polling loop...")
        print("========= =============================== =========")
        while self.running:
            try:
                # DATABASE-MEDIATED: Query database for ready commands
                ready_commands = self.pick_up_ready_commands()
                
                # Process each command sequentially
                for command in ready_commands:
                    print(f"SENDER: Processing command {command.id}")
                    self.process_command(command.id)
                
                #if not ready_commands:
                #    print(f"SENDER: No ready commands, sleeping for {POLL_INTERVAL}s...")
                
                # Poll database at configured interval
                time.sleep(POLL_INTERVAL)
                
            except KeyboardInterrupt:
                print("Command Sender shutting down...")
                self.running = False
            except Exception as e:
                print(f"SENDER: Error in main loop: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    sender = CommandSender()
    sender.run()