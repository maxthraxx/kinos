from flask import Flask, render_template, jsonify, request, make_response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import threading
import time
import os
import json
from datetime import datetime
from typing import Dict, Any
from file_manager import FileManager
from llm_service import LLMService
from specifications_agent import SpecificationsAgent
from management_agent import ManagementAgent
from production_agent import ProductionAgent
from evaluation_agent import EvaluationAgent

class ParallagonWeb:
    def __init__(self, config):
        self.app = Flask(__name__)
        CORS(self.app)  # Enable CORS
        self.limiter = Limiter(
            app=self.app,
            key_func=get_remote_address,
            default_limits=["200 per minute"]
        )
        self.content_cache = {}
        self.last_modified = {}
        self.setup_error_handlers()
        # Add file paths configuration
        self.file_paths = {
            "demande": "demande.md",
            "specifications": "specifications.md",
            "management": "management.md", 
            "production": "production.md",
            "evaluation": "evaluation.md"
        }
        self.file_manager = FileManager(self.file_paths)
        self.llm_service = LLMService(config["openai_api_key"])
        self.running = False
        self.agents = {}
        self.logs_buffer = []  # Store recent logs
        self.init_agents(config)
        self.setup_routes()

    def init_agents(self, config):
        """Initialisation des agents avec configuration standard"""
        base_config = {
            "check_interval": 5,
            "anthropic_api_key": config["anthropic_api_key"],
            "openai_api_key": config["openai_api_key"],
            "logger": self.log_message
        }
        
        self.agents = {
            "Specification": SpecificationsAgent({
                **base_config,
                "file_path": "specifications.md",
                "watch_files": ["demande.md", "management.md", "production.md", "evaluation.md"]
            }),
            "Management": ManagementAgent({
                **base_config,
                "file_path": "management.md",
                "watch_files": ["demande.md", "specifications.md", "production.md", "evaluation.md"]
            }),
            "Production": ProductionAgent({
                **base_config,
                "file_path": "production.md",
                "watch_files": ["demande.md", "specifications.md", "management.md", "evaluation.md"]
            }),
            "Evaluation": EvaluationAgent({
                **base_config,
                "file_path": "evaluation.md",
                "watch_files": ["demande.md", "specifications.md", "management.md", "production.md"]
            })
        }

    def handle_content_change(self, file_name: str, content: str):
        """Handle content change notifications"""
        # Update cache
        self.content_cache[file_name] = content
        self.last_modified[file_name] = time.time()
        
        # Notify relevant agents
        for agent in self.agents.values():
            if file_name in agent.watch_files:
                agent.handle_file_change(file_name, content)

    def setup_routes(self):
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

        @self.app.route('/')
        def home():
            # Initialize empty notifications list
            notifications = []  # Will be populated with any notifications to show
            return render_template('index.html', notifications=notifications)

        @self.app.route('/api/status')
        def get_status():
            return jsonify({
                'running': self.running,
                'agents': {name: agent.should_run() for name, agent in self.agents.items()}
            })

        @self.app.route('/api/content')
        def get_content():
            current_time = time.time()
            content = {}
            
            for file_name in self.file_paths:
                try:
                    file_path = self.file_paths[file_name]
                    mtime = os.path.getmtime(file_path)
                    
                    # Check if file has been modified since last read
                    if (file_name not in self.last_modified or 
                        mtime > self.last_modified[file_name]):
                        
                        content[file_name] = self.file_manager.read_file(file_name)
                        self.content_cache[file_name] = content[file_name]
                        self.last_modified[file_name] = mtime
                    else:
                        content[file_name] = self.content_cache[file_name]
                        
                except Exception as e:
                    self.log_message(f"Error reading {file_name}: {str(e)}")
                    content[file_name] = ""
                    
            return jsonify(content)

        @self.app.route('/api/start', methods=['POST'])
        def start_agents():
            self.start_agents()
            return jsonify({'status': 'started'})

        @self.app.route('/api/stop', methods=['POST'])
        def stop_agents():
            self.stop_agents()
            return jsonify({'status': 'stopped'})

        @self.app.route('/api/logs')
        def get_logs():
            return jsonify({
                'logs': self.logs_buffer
            })
            
        @self.app.route('/api/logs/export')
        def export_logs():
            try:
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                filename = f"parallagon-logs-{timestamp}.txt"
                
                # Format logs with timestamps
                formatted_logs = "\n".join(self.logs_buffer)
                
                # Create response with file download
                response = make_response(formatted_logs)
                response.headers["Content-Disposition"] = f"attachment; filename={filename}"
                response.headers["Content-Type"] = "text/plain"
                
                return response
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/logs/clear', methods=['POST'])
        def clear_logs():
            try:
                self.logs_buffer.clear()
                return jsonify({'status': 'success'})
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/demande', methods=['POST'])
        def update_demande():
            try:
                content = request.json.get('content')
                if not content:
                    return jsonify({'error': 'No content provided'}), 400
                    
                success = self.file_manager.write_file('demande.md', content)
                if success:
                    return jsonify({'status': 'success'})
                else:
                    return jsonify({'error': 'Failed to write file'}), 500
            except Exception as e:
                return jsonify({'error': str(e)}), 500

    def run(self, host='0.0.0.0', port=5000, **kwargs):
        """Run the Flask application with optional configuration parameters"""
        self.app.run(host=host, port=port, **kwargs)

    def start_agents(self):
        """Start all agents"""
        self.running = True
        # Start content update loop
        def update_loop():
            while self.running:
                self.check_content_updates()
                time.sleep(1)  # Check for updates every second
                
        # Start update loop in separate thread
        threading.Thread(target=update_loop, daemon=True).start()
        
        # Start agents in separate threads
        for name, agent in self.agents.items():
            thread = threading.Thread(target=agent.run, daemon=True)
            thread.start()
            self.log_message(f"Agent {name} started")

    def stop_agents(self):
        self.running = False
        for agent in self.agents.values():
            agent.stop()

    def log_message(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.logs_buffer.append(log_entry)
        
        # Broadcast log to all WebSocket clients
        self.broadcast_message({
            'type': 'log',
            'timestamp': timestamp,
            'message': message
        })
        
        # Keep only last 100 logs
        if len(self.logs_buffer) > 100:
            self.logs_buffer.pop(0)
        print(log_entry)

    def check_content_updates(self):
        """Check for content updates"""
        try:
            current_content = {
                'demande': self.file_manager.read_file('demande'),
                'specifications': self.file_manager.read_file('specifications'),
                'management': self.file_manager.read_file('management'),
                'production': self.file_manager.read_file('production'),
                'evaluation': self.file_manager.read_file('evaluation')
            }
            
            if current_content != self.last_content:
                self.last_content = current_content.copy()
                self.log_message("Content updated")
                
        except Exception as e:
            self.log_message(f"Error checking content updates: {str(e)}")

    def setup_error_handlers(self):
        @self.app.errorhandler(404)
        def not_found_error(error):
            return jsonify({'error': 'Resource not found'}), 404

        @self.app.errorhandler(500)
        def internal_error(error):
            return jsonify({'error': 'Internal server error'}), 500

        @self.app.errorhandler(Exception)
        def handle_exception(error):
            return jsonify({'error': str(error)}), 500

    def shutdown(self):
        """Graceful shutdown of the application"""
        try:
            # Stop all agents
            self.stop_agents()
            
            # Clear caches
            self.content_cache.clear()
            self.last_modified.clear()
            
            # Export final logs
            self.export_logs()
            
            self.log_message("Application shutdown complete")
        except Exception as e:
            self.log_message(f"Error during shutdown: {str(e)}")

    def get_app(self):
        """Return the Flask app instance"""
        return self.app

if __name__ == "__main__":
    config = {
        "anthropic_api_key": "your-api-key-here",
        "openai_api_key": "your-api-key-here"
    }
    app = ParallagonWeb(config)
    # Use Flask's development server when running directly 
    app.run(debug=True)
