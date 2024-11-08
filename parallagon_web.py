from agents import (SpecificationsAgent, ProductionAgent, 
    ManagementAgent, EvaluationAgent, SuiviAgent)
from parallagon_agent import ParallagonAgent
from flask import Flask, render_template, jsonify, request, make_response, redirect, url_for
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import threading
import time
import os
import git
from datetime import datetime
from typing import Dict, Any
from mission_service import MissionService
from file_manager import FileManager
from agents import (
    SpecificationsAgent,
    ProductionAgent,
    ManagementAgent,
    EvaluationAgent
)

class ParallagonWeb:
    # Log level colors
    LOG_COLORS = {
        'info': 'blue',
        'success': 'green', 
        'warning': 'orange',
        'error': 'red',
        'debug': 'gray'
    }

    def log_message(self, message: str, level: str = 'info') -> None:
        """Log a message with optional level"""
        try:
            # Format timestamp
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Get color for level
            color = self.LOG_COLORS.get(level, 'white')
            
            # Format the message
            formatted_message = f"[{timestamp}] [{level.upper()}] {message}"
            
            # Print to console
            print(formatted_message)
            
            # Log to file if needed
            try:
                with open('agent_operations.log', 'a', encoding='utf-8') as f:
                    f.write(f"{formatted_message}\n")
            except Exception as file_error:
                print(f"Error writing to log file: {file_error}")
                
        except Exception as e:
            # Fallback to basic print if logging fails
            print(f"Logging error: {e}")
            print(f"Original message: {message}")

    def _load_test_data(self):
        """Load test data from template file"""
        try:
            test_data_path = os.path.join("templates", "test_data", "demande_test_1.md")
            if not os.path.exists(test_data_path):
                self.log_message(f"Test data file not found: {test_data_path}", level='error')
                return ""
                
            with open(test_data_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.log_message(f"Error loading test data: {str(e)}", level='error')
            return ""

    def __init__(self, config):
        self.app = Flask(__name__)
        CORS(self.app)  # Enable CORS
        self.monitor_thread = None  # Add monitor thread tracking
        self.mission_service = MissionService()
        
        # Ensure missions directory exists
        os.makedirs("missions", exist_ok=True)
        self.limiter = Limiter(
            app=self.app,
            key_func=get_remote_address,
            default_limits=["1000 per minute"]
        )
        self.content_cache = {}
        self.last_modified = {}
        self.last_content = {}
        self.notifications_queue = []
        self.setup_error_handlers()
        # Add file paths configuration
        self.file_paths = {
            "demande": "demande.md",
            "specifications": "specifications.md",
            "management": "management.md", 
            "production": "production.md",
            "evaluation": "evaluation.md",
            "suivi": "suivi.md"
        }
        # Initialize FileManager with current mission
        first_mission = self.mission_service.get_all_missions()
        current_mission = first_mission[0]['name'] if first_mission else None
        
        self.file_manager = FileManager(
            self.file_paths,
            on_content_changed=self.handle_content_change
        )
        if current_mission:
            self.file_manager.current_mission = current_mission
        self.running = False
        self.agents = {}
        self.init_agents(config)
        self.setup_routes()

    def init_agents(self, config):
        """Initialisation des agents avec configuration standard"""
        try:
            self.log_message("Initializing agents...", level='info')
            
            # S'assurer que le dossier missions existe
            os.makedirs("missions", exist_ok=True)

            # Obtenir la liste des missions
            missions = self.mission_service.get_all_missions()
            if not missions:
                self.log_message("No missions available. Please create a mission first.", level='warning')
                return

            # Utiliser la première mission par défaut ou la mission courante si définie
            mission_name = getattr(self, 'current_mission', missions[0]['name']) if missions else None
            if not mission_name:
                raise ValueError("No mission available for initialization")
                
            # Create mission directory path
            mission_dir = os.path.join("missions", mission_name)
            
            base_config = {
                "check_interval": 10,
                "anthropic_api_key": config["anthropic_api_key"],
                "openai_api_key": config["openai_api_key"],
                "logger": self.log_message,
                "mission_name": mission_name
            }

            # Load prompts from files
            def load_prompt(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return f.read()
                except Exception as e:
                    self.log_message(f"Error loading prompt from {file_path}: {e}", level='error')
                    return ""

            # Créer les agents avec leurs prompts dédiés ET leurs rôles
            self.agents = {
                "Specification": SpecificationsAgent({
                    **base_config,
                    "name": "Specification",
                    "file_path": "specifications.md",
                    "prompt_file": "prompts/specifications.md",
                    "prompt": load_prompt("prompts/specifications.md")
                }),
                "Production": ProductionAgent({
                    **base_config,
                    "name": "Production", 
                    "file_path": os.path.join(mission_dir, "production.md"),
                    "prompt_file": "prompts/production.md",
                    "prompt": load_prompt("prompts/production.md")
                }),
                "Management": ManagementAgent({
                    **base_config,
                    "name": "Management",
                    "file_path": os.path.join(mission_dir, "management.md"),
                    "prompt_file": "prompts/management.md",
                    "prompt": load_prompt("prompts/management.md")
                }),
                "Evaluation": EvaluationAgent({
                    **base_config,
                    "name": "Evaluation",
                    "file_path": os.path.join(mission_dir, "evaluation.md"),
                    "prompt_file": "prompts/evaluation.md",
                    "prompt": load_prompt("prompts/evaluation.md")
                }),
                "Suivi": SuiviAgent({
                    **base_config,
                    "name": "Suivi", 
                    "file_path": os.path.join(mission_dir, "suivi.md"),
                    "prompt_file": "prompts/suivi.md",
                    "prompt": load_prompt("prompts/suivi.md")
                })
            }

            # Vérifier que tous les agents sont correctement initialisés
            for name, agent in self.agents.items():
                if not agent:
                    raise ValueError(f"Agent {name} non initialisé correctement")
                self.log_message(f"✓ Agent {name} initialisé", level='success')

            self.log_message("Agents initialized successfully", level='success')
            
        except Exception as e:
            self.log_message(f"Error initializing agents: {str(e)}", level='error')
            import traceback
            self.log_message(traceback.format_exc(), level='error')
            raise

    def handle_content_change(self, file_path: str, content: str, panel_name: str = None, flash: bool = False):
        """Handle content change notifications"""
        try:
            # Format timestamp consistently
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Get panel name from file path if not provided
            if not panel_name:
                panel_name = os.path.splitext(os.path.basename(file_path))[0].capitalize()
            
            # Create notification with all required fields
            notification = {
                'type': 'info',
                'message': f'Content updated in {panel_name}',
                'timestamp': timestamp,
                'panel': panel_name,
                'status': os.path.basename(file_path),
                'operation': 'flash_tab' if flash else 'update',
                'id': len(self.notifications_queue),
                'flash': flash  # Explicitly include flash flag
            }
            
            # Add to notifications queue
            self.notifications_queue.append(notification)
            
            # Update cache with validation
            if content and content.strip():
                self.content_cache[file_path] = content
                self.last_modified[file_path] = time.time()
                self.log_message(f"Content cache updated for {panel_name}", level='debug')
                
            return jsonify({'status': 'success'})
            
        except Exception as e:
            self.log_message(f"Error handling content change: {str(e)}", level='error')
            import traceback
            self.log_message(traceback.format_exc(), level='error')
            return jsonify({'error': str(e)}), 500

    def toggle_agent(self, agent_id: str, action: str) -> bool:
        """
        Toggle an individual agent's state
        
        Args:
            agent_id: ID of the agent to toggle
            action: 'start' or 'stop'
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            agent_name = agent_id.capitalize()
            if agent_name not in self.agents:
                self.log_message(f"Agent {agent_id} not found", level='error')
                return False
                
            agent = self.agents[agent_name]
            
            if action == 'start':
                if not agent.running:
                    agent.start()
                    thread = threading.Thread(
                        target=agent.run,
                        daemon=True,
                        name=f"Agent-{agent_name}"
                    )
                    thread.start()
                    self.log_message(f"Agent {agent_name} started", level='success')
            elif action == 'stop':
                if agent.running:
                    agent.stop()
                    self.log_message(f"Agent {agent_name} stopped", level='info')
            
            return True
            
        except Exception as e:
            self.log_message(f"Failed to toggle agent {agent_id}: {str(e)}", level='error')
            return False

    def setup_routes(self):
        @self.app.route('/api/missions/<int:mission_id>/content', methods=['GET'])
        def get_mission_content(mission_id):
            try:
                mission = self.mission_service.get_mission(mission_id)
                if not mission:
                    return jsonify({'error': 'Mission not found'}), 404
                    
                content = {}
                for file_type, file_path in mission['files'].items():
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content[file_type] = f.read()
                    except Exception as e:
                        self.log_message(f"Error reading {file_type} file: {str(e)}", level='error')
                        content[file_type] = ""
                        
                return jsonify(content)
                
            except Exception as e:
                self.log_message(f"Error getting mission content: {str(e)}", level='error')
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/missions/<int:mission_id>/content/<file_type>', methods=['POST'])
        def save_mission_content(mission_id, file_type):
            try:
                data = request.get_json()
                if not data or 'content' not in data:
                    return jsonify({'error': 'Content is required'}), 400
                    
                success = self.mission_service.save_mission_file(
                    mission_id,
                    file_type,
                    data['content']
                )
                
                if not success:
                    return jsonify({'error': 'Failed to save content'}), 500
                    
                self.log_message(f"Saved {file_type} content for mission {mission_id}", level='success')
                return jsonify({'status': 'success'})
                
            except Exception as e:
                self.log_message(f"Error saving mission content: {str(e)}", level='error')
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/missions', methods=['GET'])
        def get_missions():
            try:
                missions = self.mission_service.get_all_missions()
                if missions is None:
                    return jsonify({'error': 'Failed to fetch missions'}), 500
                    
                return jsonify(missions)
                
            except Exception as e:
                self.log_message(f"Error getting missions: {str(e)}", level='error')
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/missions/validate-directory', methods=['POST'])
        def validate_mission_directory():
            """Validate that a directory contains required mission files"""
            try:
                data = request.get_json()
                if not data or 'path' not in data:
                    return jsonify({'error': 'Path is required'}), 400
                    
                path = data['path']
                
                # Verify only required files at root level
                required_files = [
                    "demande.md",
                    "specifications.md", 
                    "management.md",
                    "production.md",
                    "evaluation.md",
                    "suivi.md"
                ]
                
                missing_files = []
                for file in required_files:
                    if not os.path.isfile(os.path.join(path, file)):
                        missing_files.append(file)
                        
                if missing_files:
                    return jsonify({
                        'error': f'Dossier invalide. Fichiers manquants : {", ".join(missing_files)}'
                    }), 400
                    
                return jsonify({'status': 'valid'})
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/missions/get-directory-path', methods=['POST'])
        def get_directory_path():
            """Get full path for a directory selected in the frontend"""
            try:
                data = request.get_json()
                if not data or 'name' not in data:
                    return jsonify({'error': 'Directory name is required'}), 400
                    
                directory_name = data['name']
                
                # Chercher le dossier dans les emplacements possibles
                possible_paths = [
                    os.path.abspath(directory_name),  # Chemin absolu
                    os.path.join(os.getcwd(), directory_name),  # Relatif au dossier courant
                    os.path.expanduser(f"~/{directory_name}"),  # Dans le home
                    os.path.join(os.path.expanduser("~/Documents"), directory_name),  # Dans Documents
                    os.path.join(os.path.expanduser("~"), "Documents", directory_name)  # Autre syntaxe pour Documents
                ]
                
                # Debug log
                self.log_message(f"Searching for directory: {directory_name}")
                self.log_message(f"Possible paths: {possible_paths}")
                
                # Trouver le premier chemin valide
                for path in possible_paths:
                    if os.path.isdir(path):
                        self.log_message(f"Found valid path: {path}")
                        return jsonify({'path': path})
                
                self.log_message(f"No valid path found for: {directory_name}", level='error')        
                return jsonify({'error': 'Directory not found'}), 404
                
            except Exception as e:
                self.log_message(f"Error getting directory path: {str(e)}", level='error')
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/missions/link', methods=['POST'])
        def create_mission_link():
            """Create a mission from an external directory"""
            try:
                data = request.get_json()
                if not data or 'path' not in data:
                    return jsonify({'error': 'External path is required'}), 400
                    
                external_path = data['path']
                mission_name = data.get('name')  # Optional
                
                # Create mission link
                mission = self.mission_service.create_mission_link(
                    external_path=external_path,
                    mission_name=mission_name
                )
                
                self.log_message(
                    f"Created link to external mission at {external_path}", 
                    level='success'
                )
                return jsonify(mission), 201
                
            except Exception as e:
                self.log_message(f"Error creating mission link: {str(e)}", level='error')
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/missions', methods=['POST'])
        def create_mission():
            try:
                data = request.get_json()
                if not data or 'name' not in data:
                    return jsonify({'error': 'Name is required'}), 400
                    
                # Validate mission name
                mission_name = data['name'].strip()
                if not mission_name:
                    return jsonify({'error': 'Mission name cannot be empty'}), 400
                    
                # Check if mission already exists
                if self.mission_service.mission_exists(mission_name):
                    return jsonify({'error': 'Mission with this name already exists'}), 409
                    
                # Create mission in database
                mission = self.mission_service.create_mission(
                    name=mission_name,
                    description=data.get('description')
                )
                
                # Update FileManager's current mission
                self.file_manager.current_mission = mission_name
                
                # Create mission files
                if not self.file_manager.create_mission_files(mission_name):
                    # Rollback database creation if file creation fails
                    self.mission_service.delete_mission(mission['id'])
                    self.file_manager.current_mission = None
                    return jsonify({'error': 'Failed to create mission files'}), 500
                
                self.log_message(f"Mission '{mission_name}' created successfully", level='success')
                return jsonify(mission), 201
                
            except Exception as e:
                self.log_message(f"Error creating mission: {str(e)}", level='error')
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/missions/<int:mission_id>', methods=['GET'])
        def get_mission(mission_id):
            try:
                mission = self.mission_service.get_mission(mission_id)
                if not mission:
                    return jsonify({'error': 'Mission not found'}), 404
                    
                # Update FileManager's current mission
                self.file_manager.current_mission = mission['name']
                
                # Update agent paths when mission changes
                self.update_agent_paths(mission['name'])
                
                # Stop agents if they're running
                was_running = self.running
                if was_running:
                    self.stop_agents()
                    
                # Start agents again if they were running
                if was_running:
                    self.start_agents()
                    
                self.log_message(f"Mission {mission['name']} loaded successfully", level='success')
                return jsonify(mission)
                
            except Exception as e:
                self.log_message(f"Error getting mission: {str(e)}", level='error')
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/missions/<int:mission_id>', methods=['PUT'])
        def update_mission(mission_id):
            try:
                data = request.get_json()
                mission = self.mission_service.update_mission(
                    mission_id,
                    name=data.get('name'),
                    description=data.get('description'),
                    status=data.get('status')
                )
                if not mission:
                    return jsonify({'error': 'Mission not found'}), 404
                    
                self.log_message(f"Mission {mission_id} updated", level='success')
                return jsonify(mission)
                
            except Exception as e:
                self.log_message(f"Error updating mission: {str(e)}", level='error')
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/agent/<agent_id>/<action>', methods=['POST'])
        def control_agent(agent_id, action):
            """Control (start/stop) a specific agent"""
            try:
                # Debug logs
                self.log_message(f"Agent control request: {agent_id} - {action}", level='debug')
                
                # Validate action
                if action not in ['start', 'stop']:
                    return jsonify({'error': 'Invalid action'}), 400
                    
                # Convert agent_id to proper case and normalize
                agent_name = agent_id.capitalize()
                
                # Handle plural forms for agent names
                if agent_name.endswith('s'):  # Remove trailing 's' for agents
                    agent_name = agent_name[:-1]
                
                # Debug log
                self.log_message(f"Looking for agent: {agent_name}", level='debug')
                self.log_message(f"Available agents: {list(self.agents.keys())}", level='debug')
                
                if agent_name not in self.agents:
                    return jsonify({'error': f'Agent {agent_id} not found (normalized: {agent_name})'}), 404
                    
                agent = self.agents[agent_name]
                
                if action == 'start':
                    if not agent.running:
                        agent.start()
                        thread = threading.Thread(
                            target=agent.run,
                            daemon=True,
                            name=f"Agent-{agent_name}"
                        )
                        thread.start()
                        self.log_message(f"Agent {agent_name} started", level='success')
                else:  # stop
                    if agent.running:
                        agent.stop()
                        self.log_message(f"Agent {agent_name} stopped", level='success')
                        
                return jsonify({
                    'status': 'success',
                    'message': f'Agent {agent_name} {action}ed successfully',
                    'running': agent.running
                })
                
            except Exception as e:
                self.log_message(f"Error controlling agent {agent_id}: {str(e)}", level='error')
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/agents/status', methods=['GET'])
        def get_agents_status():
            """Get status of all agents"""
            try:
                status = {
                    name.lower(): {
                        'running': agent.running,
                        'last_run': agent.last_run.isoformat() if agent.last_run else None,
                        'last_change': agent.last_change.isoformat() if agent.last_change else None
                    }
                    for name, agent in self.agents.items()
                }
                return jsonify(status)
                
            except Exception as e:
                self.log_message(f"Failed to get agents status: {str(e)}", level='error')
                return jsonify({'error': str(e)}), 500

        @self.app.route('/clean')
        def clean_interface():
            try:
                with open('production.md', 'r', encoding='utf-8') as f:
                    content = f.read()
                with open('suivi.md', 'r', encoding='utf-8') as f:
                    suivi_content = f.read()
                with open('demande.md', 'r', encoding='utf-8') as f:
                    demande_content = f.read()
                return render_template('clean.html', 
                             content=content, 
                             suivi_content=suivi_content,
                             demande_content=demande_content)
            except Exception as e:
                return f"Error loading content: {str(e)}", 500

        @self.app.route('/api/missions/<int:mission_id>/test-data', methods=['POST'])
        def load_test_data(mission_id):
            """Load test data into the current mission"""
            try:
                # Vérifier que la mission existe
                mission = self.mission_service.get_mission(mission_id)
                if not mission:
                    return jsonify({'error': 'Mission not found'}), 404

                # Load test data from file
                test_data = self._load_test_data()

                # Sauvegarder dans le fichier demande.md de la mission
                mission_path = os.path.join("missions", mission['name'])
                demande_path = os.path.join(mission_path, "demande.md")

                try:
                    with open(demande_path, 'w', encoding='utf-8') as f:
                        f.write(test_data)

                    self.log_message(f"✓ Données de test chargées pour la mission {mission['name']}", level='success')
                    return jsonify({'status': 'success'})

                except Exception as write_error:
                    self.log_message(f"❌ Erreur d'écriture des données de test: {str(write_error)}", level='error')
                    return jsonify({'error': f'File write error: {str(write_error)}'}), 500

            except Exception as e:
                self.log_message(f"❌ Erreur chargement données test: {str(e)}", level='error')
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/missions/<int:mission_id>/reset', methods=['POST'])
        def reset_mission_files(mission_id):
            try:
                mission = self.mission_service.get_mission(mission_id)
                if not mission:
                    return jsonify({'error': 'Mission not found'}), 404

                # Liste des fichiers à réinitialiser (excluant demande.md)
                files_to_reset = {
                    "specifications": "specifications.md",
                    "management": "management.md",
                    "production": "production.md", 
                    "evaluation": "evaluation.md",
                    "suivi": "suivi.md"
                }

                # Réinitialiser chaque fichier de la mission sauf demande.md
                for file_type, file_name in files_to_reset.items():
                    initial_content = self.file_manager._get_initial_content(file_type)
                    success = self.mission_service.save_mission_file(
                        mission_id,
                        file_type,
                        initial_content
                    )
                    if not success:
                        return jsonify({'error': f'Failed to reset {file_name}'}), 500

                self.log_message(f"Files reset for mission {mission['name']} (excluding demande.md)", level='success')
                return jsonify({'status': 'success'})
                
            except Exception as e:
                self.log_message(f"Error resetting files: {str(e)}", level='error')
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/health')
        def health_check():
            return jsonify({
                'status': 'healthy',
                'running': self.running,
                'agents': {
                    name: {
                        'running': agent.should_run(),
                        'last_update': agent.last_update
                    }
                    for name, agent in self.agents.items()
                }
            })


        @self.app.route('/editor')
        def editor_interface():
            try:
                content = self.file_manager.read_file("production")
                if content is None:
                    content = ""
                    
                suivi_content = self.file_manager.read_file("suivi")
                if suivi_content is None:
                    suivi_content = ""
                    
                return render_template('editor.html', 
                                     content=content, 
                                     suivi_content=suivi_content)
            except Exception as e:
                self.log_message(f"Error loading editor: {str(e)}", level='error')
                return render_template('editor.html',
                                     content="Error loading content",
                                     suivi_content="Error loading suivi content")

        @self.app.route('/')
        def home():
            """Redirect root to editor interface"""
            return redirect(url_for('editor_interface'))

        @self.app.route('/api/status')
        def get_status():
            return jsonify({
                'running': self.running,
                'agents': {name: agent.should_run() for name, agent in self.agents.items()}
            })

        @self.app.route('/api/content', methods=['GET'])
        def handle_content():
            try:
                # Skip if no mission selected
                if not hasattr(self, 'current_mission') or not self.current_mission:
                    return jsonify({})  # Return empty object if no mission

                content = {}
                mission_dir = os.path.join("missions", self.current_mission)

                # List of files to check
                files_to_check = {
                    'demande': 'demande.md',
                    'specifications': 'specifications.md', 
                    'management': 'management.md',
                    'production': 'production.md',
                    'evaluation': 'evaluation.md',
                    'suivi': 'suivi.md'
                }

                # Check each file
                for panel_id, filename in files_to_check.items():
                    file_path = os.path.join(mission_dir, filename)
                    try:
                        if os.path.exists(file_path):
                            # Get last modified time
                            last_modified = os.path.getmtime(file_path)
                            
                            # Check if file has been modified
                            if panel_id not in self.last_modified or self.last_modified[panel_id] != last_modified:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    new_content = f.read()
                                    
                                # If content has changed
                                if panel_id not in self.content_cache or self.content_cache[panel_id] != new_content:
                                    self.log_message(
                                        f"File changed: {filename} in mission {self.current_mission}",
                                        level='info'
                                    )
                                    content[panel_id] = new_content
                                    self.content_cache[panel_id] = new_content
                                    self.last_modified[panel_id] = last_modified
                                    
                    except Exception as e:
                        self.log_message(f"Error reading {filename}: {str(e)}", level='error')
                        # Continue with other files even if one fails

                return jsonify(content)
                    
            except Exception as e:
                self.log_message(f"Error handling content: {str(e)}", level='error')
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/start', methods=['POST'])
        def start_agents():
            self.start_agents()
            return jsonify({'status': 'started'})

        @self.app.route('/api/stop', methods=['POST'])
        def stop_agents():
            self.stop_agents()
            return jsonify({'status': 'stopped'})

        @self.app.route('/api/agent/<agent_id>/prompt', methods=['GET'])
        def get_agent_prompt(agent_id):
            """Get the prompt for a specific agent"""
            try:
                agent_name = agent_id.capitalize()
                if agent_name not in self.agents:
                    return jsonify({'error': 'Agent not found'}), 404
                    
                prompt = self.agents[agent_name].get_prompt()
                return jsonify({'prompt': prompt})
                
            except Exception as e:
                self.log_message(f"Error getting agent prompt: {str(e)}", level='error')
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/agent/<agent_id>/prompt', methods=['POST'])
        def save_agent_prompt(agent_id):
            """Save the prompt for a specific agent"""
            try:
                data = request.get_json()
                if not data or 'prompt' not in data:
                    return jsonify({'error': 'Prompt is required'}), 400
                    
                agent_name = agent_id.capitalize()
                if agent_name not in self.agents:
                    return jsonify({'error': 'Agent not found'}), 404
                    
                success = self.agents[agent_name].save_prompt(data['prompt'])
                if success:
                    self.log_message(f"Prompt saved for agent {agent_name}", level='success')
                    return jsonify({'status': 'success'})
                else:
                    return jsonify({'error': 'Failed to save prompt'}), 500
                    
            except Exception as e:
                self.log_message(f"Error saving agent prompt: {str(e)}", level='error')
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/changes')
        def get_changes():
            """Return and clear pending changes"""
            try:
                # Obtenir le timestamp actuel
                current_time = datetime.now()
                
                # Convertir les timestamps des notifications en objets datetime pour comparaison
                recent_notifications = []
                for n in self.notifications_queue:
                    try:
                        # Convertir le timestamp de la notification en datetime
                        notif_time = datetime.strptime(n['timestamp'], "%H:%M:%S")
                        # Utiliser la date d'aujourd'hui avec l'heure de la notification
                        notif_datetime = current_time.replace(
                            hour=notif_time.hour,
                            minute=notif_time.minute,
                            second=notif_time.second
                        )
                        
                        # Garder seulement les notifications des 3 dernières secondes
                        if (current_time - notif_datetime).total_seconds() <= 3:
                            recent_notifications.append(n)
                            
                    except ValueError as e:
                        self.log_message(f"Invalid timestamp format in notification: {e}", level='error')
                        continue
                
                # Debug logging
                if recent_notifications:
                    self.log_message(
                        f"Sending {len(recent_notifications)} notifications", 
                        level='debug'
                    )
                
                # Clear queue after getting notifications
                self.notifications_queue = []
                
                return jsonify(recent_notifications)
                    
            except Exception as e:
                self.log_message(f"Error in get_changes: {str(e)}", level='error')
                return jsonify([])

        @self.app.route('/api/notifications', methods=['GET', 'POST'])
        @self.limiter.limit("500 per minute")
        def handle_notifications():
            """Handle notifications GET and POST"""
            if request.method == 'GET':
                """Get pending notifications"""
                try:
                    # Récupérer les notifications en attente
                    notifications = []
                    
                    # Ajouter les notifications de la queue
                    while self.notifications_queue:
                        notification = self.notifications_queue.pop(0)
                        notifications.append(notification)
                        self.log_message(f"Sending notification: {notification}", level='debug')
                        
                    # Debug log
                    if notifications:
                        self.log_message(f"Sending {len(notifications)} notifications to frontend", level='debug')
                        
                    return jsonify(notifications)
                    
                except Exception as e:
                    self.log_message(f"Error getting notifications: {str(e)}", level='error')
                    # Retourner une liste vide au lieu d'une erreur 500
                    return jsonify([])
                    
            else:  # POST
                """Handle content change notifications from agents"""
                try:
                    data = request.get_json()
                    self.log_message(f"Received notification: {data}", level='debug')
                    
                    # Validate required fields
                    required_fields = ['file_path', 'content', 'panel', 'message']
                    if not all(field in data for field in required_fields):
                        missing = [f for f in required_fields if f not in data]
                        self.log_message(f"Missing required fields: {missing}", level='error')
                        return jsonify({'error': f'Missing required fields: {missing}'}), 400
                        
                    # Add notification to queue with explicit flash and status
                    notification = {
                        'type': data.get('type', 'info'),
                        'message': data['message'],
                        'panel': data['panel'],
                        'content': data['content'],
                        'flash': data.get('flash', True),
                        'timestamp': datetime.now().strftime("%H:%M:%S"),
                        'id': len(self.notifications_queue),
                        'status': data['file_path']  # Important for tab flashing
                    }
                    
                    self.log_message(f"Adding notification to queue: {notification}", level='debug')
                    self.notifications_queue.append(notification)
                    
                    # Update content cache
                    if data['content'].strip():
                        self.content_cache[data['file_path']] = data['content']
                        self.last_modified[data['file_path']] = time.time()
                        
                    return jsonify({'status': 'success'})
                    
                except Exception as e:
                    self.log_message(f"Error handling notification: {str(e)}", level='error')
                    return jsonify({'error': str(e)}), 500

        @self.app.route('/api/demande', methods=['POST'])
        def save_demande():
            try:
                data = request.get_json()
                
                # Debug logs
                self.log_message(f"Received save request with data: {data}", level='debug')
                
                if not data or 'content' not in data:
                    self.log_message("❌ Pas de contenu fourni pour la demande", level='error')
                    return jsonify({'error': 'No content provided'}), 400

                # Vérification explicite de la mission
                if 'missionId' not in data or 'missionName' not in data:
                    self.log_message("❌ Informations de mission manquantes", level='error')
                    return jsonify({'error': 'Mission information missing'}), 400

                # Mise à jour du FileManager avec le nom de la mission
                self.file_manager.current_mission = data['missionName']

                # Construction du chemin avec vérification
                mission_path = os.path.join("missions", data['missionName'])
                if not os.path.exists(mission_path):
                    os.makedirs(mission_path, exist_ok=True)
                    self.log_message(f"✓ Dossier mission créé: {mission_path}", level='info')

                demande_path = os.path.join(mission_path, "demande.md")
                
                # Log du chemin pour debug
                self.log_message(f"Saving to path: {demande_path}", level='debug')

                # Écriture du fichier
                try:
                    with open(demande_path, 'w', encoding='utf-8') as f:
                        f.write(data['content'])
                    
                    self.log_message("✓ Demande sauvegardée", level='success')
                    
                    # Notification du changement
                    self.handle_content_change(
                        'demande.md',
                        data['content'],
                        panel_name='Demande'
                    )
                    return jsonify({'status': 'success', 'success': True})
                    
                except Exception as write_error:
                    self.log_message(f"❌ Erreur d'écriture: {str(write_error)}", level='error')
                    return jsonify({'error': f'File write error: {str(write_error)}'}), 500
                    
            except Exception as e:
                self.log_message(f"❌ Erreur générale: {str(e)}", level='error')
                return jsonify({'error': str(e)}), 500

    def run(self, host='0.0.0.0', port=5000, **kwargs):
        """Run the Flask application with optional configuration parameters"""
        self.app.run(host=host, port=port, **kwargs)

    def monitor_agents(self):
        """Monitor agents and restart them if they crash"""
        while self.running:
            try:
                for name, agent in self.agents.items():
                    if agent.running:
                        # Check if agent is active but stuck
                        if (agent.last_run and 
                            (datetime.now() - agent.last_run).seconds > 30):  # 30s timeout
                            self.log_message(
                                f"Agent {name} seems stuck, restarting...", 
                                level='warning'
                            )
                            # Restart agent
                            agent.stop()
                            agent.start()
                            thread = threading.Thread(
                                target=agent.run,
                                daemon=True,
                                name=f"Agent-{name}"
                            )
                            thread.start()
                time.sleep(5)  # Check every 5 seconds
            except Exception as e:
                self.log_message(f"Error in monitor_agents: {str(e)}", level='error')
                if not self.running:  # Exit if system is shutting down
                    break

    def monitor_agents(self):
        """Monitor agents and restart them if they crash"""
        while self.running:
            try:
                for name, agent in self.agents.items():
                    if agent.running:
                        # Check if agent is active but stuck
                        if (agent.last_run and 
                            (datetime.now() - agent.last_run).seconds > 30):  # 30s timeout
                            self.log_message(
                                f"Agent {name} seems stuck, restarting...", 
                                level='warning'
                            )
                            # Restart agent
                            agent.stop()
                            agent.start()
                            thread = threading.Thread(
                                target=agent.run,
                                daemon=True,
                                name=f"Agent-{name}"
                            )
                            thread.start()
                time.sleep(5)  # Check every 5 seconds
            except Exception as e:
                self.log_message(f"Error in monitor_agents: {str(e)}", level='error')

    def start_agents(self):
        """Start all agents"""
        try:
            self.log_message("🚀 Démarrage des agents...", level='info')
            self.running = True
            
            # Start monitor thread if not already running
            if not self.monitor_thread or not self.monitor_thread.is_alive():
                self.monitor_thread = threading.Thread(
                    target=self.monitor_agents,
                    daemon=True,
                    name="AgentMonitor"
                )
                self.monitor_thread.start()
            
            # Start agents in separate threads
            for name, agent in self.agents.items():
                try:
                    agent.start()  # Set agent running flag
                    thread = threading.Thread(
                        target=agent.run,
                        daemon=True,
                        name=f"Agent-{name}"
                    )
                    thread.start()
                    self.log_message(f"✓ Agent {name} démarré", level='success')
                except Exception as e:
                    self.log_message(f"❌ Erreur démarrage agent {name}: {str(e)}", level='error')
                    
            self.log_message("✨ Tous les agents sont actifs", level='success')
            
        except Exception as e:
            self.log_message(f"❌ Erreur globale: {str(e)}", level='error')
            raise

    def stop_agents(self):
        """Stop all agents and update loop"""
        try:
            self.running = False
            
            # Stop each agent individually
            for name, agent in self.agents.items():
                try:
                    agent.stop()
                    self.log_message(f"Agent {name} stopped", level='info')
                except Exception as e:
                    self.log_message(f"Error stopping agent {name}: {str(e)}", level='error')
            
            # Clear running agents set
            self.runningAgents.clear()
            
            # Wait for monitor thread to finish
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=2)
            
            self.log_message("All agents stopped", level='success')
            
        except Exception as e:
            self.log_message(f"Error in stop_agents: {str(e)}", level='error')
            raise

    def safe_operation(self, operation_func):
        """Decorator for safe operation execution with recovery"""
        def wrapper(*args, **kwargs):
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    return operation_func(*args, **kwargs)
                except Exception as e:
                    retry_count += 1
                    self.log_message(
                        str(e),
                        operation=operation_func.__name__,
                        status=f"RETRY {retry_count}/{max_retries}"
                    )
                    
                    if retry_count == max_retries:
                        self.log_message(
                            "Operation failed permanently",
                            operation=operation_func.__name__,
                            status="FAILED"
                        )
                        raise
                    
                    time.sleep(1)  # Wait before retry
                    
        return wrapper

    def check_content_updates(self):
        """Check for content updates"""
        try:
            # Read current content of all files
            current_content = {}
            for file_name, path in self.file_paths.items():
                content = self.file_manager.read_file(file_name)
                if content is not None:
                    current_content[file_name] = content

            # Compare with last known content
            if not hasattr(self, 'last_content'):
                self.last_content = {}

            # Check changes for each file
            for file_name, content in current_content.items():
                if content is None:
                    continue
                    
                if (file_name not in self.last_content or 
                    content != self.last_content[file_name]):
                    # Content modified or new file
                    self.handle_content_change(
                        file_name, 
                        content,
                        panel_name=file_name.split('.')[0].capitalize()
                    )
                    self.last_content[file_name] = content
                    self.log_message(f"Content updated in {file_name}")

        except Exception as e:
            self.log_message(f"Error checking content updates: {str(e)}", level='error')

    def setup_error_handlers(self):
        @self.app.errorhandler(404)
        def not_found_error(error):
            self.log_message(f"404 Error: {str(error)}", level='error')
            return jsonify({'error': 'Resource not found'}), 404

        @self.app.errorhandler(500)
        def internal_error(error):
            self.log_message(f"500 Error: {str(error)}", level='error')
            import traceback
            self.log_message(traceback.format_exc(), level='error')
            return jsonify({'error': 'Internal server error'}), 500

        @self.app.errorhandler(Exception)
        def handle_exception(error):
            self.log_message(f"Unhandled Exception: {str(error)}", level='error')
            import traceback
            self.log_message(traceback.format_exc(), level='error')
            return jsonify({'error': str(error)}), 500

    def safe_operation(self, operation_func):
        """Decorator for safe operation execution with recovery"""
        def wrapper(*args, **kwargs):
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    return operation_func(*args, **kwargs)
                except Exception as e:
                    retry_count += 1
                    self.log_message(
                        str(e),
                        operation=operation_func.__name__,
                        status=f"RETRY {retry_count}/{max_retries}"
                    )
                    
                    if retry_count == max_retries:
                        self.log_message(
                            "Operation failed permanently",
                            operation=operation_func.__name__,
                            status="FAILED"
                        )
                        raise
                    
                    time.sleep(1)  # Wait before retry
                    
        return wrapper

    def shutdown(self):
        """Graceful shutdown of the application"""
        try:
            # Stop all agents
            self.stop_agents()
            
            # Clear caches
            self.content_cache.clear()
            self.last_modified.clear()
            
            self.log_message("Application shutdown complete")
        except Exception as e:
            self.log_message(f"Error during shutdown: {str(e)}")

    def update_agent_paths(self, mission_name: str) -> None:
        """Update file paths for all agents when mission changes"""
        try:
            # Ensure mission directory exists
            mission_dir = os.path.abspath(os.path.join("missions", mission_name))
            os.makedirs(mission_dir, exist_ok=True)
            
            self.log_message(f"Updating agent paths for mission: {mission_name}", level='debug')
            
            # Stop agents if running
            was_running = self.running
            if was_running:
                self.stop_agents()
            
            # Update paths for each agent with correct file mappings
            agent_files = {
                "Specification": {
                    "main": os.path.join(mission_dir, "specifications.md"),
                    "watch": [
                        os.path.join(mission_dir, "demande.md"),
                        os.path.join(mission_dir, "production.md")
                    ]
                },
                "Production": {
                    "main": os.path.join(mission_dir, "production.md"),
                    "watch": [
                        os.path.join(mission_dir, "specifications.md"),
                        os.path.join(mission_dir, "evaluation.md")
                    ]
                },
                "Management": {
                    "main": os.path.join(mission_dir, "management.md"),
                    "watch": [
                        os.path.join(mission_dir, "specifications.md"),
                        os.path.join(mission_dir, "production.md"),
                        os.path.join(mission_dir, "evaluation.md")
                    ]
                },
                "Evaluation": {
                    "main": os.path.join(mission_dir, "evaluation.md"),
                    "watch": [
                        os.path.join(mission_dir, "specifications.md"),
                        os.path.join(mission_dir, "production.md")
                    ]
                },
            }
            
            for name, agent in self.agents.items():
                try:
                    if name in agent_files:
                        config = agent_files[name]
                        # Pass pre-built absolute paths
                        agent.update_paths(
                            config["main"],
                            config["watch"]
                        )
                except Exception as e:
                    self.log_message(f"Error updating paths for {name}: {str(e)}", level='error')
            
            # Restart agents if they were running
            if was_running:
                self.start_agents()
                
            self.log_message(f"✓ Agent paths updated for mission: {mission_name}", level='success')
            
        except Exception as e:
            self.log_message(f"❌ Error updating agent paths: {str(e)}", level='error')

    @self.app.route('/explorer')
    def explorer():
        """Explorer interface"""
        return render_template('explorer.html')

    @self.app.route('/api/missions/<int:mission_id>/files')
    def get_mission_files(mission_id):
        """Get all text files in mission directory"""
        try:
            mission = self.mission_service.get_mission(mission_id)
            if not mission:
                return jsonify({'error': 'Mission not found'}), 404

            # Extensions de fichiers texte supportées
            text_extensions = {'.md', '.txt', '.py', '.js', '.json', '.yaml', '.yml'}
            
            mission_dir = os.path.join("missions", mission['name'])
            files = []

            # Parcourir récursivement le dossier
            for root, _, filenames in os.walk(mission_dir):
                for filename in filenames:
                    if os.path.splitext(filename)[1].lower() in text_extensions:
                        full_path = os.path.join(root, filename)
                        relative_path = os.path.relpath(full_path, mission_dir)
                        files.append({
                            'name': filename,
                            'path': full_path,
                            'relativePath': relative_path,
                            'size': os.path.getsize(full_path),
                            'modified': os.path.getmtime(full_path)
                        })

            return jsonify(files)

        except Exception as e:
            self.log_message(f"Error getting mission files: {str(e)}", level='error')
            return jsonify({'error': str(e)}), 500

    def get_app(self):
        """Return the Flask app instance"""
        return self.app

if __name__ == "__main__":
    # Load keys from .env file
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    
    config = {
        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY"),
        "openai_api_key": os.getenv("OPENAI_API_KEY")
    }
    
    # Validate API keys
    if not config["openai_api_key"] or config["openai_api_key"] == "your-api-key-here":
        raise ValueError("OPENAI_API_KEY not configured in .env file")
        
    if not config["anthropic_api_key"] or config["anthropic_api_key"] == "your-api-key-here":
        raise ValueError("ANTHROPIC_API_KEY not configured in .env file")
    
    app = ParallagonWeb(config)
    # Change port to 8000 to match frontend
    app.run(host='0.0.0.0', port=8000, debug=True)
