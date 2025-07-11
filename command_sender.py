import time
import random
import requests
import json
import sys
import os
from datetime import datetime

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))
from models import db, Telecommand, TelecommandStatus

from flask import Flask

# Create Flask app for database context
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///TECChallenge.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Configuration
SPACECRAFT_URL = 'http://localhost:8080/commands'

class CommandSender:
    def __init__(self):
        self.running = True
    
    def pick_up_ready_commands(self):
        """✅ REQUIREMENT: Pick up issued telecommands"""
        with app.app_context():
            ready_commands = Telecommand.query.filter_by(
                status=TelecommandStatus.READY
            ).order_by(
                Telecommand.priority.asc(),
                Telecommand.created_at.asc()
            ).all()
            
            if ready_commands:
                print(f"🚀 SENDER: Found {len(ready_commands)} ready commands")
            return ready_commands
    
    def process_command(self, command_id):
        """Process single command through complete pipeline"""
        with app.app_context():
            # Get fresh command from database
            cmd = Telecommand.query.get(command_id)
            if not cmd or cmd.status != TelecommandStatus.READY:
                return
            
            print(f"🚀 SENDER: Processing {cmd.command_name} [{cmd.id}]")
            
            # ===== PHASE 1: Ready → Transmitted =====
            # ✅ REQUIREMENT: Random delay up to 30 seconds
            delay = random.uniform(1, 30)
            print(f"🚀 SENDER: Waiting {delay:.1f}s before transmission...")
            time.sleep(delay)
            
            # Update to Transmitted
            cmd.status = TelecommandStatus.TRANSMITTED
            cmd.transmitted_at = datetime.utcnow()
            db.session.commit()
            print(f"🚀 SENDER: Status → Transmitted")
            
            # Send to spacecraft
            try:
                payload = {
                    'command_name': cmd.command_name,
                    'parameters': json.loads(cmd.parameters) if cmd.parameters else {},
                    'command_id': cmd.id
                }
                
                print(f"🚀 SENDER: Transmitting to spacecraft...")
                response = requests.post(SPACECRAFT_URL, json=payload, timeout=10)
                
                if response.status_code != 200:
                    raise Exception(f"HTTP {response.status_code}")
                
                print(f"🚀 SENDER: ✅ Transmission successful")
                
            except Exception as e:
                print(f"🚀 SENDER: ❌ Transmission failed: {e}")
                cmd.status = TelecommandStatus.FAILED
                cmd.error_message = str(e)
                cmd.executed_at = datetime.utcnow()
                db.session.commit()
                return
            
            # ===== PHASE 2: Transmitted → Acknowledged =====
            delay = random.uniform(2, 8)
            print(f"🚀 SENDER: Waiting {delay:.1f}s for acknowledgment...")
            time.sleep(delay)
            
            cmd.status = TelecommandStatus.ACKNOWLEDGED
            cmd.acknowledged_at = datetime.utcnow()
            db.session.commit()
            print(f"🚀 SENDER: Status → Acknowledged")
            
            # ===== PHASE 3: Acknowledged → Executed/Failed =====
            # ✅ REQUIREMENT: Advance status until Executed or Failed
            delay = random.uniform(3, 12)
            print(f"🚀 SENDER: Waiting {delay:.1f}s for execution...")
            time.sleep(delay)
            
            # 85% success rate
            success = random.random() < 0.85
            
            if success:
                cmd.status = TelecommandStatus.EXECUTED
                print(f"🚀 SENDER: Status → ✅ Executed")
            else:
                cmd.status = TelecommandStatus.FAILED
                cmd.error_message = "Command execution failed on spacecraft"
                print(f"🚀 SENDER: Status → ❌ Failed")
            
            cmd.executed_at = datetime.utcnow()
            db.session.commit()
            
            print(f"🚀 SENDER: Command {cmd.command_name} complete!")
    
    def run(self):
        """Main command sender loop - simple and sequential"""
        print("🚀 Starting Command Sender Service")
        print("🚀 Polling for ready commands every 5 seconds...")
        print("🚀 Processing commands sequentially (no threading)")
        
        while self.running:
            try:
                ready_commands = self.pick_up_ready_commands()
                
                # Process each command sequentially
                for command in ready_commands:
                    self.process_command(command.id)
                
                # Poll every 5 seconds
                time.sleep(5)
                
            except KeyboardInterrupt:
                print("\n🚀 Command Sender shutting down...")
                self.running = False
            except Exception as e:
                print(f"🚀 Error in command sender: {e}")
                time.sleep(5)

if __name__ == "__main__":
    sender = CommandSender()
    sender.run()