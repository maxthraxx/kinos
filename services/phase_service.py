"""PhaseService - Service for managing project phases based on token usage"""
from enum import Enum
from typing import Dict, Any, Tuple
from datetime import datetime
from services.base_service import BaseService
from utils.logger import Logger
from utils.constants import (
    MODEL_TOKEN_LIMIT,
    CONVERGENCE_THRESHOLD,
    EXPANSION_THRESHOLD
)

class ProjectPhase(Enum):
    EXPANSION = "EXPANSION"
    CONVERGENCE = "CONVERGENCE"

class PhaseService(BaseService):
    """Manages project phases based on token usage"""
    
    # Add MODEL_TOKEN_LIMIT as a class attribute
    MODEL_TOKEN_LIMIT = 128_000
    
    # Import constants directly to ensure availability
    CONVERGENCE_THRESHOLD = 0.60
    EXPANSION_THRESHOLD = 0.50
    
    # Derived values
    CONVERGENCE_TOKENS = int(MODEL_TOKEN_LIMIT * CONVERGENCE_THRESHOLD)
    EXPANSION_TOKENS = int(MODEL_TOKEN_LIMIT * EXPANSION_THRESHOLD)

    def __init__(self, _):  # Keep parameter for compatibility but don't use it
        self.logger = Logger()
        self.current_phase = ProjectPhase.EXPANSION
        self.last_transition = datetime.now()
        self.total_tokens = 0

    def determine_phase(self, total_tokens: int) -> Tuple[ProjectPhase, str]:
        """Determine appropriate phase based on token count"""
        # Store total tokens first
        self.total_tokens = total_tokens
        old_phase = self.current_phase
        
        # Calculate usage percentage
        usage_percent = (total_tokens / self.MODEL_TOKEN_LIMIT) * 100
        
        # Determine phase based on thresholds
        if total_tokens > self.CONVERGENCE_TOKENS:
            new_phase = ProjectPhase.CONVERGENCE
            message = f"Convergence needed - Token usage at {usage_percent:.1f}%"
        elif total_tokens < self.EXPANSION_TOKENS:
            new_phase = ProjectPhase.EXPANSION
            message = f"Expansion phase - Token usage at {usage_percent:.1f}%"
        else:
            new_phase = self.current_phase
            message = f"Maintaining current phase - Token usage at {usage_percent:.1f}%"
        
        # Log phase transition if it occurred
        if new_phase != old_phase:
            self.current_phase = new_phase
            self.last_transition = datetime.now()
            self.logger.log(
                f"Phase transition: {old_phase.value} → {new_phase.value}\n"
                f"Reason: {message}\n"
                f"Total tokens: {total_tokens:,}\n"
                f"Usage: {usage_percent:.1f}%",
                'info'
            )
        
        return new_phase, message

    def get_status_info(self) -> Dict[str, Any]:
        """Get current phase status information"""
        usage_percent = (self.total_tokens / self.MODEL_TOKEN_LIMIT) * 100
        
        # Determine status icon
        if usage_percent < 55:
            status_icon = "✓"
            status_message = "Below convergence threshold"
        elif usage_percent < 60:
            status_icon = "⚠️"
            status_message = "Approaching convergence threshold"
        else:
            status_icon = "🔴"
            status_message = "Convergence needed"
            
        # Calculate headroom
        if self.current_phase == ProjectPhase.EXPANSION:
            headroom = self.CONVERGENCE_TOKENS - self.total_tokens
        else:
            headroom = self.EXPANSION_TOKENS - self.total_tokens
            
        return {
            "phase": self.current_phase.value,
            "total_tokens": self.total_tokens,
            "usage_percent": usage_percent,
            "status_icon": status_icon,
            "status_message": status_message,
            "headroom": headroom,
            "last_transition": self.last_transition.isoformat()
        }

    def force_phase(self, phase: str) -> bool:
        """Force a specific phase (for debugging)"""
        try:
            new_phase = ProjectPhase(phase.upper())
            if new_phase != self.current_phase:
                self.current_phase = new_phase
                self.last_transition = datetime.now()
                self.logger.log(f"Phase manually set to: {new_phase.value}", 'warning')
            return True
        except ValueError:
            self.logger.log(f"Invalid phase: {phase}", 'error')
            return False
