from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
from enum import Enum

db = SQLAlchemy()

class TelecommandStatus(Enum):
    READY = "Ready"
    TRANSMITTED = "Transmitted" 
    ACKNOWLEDGED = "Acknowledged"
    EXECUTED = "Executed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"

class Telecommand(db.Model):
    __tablename__ = 'telecommands'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    command_name = db.Column(db.String(100), nullable = False)
    parameters = db.Column(db.Text)  # JSON string
    status = db.Column(db.Enum(TelecommandStatus), default=TelecommandStatus.READY)
    priority = db.Column(db.Integer, default=5)  # 1=highest, 10=lowest
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    transmitted_at = db.Column(db.DateTime)
    acknowledged_at = db.Column(db.DateTime)
    executed_at = db.Column(db.DateTime)
    
    # Operator info
    operator_id = db.Column(db.String(50))
    description = db.Column(db.Text)
    error_message = db.Column(db.Text)

    def can_be_cancelled(self):
        """Check if command can be cancelled"""
        return self.status == TelecommandStatus.READY
    
    def cancel(self):
        """Cancel the command if in Ready state"""
        if self.can_be_cancelled():
            self.status = TelecommandStatus.CANCELLED
            return True
        return False
    
    def to_dict(self):
        """Convert to dictionary for JSON response"""
        return {
            'id': self.id,
            'command_name': self.command_name,
            'parameters': self.parameters,
            'status': self.status.value,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'transmitted_at': self.transmitted_at.isoformat() if self.transmitted_at else None,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'operator_id': self.operator_id,
            'description': self.description,
            'error_message': self.error_message
        }