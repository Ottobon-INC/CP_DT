from sqlalchemy import Column, String, Integer, DateTime, Boolean, func
from app.database.session import Base

class TwinInactivityState(Base):
    """
    TwinInactivityState: Stores persistent inactivity tracking variables 
    for each learner to enable state tracking across application restarts.
    """
    __tablename__ = "twin_inactivity_state"
    
    learner_id = Column(String, primary_key=True, index=True)
    last_activity_at = Column(DateTime(timezone=True), nullable=False)
    inactivity_stage = Column(Integer, default=0, nullable=False)
    
    first_message_sent_at = Column(DateTime(timezone=True), nullable=True)
    second_message_sent_at = Column(DateTime(timezone=True), nullable=True)
    third_message_sent_at = Column(DateTime(timezone=True), nullable=True)
    email_sent_at = Column(DateTime(timezone=True), nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
