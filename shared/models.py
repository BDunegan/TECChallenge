from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
from enum import Enum

db = SQLAlchemy()

# All status are per instruction requirements. (with the addition of cancelled for functional requirement)
# We use Enum here for typesafety and for the association of variables to english terms. 
# While this is excessive for a demo, it highlights possible errors caused by incorrect validation in larger scales.
class TelecommandStatus(Enum):
    READY = "Ready"
    TRANSMITTED = "Transmitted" 
    ACKNOWLEDGED = "Acknowledged"
    EXECUTED = "Executed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"

class Telecommand(db.Model):
    __tablename__ = 'telecommands'
    #uuid is used as the primary key to ensure uniqueness and following of best distributive principles.
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    #A field to store the name of a command
    command_name = db.Column(db.String(100), nullable = False)
    # logs the TelecommandStatus of each row
    status = db.Column(db.Enum(TelecommandStatus), default=TelecommandStatus.READY)
    
    # Timestamps to allow for status tracking. we save these for each stage.
    created_at = db.Column(db.DateTime)
    transmitted_at = db.Column(db.DateTime)
    acknowledged_at = db.Column(db.DateTime)
    executed_at = db.Column(db.DateTime)
    # Allows for more detailed error logging
    error_message = db.Column(db.Text)

    # Helper function to ensure only READY commands can be cancelled (per instructions). I discuss the redundancy of this validation in its ground_station.py correspondant
    def can_be_cancelled(self):
        """Check if command can be cancelled"""
        return self.status == TelecommandStatus.READY
    
    # Function to actually set a specific TelecommandStatus to CANCELLED
    def cancel(self):
        """Cancel the command if in Ready state"""
        if self.can_be_cancelled():
            self.status = TelecommandStatus.CANCELLED
            return True
        return False
    
    # Converts the model to a dictionary to facilitate JSON communication
    def to_dict(self):
        """Convert to dictionary for JSON response"""
        return {
            'id': self.id,
            'command_name': self.command_name,
            'status': self.status.value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'transmitted_at': self.transmitted_at.isoformat() if self.transmitted_at else None,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'error_message': self.error_message
        }