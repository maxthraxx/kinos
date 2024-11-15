import sys
import threading
import queue
import time
import random
import argparse
import traceback
from cli.commands.commits import commits
from typing import List, Dict
import os
import json
from datetime import datetime
from utils.logger import Logger
from services.agent_service import AgentService
from utils.model_router import ModelRouter

def load_team_config(team_name: str) -> List[str]:
    """Load agent names from team config"""
    try:
        # Use PathManager to get KinOS root path
        from utils.path_manager import PathManager
        kinos_root = PathManager.get_kinos_root()
        
        config_path = os.path.join(kinos_root, "teams", team_name, "config.json")
        with open(config_path, 'r') as f:
            config = json.load(f)
            return [agent['name'] if isinstance(agent, dict) else agent 
                   for agent in config.get('agents', [])]
    except Exception as e:
        print(f"Error loading team config: {e}")
        return []

class AgentRunner(threading.Thread):
    """Thread class for running an agent and capturing output"""
    def __init__(self, agent_service: AgentService, team_agents: List[str], 
                 output_queue: queue.Queue, logger: Logger):
        super().__init__(daemon=True)
        self.agent_service = agent_service
        self.team_agents = team_agents  # Liste complète des agents de l'équipe
        self.output_queue = output_queue
        self.logger = logger
        self.running = True
        self.agent_type = 'aider'  # Default type

    def run(self):
        while self.running:
            try:
                # Sélectionner un nouvel agent aléatoirement à chaque itération
                from services import init_services
                services = init_services(None)
                phase_service = services['phase_service']
                phase_status = phase_service.get_status_info()
                current_phase = phase_status['phase']
                
                phase_weights = phase_service.get_phase_weights(current_phase)
                weights = [phase_weights.get(agent, 0.5) for agent in self.team_agents]
                self.agent_name = random.choices(self.team_agents, weights=weights, k=1)[0]
                
                self.logger.log(f"Selected agent for execution: {self.agent_name}", 'debug')

                # Log start of agent execution
                self.logger.log(f"Starting agent execution: {self.agent_name}", 'debug')
                
                # Capture start time
                start_time = datetime.now()
            
                # Initialize agent
                agent = self.agent_service.create_agent(self.agent_name)
                if not agent:
                    self.logger.log(f"Failed to create agent: {self.agent_name}", 'error')
                    continue
                    
                self.logger.log(f"Agent {self.agent_name} created successfully", 'debug')
                
                # Start agent
                try:
                    agent.start()
                    self.logger.log(f"Agent {self.agent_name} started", 'debug')
                except Exception as start_error:
                    self.logger.log(f"Error starting agent {self.agent_name}: {str(start_error)}", 'error')
                    continue
                
                # Run agent's main loop
                try:
                    agent.run()
                except Exception as run_error:
                    self.logger.log(f"Error in agent {self.agent_name} run loop: {str(run_error)}", 'error')
                
                # Calculate duration
                duration = (datetime.now() - start_time).total_seconds()
            
                # Put completion message in queue
                self.output_queue.put({
                    'thread_id': threading.get_ident(),
                    'agent_name': self.agent_name,
                    'status': 'completed',
                    'duration': duration,
                    'timestamp': datetime.now().isoformat()
                })
            
            except Exception as e:
                self.output_queue.put({
                    'thread_id': threading.get_ident(),
                    'agent_name': self.agent_name,
                    'status': 'error',
                    'error': str(e),
                    'traceback': traceback.format_exc(),
                    'timestamp': datetime.now().isoformat()
                })
            
                # Log detailed error
                self.logger.log(
                    f"Agent runner error for {self.agent_name}:\n{traceback.format_exc()}",
                    'error'
                )
            
                time.sleep(5)  # Brief pause on error

def initialize_team_structure(team_name: str, specific_name: str = None):
    """
    Initialise la structure de dossiers pour une équipe
    
    Args:
        team_name: Nom de l'équipe
        specific_name: Nom spécifique de l'agent (optionnel)
    """
    logger = Logger()
    
    # Créer la structure de base de l'équipe
    team_dir = os.path.join('teams', f'team_{team_name}')
    subdirs = ['history', 'prompts', 'map']
    
    for subdir in subdirs:
        os.makedirs(os.path.join(team_dir, subdir), exist_ok=True)
    
    # Fichiers par défaut
    default_files = {
        'map.md': '# Project Map\n\n## Overview\n',
        'todolist.md': '# Todo List\n\n## Pending Tasks\n',
        'demande.md': '# Mission Request\n\n## Objective\n',
        'directives.md': '# Project Directives\n\n## Guidelines\n'
    }
    
    # Créer les fichiers de base de l'équipe
    for filename, content in default_files.items():
        file_path = os.path.join(team_dir, filename)
        
        if not os.path.exists(file_path):
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.log(f"Created {filename}", 'info')
    
    # Créer le fichier .gitignore
    gitignore_path = os.path.join(team_dir, '.gitignore')
    gitignore_content = """# Ignore Aider and KinOS history files
.aider*
.kinos*
"""
    
    with open(gitignore_path, 'w', encoding='utf-8') as f:
        f.write(gitignore_content)
    logger.log("Created .gitignore", 'info')
    
    # Déterminer le chemin racine du projet
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Créer le fichier de configuration .kinos.config.json
    config_path = os.path.join(team_dir, '.kinos.config.json')
    
    # Configuration par défaut
    kinos_config = {
        "team_name": team_name,
        "team_type": "default",
        "paths": {
            "prompts": os.path.join(project_root, "teams", "prompts"),
            "history": os.path.join(team_dir, "history"),
            "map": os.path.join(team_dir, "map")
        },
        "agents": [],
        "created_at": datetime.now().isoformat()
    }
    
    # Écrire le fichier de configuration
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(kinos_config, f, indent=2)
    
    logger.log(f"Created .kinos.config.json for team {team_name}", 'info')

def run_team_loop(team_name: str, specific_name: str = None):
    """Main team execution loop"""
    logger = Logger()
    logger.log(f"🚀 Starting team loop for: {team_name}", 'debug')
    
    # Initialiser la structure de l'équipe
    initialize_team_structure(team_name, specific_name)

    agent_service = AgentService(None)
    
    # Load team configuration with enhanced logging
    agents = load_team_config(team_name)
    logger.log(f"Loaded {len(agents)} agents: {', '.join(agents)}", 'debug')
    
    if not agents:
        logger.log(f"No agents found for team: {team_name}", 'error')
        return
        
    logger.log(f"Starting team {team_name} with agents: {', '.join(agents)}")
    
    # Create output queue
    output_queue = queue.Queue()
    active_threads: Dict[int, AgentRunner] = {}
    
    logger.log("Entering main loop", 'debug')
    
    try:
        while True:  # Main loop
            logger.log("Checking agent initialization conditions", 'debug')
            
            # Clean up finished threads
            active_threads = {tid: runner for tid, runner in active_threads.items() 
                            if runner.is_alive()}
            
            logger.log(f"Active threads: {len(active_threads)}", 'debug')
            
            # Start new threads if needed
            while len(active_threads) < 3:
                # Get current phase weights
                from services import init_services
                services = init_services(None)
                phase_service = services['phase_service']
                phase_status = phase_service.get_status_info()
                current_phase = phase_status['phase']
                
                logger.log(f"Current phase: {current_phase}", 'debug')
                
                phase_weights = phase_service.get_phase_weights(current_phase)
                logger.log(f"Phase weights: {phase_weights}", 'debug')
                
                # Select random agent based on weights
                weights = [phase_weights.get(agent, 0.5) for agent in agents]
                agent_name = random.choices(agents, weights=weights, k=1)[0]
                
                logger.log(f"Selected agent: {agent_name}", 'debug')
                
                # Start new runner
                runner = AgentRunner(agent_service, agents, output_queue, logger)
                runner.start()
                active_threads[runner.ident] = runner
                logger.log(f"Started new agent runner (total: {len(active_threads)})")
            
            # Process output queue
            try:
                msg = output_queue.get(timeout=0.1)
                logger.log(f"Received message from queue: {msg['status']}", 'warning')
            except queue.Empty:
                pass
            
            time.sleep(0.1)  # Brief sleep to prevent CPU spinning
                
    except KeyboardInterrupt:
        logger.log("Stopping team execution...")
        
        # Stop all threads
        for runner in active_threads.values():
            runner.running = False
            
        # Wait for threads to finish
        for runner in active_threads.values():
            runner.join(timeout=1.0)
            
def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description='KinOS CLI')
    parser.add_argument('command', help='Command to execute')
    parser.add_argument('--name', help='Specific agent or team name for file context', required=True)
    parser.add_argument('--model', help='Model to use (e.g. "claude-3-haiku", "gpt-4", etc.)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    args = parser.parse_args()

    # Configuration du logger
    logger = Logger()
    if args.verbose:
        logger.set_level('debug')

    # Validation du nom
    if not args.name:
        logger.log("Error: --name is required", 'error')
        sys.exit(1)

    # Initialiser la structure de l'équipe
    initialize_team_structure(args.command, args.name)

    # If model is specified, update ModelRouter
    if args.model:
        try:
            from services import init_services
            services = init_services(None)
            model_router = services['model_router']
                    
            if not model_router.set_model(args.model):
                logger.log(f"Model {args.model} not found. Available models:", 'warning')
                for provider, models in model_router.get_available_models().items():
                    logger.log(f"{provider}: {', '.join(models)}", 'info')
                return
                        
        except Exception as e:
            logger.log(f"Error setting model: {str(e)}", 'error')
            return

    if args.command == "commits":
        if len(sys.argv) < 3:
            print("Usage: kin commits <generate>")
            return
        if sys.argv[2] == "generate":
            from utils.generate_commit_log import generate_commit_log
            generate_commit_log()
    else:
        # Execute team command
        team_name = args.command
        run_team_loop(team_name, args.name)

if __name__ == "__main__":
    main()
