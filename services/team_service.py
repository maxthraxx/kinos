"""Team configuration and management service"""
import os
import json
from typing import Dict, Any, List, Optional, Tuple
from services.base_service import BaseService
from utils.exceptions import ServiceError
from utils.path_manager import PathManager

class TeamService(BaseService):
    """Manages team configurations and state"""

    def __init__(self, _):  # Keep parameter for compatibility but don't use it
        """Initialize with minimal dependencies"""
        super().__init__(_)
        self.active_team = None
        self.team_types = self._load_team_types()

    def _load_team_types(self) -> List[Dict[str, Any]]:
        """Load predefined team configurations"""
        try:
            teams = []
            teams_dir = PathManager.get_team_types_root()
        
            if not os.path.exists(teams_dir):
                self.logger.log("Teams directory not found", 'warning')
                return []
            
            # Load each team config
            for team_dir in os.listdir(teams_dir):
                # Check if it's a directory
                full_path = os.path.join(teams_dir, team_dir)
                if not os.path.isdir(full_path):
                    continue
            
                config_path = os.path.join(full_path, "config.json")
                if os.path.exists(config_path):
                    try:
                        with open(config_path, 'r', encoding='utf-8') as f:
                            config = json.load(f)
                            valid, error = self.validate_team_config(config)
                            if valid:
                                teams.append(config)
                            else:
                                self.logger.log(
                                    f"Invalid team config {team_dir}: {error}",
                                    'warning'
                                )
                    except Exception as e:
                        self.logger.log(
                            f"Error loading team {team_dir}: {str(e)}", 
                            'error'
                        )
            return teams

        except Exception as e:
            self.logger.log(f"Error loading predefined teams: {str(e)}", 'error')
            return []

    def get_team_config(self, team_id: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific team with flexible matching
        
        Args:
            team_id: Team identifier to match
        
        Returns:
            Team configuration dictionary or None if not found
        """
        try:
            # Normalize team_id for comparison
            normalized_team_id = team_id.lower().replace('team_', '').replace('-', '_')
            
            for team in self.team_types:
                # Normalize team's ID for comparison
                team_config_id = str(team.get('id', '')).lower().replace('team_', '').replace('-', '_')
                
                # Check for exact or normalized match
                if (team_config_id == normalized_team_id or 
                    normalized_team_id in team_config_id):
                    return team
            
            # Fallback logging if no match found
            self.logger.log(f"No team configuration found for: {team_id}", 'warning')
            return None
                
        except Exception as e:
            self.logger.log(f"Error getting team config for {team_id}: {str(e)}", 'error')
            return None

    def set_active_team(self, team_id: str) -> bool:
        """Set the active team configuration"""
        try:
            team_config = self.get_team_config(team_id)
            if not team_config:
                raise ServiceError(f"Team not found: {team_id}")
                
            self.active_team = team_config
            self.logger.log(f"Active team set to: {team_id}", 'success')
            return True
            
        except Exception as e:
            self.logger.log(f"Error setting active team: {str(e)}", 'error')
            return False

    def get_active_team(self) -> Optional[Dict[str, Any]]:
        """Get the currently active team configuration"""
        return self.active_team

    def get_team_agents(self, team_id: Optional[str] = None) -> List[str]:
        """Get list of agent names for a team"""
        try:
            # Use active team if no ID provided
            config = self.get_team_config(team_id) if team_id else self.active_team
            
            if not config:
                return []
                
            # Extract agent names
            agents = []
            for agent in config.get('agents', []):
                if isinstance(agent, dict):
                    agents.append(agent['name'])
                else:
                    agents.append(agent)
                    
            return agents
            
        except Exception as e:
            self.logger.log(f"Error getting team agents: {str(e)}", 'error')
            return []

    def validate_team_config(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate team configuration format"""
        try:
            # Check required fields
            required = ['id', 'name', 'agents']
            missing = [f for f in required if f not in config]
            if missing:
                return False, f"Missing required fields: {', '.join(missing)}"
                
            # Validate agents
            if not config['agents']:
                return False, "No agents defined"
                
            for agent in config['agents']:
                if isinstance(agent, dict):
                    if 'name' not in agent:
                        return False, f"Missing name in agent config: {agent}"
                elif not isinstance(agent, str):
                    return False, f"Invalid agent format: {agent}"
                    
            return True, None
            
        except Exception as e:
            return False, str(e)

    def load_team_prompts(self, team_id: str) -> Dict[str, str]:
        """Load all prompt files for a team"""
        try:
            prompts = {}
            team_dir = os.path.join(PathManager.get_teams_root(), team_id)
            
            if not os.path.exists(team_dir):
                self.logger.log(f"Team directory not found: {team_id}", 'warning')
                return prompts
                
            # Load each .md file as a prompt
            for file in os.listdir(team_dir):
                if file.endswith('.md'):
                    prompt_path = os.path.join(team_dir, file)
                    try:
                        with open(prompt_path, 'r', encoding='utf-8') as f:
                            agent_name = file[:-3]  # Remove .md extension
                            prompts[agent_name] = f.read()
                    except Exception as e:
                        self.logger.log(f"Error loading prompt {file}: {str(e)}", 'warning')
                        
            return prompts
            
        except Exception as e:
            self.logger.log(f"Error loading team prompts: {str(e)}", 'error')
            return {}

    def validate_team_prompts(self, team_id: str) -> Dict[str, List[str]]:
        """Validate all prompts for a team"""
        validation_results = {
            'valid': [],
            'invalid': [],
            'missing': []
        }
        
        try:
            team_config = self.get_team_config(team_id)
            if not team_config:
                return validation_results
                
            # Get expected agents
            expected_agents = self.get_team_agents(team_id)
            
            # Load and validate each prompt
            prompts = self.load_team_prompts(team_id)
            
            for agent in expected_agents:
                if agent not in prompts:
                    validation_results['missing'].append(agent)
                    continue
                    
                # Basic validation - check for required sections
                prompt_content = prompts[agent]
                required_sections = ['MISSION:', 'CONTEXT:', 'INSTRUCTIONS:', 'RULES:']
                
                if all(section in prompt_content for section in required_sections):
                    validation_results['valid'].append(agent)
                else:
                    validation_results['invalid'].append(agent)
                    
            return validation_results
            
        except Exception as e:
            self.logger.log(f"Error validating team prompts: {str(e)}", 'error')
            return validation_results

    def get_agent_prompt_path(self, team_id: str, agent_name: str) -> Optional[str]:
        """Get prompt file path for an agent in a team"""
        try:
            team_dir = os.path.join(PathManager.get_kinos_root(), "teams", team_id)
            prompt_file = os.path.join(team_dir, f"{agent_name.lower()}.md")
            
            if os.path.exists(prompt_file):
                return prompt_file
            return None
            
        except Exception as e:
            self.logger.log(f"Error getting agent prompt path: {str(e)}", 'error')
            return None

    def get_agent_prompt_path(self, team_id: str, agent_name: str) -> Optional[str]:
        """Get prompt file path for an agent in a team"""
        try:
            team_dir = os.path.join(PathManager.get_kinos_root(), "teams", team_id)
            prompt_file = os.path.join(team_dir, f"{agent_name.lower()}.md")
            
            if os.path.exists(prompt_file):
                return prompt_file
            return None
            
        except Exception as e:
            self.logger.log(f"Error getting agent prompt path: {str(e)}", 'error')
            return None

    def cleanup(self):
        """Cleanup team service resources"""
        try:
            self.active_team = None
            self.team_types.clear()
        except Exception as e:
            self.logger.log(f"Error cleaning up team service: {str(e)}", 'error')

    def list_teams(self) -> List[str]:
        """
        List all teams in the mission directory
        
        Returns:
            List of team names
        """
        try:
            # Get the mission directory
            mission_dir = os.getcwd()
            
            # List all directories in the mission directory
            all_dirs = [d for d in os.listdir(mission_dir) if os.path.isdir(os.path.join(mission_dir, d))]
            
            # Filter directories that start with "team_"
            team_dirs = [d[5:] for d in all_dirs if d.startswith("team_")]
            
            # Log the found teams
            if team_dirs:
                self.logger.log(f"Found teams: {', '.join(team_dirs)}", 'info')
            else:
                self.logger.log("No teams found in mission directory", 'warning')
            
            return team_dirs
        
        except Exception as e:
            self.logger.log(f"Error listing teams: {str(e)}", 'error')
            return []
