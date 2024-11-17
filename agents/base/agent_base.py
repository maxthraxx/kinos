"""
Base agent functionality providing core agent capabilities.
"""
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional, List
from utils.logger import Logger
from agents.base.file_handler import FileHandler
from utils.path_manager import PathManager

class AgentBase(ABC):
    """
    Abstract base class that all KinOS agents must inherit from.
    
    Provides core agent functionality including:
    - Lifecycle management
    - State tracking
    - Health monitoring
    - Dynamic timing
    - Error handling
    """
    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize base agent with configuration."""
        if not config:
            raise ValueError("Config is required")
            
        # Required fields - fail fast if missing
        if 'name' not in config:
            raise ValueError("Agent name is required in config")
        if 'type' not in config:
            raise ValueError("Agent type is required in config")
        if 'weight' not in config:
            raise ValueError("Agent weight is required in config")
        if 'mission_dir' not in config:
            raise ValueError("Mission directory is required in config")
            
        self.name = config['name']
        self.type = config['type']
        self.weight = config['weight']
        self.mission_dir = config['mission_dir']
        self.prompt_file = config.get('prompt_file')  # Optional since it's derived from name
        
        self.logger = Logger()
        self.running = True  # Always True from initialization
        self._init_state()
        
    def _init_state(self):
        """Initialize agent state tracking"""
        self.last_run = None
        self.last_change = None
        self.consecutive_no_changes = 0
        self.error_count = 0
        self.mission_files = {}

    def calculate_dynamic_interval(self) -> float:
        """
        Calculate the dynamic execution interval based on agent activity.

        Returns:
            float: Number of seconds to wait before next execution
        """
        try:
            base_interval = 60  # Default 1 minute
            min_interval = 60  # Minimum 1 minute
            max_interval = 3600  # Maximum 1 hour
            
            if self.consecutive_no_changes > 0:
                multiplier = min(10, 1.5 ** min(5, self.consecutive_no_changes))
                if self.error_count > 0:
                    multiplier *= 1.5
                interval = base_interval * multiplier
                return max(min_interval, min(max_interval, interval))
                
            return max(min_interval, base_interval)
            
        except Exception as e:
            self.logger.log(f"Error calculating interval: {str(e)}", 'error')
            return 60

    def is_healthy(self) -> bool:
        """
        Check if the agent is in a healthy state.

        Returns:
            bool: True if agent is healthy
        """
        try:
            if self.last_run:
                time_since_last = (datetime.now() - self.last_run).total_seconds()
                if time_since_last > 120:  # 2 minutes
                    return False
                    
            if self.consecutive_no_changes > 5:
                return False
                
            return True
            
        except Exception as e:
            self.logger.log(f"Error checking health: {str(e)}", 'error')
            return False

    def list_files(self) -> None:
        """List and track files that this agent should monitor"""
        try:
            # Use FileHandler to list files in mission directory
            file_handler = FileHandler(self.mission_dir, self.logger)
            self.mission_files = file_handler.list_files()
            
            # Log files being monitored
            if self.mission_files:
                self.logger.log(
                    f"[{self.name}] Monitoring {len(self.mission_files)} files:\n" + 
                    "\n".join(f"  - {os.path.relpath(f, self.mission_dir)}" for f in self.mission_files.keys()), 
                    'info'
                )
            else:
                self.logger.log(
                    f"[{self.name}] No files found to monitor in {self.mission_dir}", 
                    'warning'
                )
                
        except Exception as e:
            self.logger.log(
                f"[{self.name}] Error listing files: {str(e)}", 
                'error'
            )

    def get_prompt(self) -> str:
        """Get the current prompt using team context"""
        try:
            # Validate team context
            if not self.team:
                raise ValueError(f"No team context for agent {self.name}")
            
            # Get prompt using PathManager directly with team
            prompt_path = PathManager.get_prompt_file(self.name, self.team)
            
            if not prompt_path or not os.path.exists(prompt_path):
                raise ValueError(f"Prompt file not found for agent {self.name} in team {self.team}")
            
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
            
        except Exception as e:
            self.logger.log(f"Error retrieving prompt for team {self.team}: {str(e)}", 'error')
            raise

    @abstractmethod
    def _run_aider(self, prompt: str) -> Optional[str]:
        """Execute Aider with the given prompt"""
        pass

    def start(self) -> None:
        """Start the agent"""
        self.running = True
        self._init_state()
        self.logger.log(f"[{self.name}] Agent started", 'info')

    @property 
    def running(self):
        """Always return True"""
        return True

    @running.setter
    def running(self, value):
        """Ignore attempts to stop"""
        pass

    def stop(self) -> None:
        """Prevent agent from stopping"""
        pass  # Ne rien faire - empêcher l'arrêt

    @property 
    def running(self):
        """Always return True"""
        return True

    @running.setter
    def running(self, value):
        """Ignore attempts to stop"""
        pass


    def _format_files_context(self, files_context: Dict[str, Any]) -> str:
        """
        Format files context into readable string with validation
        
        Args:
            files_context: Dictionary mapping filenames to content
            
        Returns:
            str: Formatted string with file content blocks
            
        Raises:
            TypeError: If inputs are not correct types
            ValueError: If inputs are empty or invalid
            FileNotFoundError: If files don't exist
        """
        if not isinstance(files_context, dict):
            raise TypeError("files_context must be a dictionary")
        if not files_context:
            raise ValueError("files_context cannot be empty")
        if not self.mission_dir:
            raise ValueError("mission_dir not set")

        formatted = []
        for filename, content in files_context.items():
            if not isinstance(filename, str):
                raise TypeError(f"Filename must be string, got {type(filename)}")
                
            # Read file content if not already a string
            try:
                if not isinstance(content, str):
                    with open(filename, 'r', encoding='utf-8') as f:
                        content = f.read()
            except Exception as e:
                self.logger.log(f"Error reading file {filename}: {str(e)}", 'warning')
                continue
                
            if not os.path.exists(filename):
                self.logger.log(f"File not found: {filename}", 'warning')
                continue
                
            rel_path = os.path.relpath(filename, self.mission_dir)
            formatted.append(f"File: {rel_path}\n```\n{content}\n```\n")
            
        if not formatted:
            return "No readable files found"
            
        return "\n".join(formatted)

    def _call_llm(self, messages: List[Dict[str, str]], system: Optional[str] = None, **kwargs) -> Optional[str]:
        """Helper method for LLM calls using ModelRouter"""
        try:
            from services import init_services
            services = init_services(None)
            model_router = services['model_router']
            
            import asyncio
            response = asyncio.run(model_router.generate_response(
                messages=messages,
                system=system,
                **kwargs
            ))
            
            return response
            
        except Exception as e:
            self.logger.log(f"Error calling LLM: {str(e)}", 'error')
            return None

    async def _call_llm(self, messages: List[Dict[str, str]], system: Optional[str] = None, **kwargs) -> Optional[str]:
        """Helper method for LLM calls using ModelRouter"""
        try:
            from services import init_services
            services = init_services(None)
            model_router = services['model_router']
            
            response = await model_router.generate_response(
                messages=messages,
                system=system,
                **kwargs
            )
            
            return response
            
        except Exception as e:
            self.logger.log(f"Error calling LLM: {str(e)}", 'error')
            return None

    def cleanup(self):
        """Safe cleanup that never fails"""
        try:
            # Tenter le nettoyage mais ne jamais échouer
            if hasattr(self, 'mission_files'):
                self.mission_files.clear()
        except:
            pass

    def _get_agent_history_path(self, history_type: str = 'chat') -> str:
        """
        Get the history path for the current agent
        
        Args:
            history_type: Type of history (chat, input, output)
        
        Returns:
            str: Path to the history file/directory
        """
        try:
            from utils.path_manager import PathManager
            
            # Get team service to find the team
            from services import init_services
            services = init_services(None)
            team_service = services['team_service']
            
            # Find the team containing this agent
            agent_team_name = None
            for team in team_service.team_types:
                if self.name in team.get('agents', []):
                    agent_team_name = team.get('name')
                    break
        
            if not agent_team_name:
                agent_team_name = 'default'
            
            # Get history directory
            history_dir = PathManager.get_chat_history_path(team_name=agent_team_name)
            
            # Create specific history file/directory
            full_path = os.path.join(history_dir, f"{history_type}", f"{self.name}")
            
            # Ensure directory exists
            os.makedirs(full_path, exist_ok=True)
            
            return full_path
            
        except Exception as e:
            self.logger.log(f"Error getting agent history path: {str(e)}", 'error')
            return os.path.join(os.getcwd(), "history", self.name)
