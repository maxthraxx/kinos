"""Team configuration management"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

@dataclass 
class TeamMetrics:
    """Track team startup metrics"""
    total_agents: int = 0
    active_agents: int = 0
    healthy_agents: int = 0
    error_count: int = 0
    last_update: datetime = field(default_factory=datetime.now)

    @property
    def success_rate(self) -> float:
        if self.total_agents == 0:
            return 0.0
        return self.healthy_agents / self.total_agents

@dataclass
class TeamConfig:
    """Team configuration with validation"""
    name: str
    display_name: str
    agents: List[Dict[str, Any]]
    metrics: TeamMetrics = field(default_factory=TeamMetrics)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional['TeamConfig']:
        """Create TeamConfig from dictionary"""
        try:
            # Ensure required fields
            if not all(k in data for k in ['id', 'name', 'agents']):
                return None

            # Convert agents to list of dicts if needed
            agents = []
            for agent in data['agents']:
                if isinstance(agent, str):
                    agents.append({'name': agent, 'type': 'aider', 'weight': 0.5})
                else:
                    agents.append(agent)

            return cls(
                id=data['id'],
                name=data['name'],
                agents=agents,
                metrics=TeamMetrics()
            )
        except Exception:
            return None

    def validate(self) -> tuple[bool, Optional[str]]:
        """Validate team configuration"""
        try:
            if not self.id or not isinstance(self.id, str):
                return False, "Invalid team ID"

            if not self.name or not isinstance(self.name, str):
                return False, "Invalid team name"

            if not self.agents:
                return False, "No agents defined"

            # Validate each agent
            for agent in self.agents:
                if isinstance(agent, dict):
                    if 'name' not in agent:
                        return False, f"Missing name in agent config: {agent}"
                elif not isinstance(agent, str):
                    return False, f"Invalid agent format: {agent}"
                    
            return True, None
            
        except Exception as e:
            return False, str(e)

@dataclass 
class TeamMetrics:
    """Track team startup metrics"""
    total_agents: int = 0
    active_agents: int = 0
    healthy_agents: int = 0
    error_count: int = 0
    last_update: datetime = field(default_factory=datetime.now)

    @property
    def success_rate(self) -> float:
        if self.total_agents == 0:
            return 0.0
        return self.healthy_agents / self.total_agents

class TeamStartupError(Exception):
    """Custom exception for team startup errors"""
    def __init__(self, message: str, team_name: str, details: Optional[Dict] = None):
        super().__init__(message)
        self.team_name = team_name
        self.details = details or {}
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'error': str(self),
            'team_name': self.team_name,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }
"""Team configuration and metrics classes"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class TeamMetrics:
    """Team performance metrics"""
    total_agents: int = 0
    active_agents: int = 0
    healthy_agents: int = 0
    error_count: int = 0
    last_update: datetime = field(default_factory=datetime.now)

class TeamStartupError(Exception):
    """Custom error for team startup failures"""
    def __init__(self, message: str, team_name: str, details: Optional[Dict] = None):
        super().__init__(message)
        self.team_name = team_name
        self.details = details or {}
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format"""
        return {
            'status': 'error',
            'team_name': self.team_name,
            'error': str(self),
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }

@dataclass
class TeamConfig:
    """Team configuration with validation"""
    id: str
    name: str
    agents: List[Dict[str, Any]]
    metrics: TeamMetrics = field(default_factory=TeamMetrics)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional['TeamConfig']:
        """Create TeamConfig from dictionary"""
        try:
            # Ensure required fields
            if not all(k in data for k in ['id', 'name', 'agents']):
                return None

            # Convert agents to list of dicts if needed
            agents = []
            for agent in data['agents']:
                if isinstance(agent, str):
                    agents.append({'name': agent, 'type': 'aider', 'weight': 0.5})
                else:
                    agents.append(agent)

            return cls(
                id=data['id'],
                name=data['name'],
                agents=agents,
                metrics=TeamMetrics()
            )
        except Exception:
            return None

    def validate(self) -> tuple[bool, Optional[str]]:
        """Validate team configuration"""
        try:
            if not self.id or not isinstance(self.id, str):
                return False, "Invalid team ID"

            if not self.name or not isinstance(self.name, str):
                return False, "Invalid team name"

            if not self.agents:
                return False, "No agents defined"

            # Validate each agent
            for agent in self.agents:
                if isinstance(agent, dict):
                    if 'name' not in agent:
                        return False, f"Missing name in agent config: {agent}"
                elif not isinstance(agent, str):
                    return False, f"Invalid agent format: {agent}"

            return True, None

        except Exception as e:
            return False, str(e)
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary format"""
        return {
            'id': self.id,
            'name': self.name,
            'agents': self.agents,
            'metrics': {
                'total_agents': self.metrics.total_agents,
                'active_agents': self.metrics.active_agents,
                'healthy_agents': self.metrics.healthy_agents,
                'error_count': self.metrics.error_count,
                'last_update': self.metrics.last_update.isoformat()
            }
        }
