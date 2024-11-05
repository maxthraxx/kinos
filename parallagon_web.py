from flask import Flask, render_template, jsonify, request, make_response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import threading
import time
import os
import json
import git
from datetime import datetime
from typing import Dict, Any
from file_manager import FileManager
from llm_service import LLMService
from search_replace import SearchReplace
from parallagon_agent import ParallagonAgent
from specifications_agent import SpecificationsAgent
from management_agent import ManagementAgent
from production_agent import ProductionAgent
from evaluation_agent import EvaluationAgent
from suivi_agent import SuiviAgent

class ParallagonWeb:
    # Log level colors
    LOG_COLORS = {
        'info': 'blue',
        'success': 'green', 
        'warning': 'orange',
        'error': 'red',
        'debug': 'gray'
    }

    TEST_DATA = """1. Reformulation de la Demande (corrigée)
Sujet scientifique : Traceurs IoT universels avec communication multi-réseaux incluant le système satellite Kineis - aspects software et firmware

Objectif de recherche : Être capable de concevoir un système IoT capable d'identifier les réseaux disponibles (LoRa, SigFox, Kineis) pour choisir le plus pertinent en consommant le moins d'énergie possible

Axes de travail :

Développement software pour l'identification et la sélection des réseaux
Optimisation du firmware pour la gestion efficace de l'énergie
Plage de dates : 2023-2024

Email : e.thery@digitalkin.ai

2. Détermination des manques actuels et maximisation de l'éligibilité au CIR (corrigée)
Résultat à considérer :

Système logiciel IoT multi-réseaux économe en énergie
Algorithme de sélection de réseau optimal
Atteinte de l'objectif idéal : Non

Preuves des manques actuels :

Algorithmes d'identification dynamique des réseaux
Logiciels de sélection en temps réel
Optimisation logicielle de l'énergie multi-réseaux
Intégration logicielle Kineis avec autres protocoles
Gestion firmware des protocoles multiples
Évaluation de l'éligibilité au CIR : L'éligibilité au CIR de ce projet reste favorable, en se concentrant sur les aspects software et firmware :

Verrous technologiques : Le développement d'algorithmes capables d'identifier et de basculer efficacement entre différents réseaux (LoRa, SigFox, Kineis) tout en optimisant la consommation d'énergie présente des défis techniques significatifs au niveau logiciel.

Incertitudes techniques : L'optimisation logicielle de la consommation d'énergie tout en gérant plusieurs protocoles de communication pose des incertitudes techniques importantes. La gestion efficace des ressources limitées d'un système embarqué pour supporter multiple protocoles est un défi complexe.

Innovation : La création d'un algorithme de sélection de réseau en temps réel, capable de prendre en compte multiples paramètres (disponibilité, consommation d'énergie, qualité de signal) représente une innovation potentielle dans le domaine du software IoT.

Avancement de l'état de l'art : Le développement d'un firmware capable de gérer efficacement les transitions entre technologies terrestres (LoRa, SigFox) et satellitaire (Kineis) tout en optimisant l'énergie pourrait représenter une avancée significative par rapport aux solutions existantes.

Ces éléments suggèrent que le projet comporte des aspects de recherche et développement logiciel qui vont au-delà de l'ingénierie courante, le rendant potentiellement éligible au CIR.

3. Génération des queries de recherche (inchangée)
Les queries restent pertinentes car elles se concentrent déjà sur les aspects software et firmware :

"IoT multi-network system energy efficient LoRa SigFox Kineis 2023 2024"

"IoT software network identification selection algorithm LoRa SigFox Kineis 2023 2024"

"IoT firmware energy optimization multi-network LoRa SigFox Kineis 2023 2024"

"Kineis satellite IoT integration energy efficient tracking 2023 2024"

### Niveau de profondeur
[x] Approfondi (10-15 pages)

# TEMPLATE ÉTAT DE L'ART CIR

## Introduction générale (200-250 mots)

**But** : Présenter le contexte global du projet de R&D et introduire les différents axes de recherche.

**Directives** :
- Contextualiser la problématique générale
- Présenter succinctement les axes de recherche (2-3 axes maximum)
- Justifier la décomposition en axes distincts
- Style : Accessible aux non-spécialistes tout en restant précis
- Aucune référence nécessaire dans cette section

## Pour chaque axe de recherche (1100-1450 mots par axe)

### 1. Introduction de l'axe (100-150 mots)

**But** : Contextualiser l'axe et établir son objectif de recherche spécifique.

**Directives** :
- Présenter l'axe et son objectif de recherche spécifique
- Montrer sa contribution à l'objectif global
- Justifier sa pertinence dans le projet
- Style : Concis, technique mais accessible
- Aucune référence nécessaire

### 2. Synthèse des connaissances actuelles (400-500 mots)

**But** : Établir l'état des connaissances existantes pertinentes pour l'axe.

**Directives** :
- Structurer par thèmes ou approches principales
- Présenter chronologiquement les avancées majeures
- Références : 6-8 publications clés (< 5 ans sauf si fondamentales)
- Style : Paragraphes courts, progressifs
- Privilégier la paraphrase aux citations directes
- Maintenir le fil conducteur vers l'objectif de l'axe

### 3. Analyse critique et limites (300-400 mots)

**But** : Démontrer l'insuffisance des approches actuelles.

**Directives** :
- Identifier 3-4 limites majeures
- Lier chaque limite à l'objectif de l'axe
- Références : 3-4 publications illustrant ces limites
- Un paragraphe par limite majeure
- Utiliser des connecteurs logiques
- Tone objectif et factuel

### 4. Verrous scientifiques et techniques (200-250 mots)

**But** : Identifier les obstacles spécifiques bloquant l'atteinte de l'objectif.

**Directives** :
- Structure pour chaque verrou :
  - Description du verrou
  - Impact sur l'objectif
  - Tentatives actuelles de résolution
  - Limitations de ces tentatives
- Références : 1-2 publications par verrou
- Style : Technique mais clair
- Lien explicite avec les critères CIR

### 5. Conclusion de l'axe (100-150 mots)

**But** : Synthétiser la nécessité de nouvelles recherches pour cet axe.

**Directives** :
- Résumer les limites principales
- Justifier le besoin de nouvelles approches
- Ne pas décrire les solutions envisagées
- Style : Synthétique et conclusif
- Aucune nouvelle référence

## Synthèse multi-axes (250-300 mots)

**But** : Démontrer la cohérence globale des axes et leur complémentarité.

**Directives** :
- Rappeler brièvement les verrous majeurs de chaque axe
- Montrer les interactions entre les axes
- Justifier la nécessité d'aborder tous les axes
- Expliquer la contribution de chaque axe à l'objectif global
- Style : Vue d'ensemble stratégique
- Aucune nouvelle référence

## Conclusion générale (150-200 mots)

**But** : Synthétiser la nécessité globale du projet de R&D.

**Directives** :
- Rappeler l'objectif global
- Résumer les principaux verrous identifiés
- Justifier la nécessité d'une approche R&D
- Style : Accessible aux non-spécialistes
- Aucune nouvelle référence

## Références bibliographiques

**Directives** :
- Format : Norme APA ou IEEE
- Organisation : Par ordre alphabétique ou d'apparition
- Nombre : 10-15 références par axe
- Qualité : Publications académiques, brevets, standards
- Date : Privilégier les références récentes (< 5 ans)
- Pertinence : Chaque référence doit être citée dans le texte

## Directives générales

### Format et style
- Longueur totale : 2000-2500 mots + 1100-1450 mots par axe
- Style scientifique et objectif
- Éviter le conditionnel sauf pour les perspectives
- Paragraphes courts et structurés
- Transitions logiques entre sections

### Critères CIR à satisfaire
- Démontrer l'état des connaissances accessibles
- Identifier clairement les limites actuelles
- Justifier la nécessité de travaux de R&D
- Établir le caractère nouveau des recherches
- Mettre en évidence les verrous technologiques

### Relations clés à maintenir
- État de l'art ↔ Objectif global
- État de l'art ↔ Objectifs spécifiques des axes
- Axes ↔ Verrous technologiques
- Verrous ↔ Critères CIR
- Axes entre eux (complémentarité)

## But global de l'état de l'art

Démontrer rigoureusement que l'objectif global du projet ne peut être atteint avec les connaissances et approches actuelles, justifiant ainsi la nécessité d'engager des travaux de R&D potentiellement éligibles au CIR. Pour cela, l'état de l'art doit :
1. Établir l'état des connaissances accessible
2. Identifier les limites des approches existantes
3. Démontrer l'existence de verrous technologiques
4. Justifier la nécessité d'une approche R&D structurée
5. Préparer la justification des travaux proposés
"""

    def __init__(self, config):
        self.app = Flask(__name__)
        CORS(self.app)  # Enable CORS
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
        try:
            self.log_message("Initializing agents...", level='info')
            # Initialize git repo
            try:
                self.repo = git.Repo(os.getcwd())
            except git.InvalidGitRepositoryError:
                self.repo = git.Repo.init(os.getcwd())
                self.log_message("Initialized new git repository")

            base_config = {
                "check_interval": 5,
                "anthropic_api_key": config["anthropic_api_key"],
                "openai_api_key": config["openai_api_key"],
                "logger": self.log_message,
                "repo": self.repo
            }
            
            self.agents = {
                "Specification": SpecificationsAgent({
                    **base_config,
                    "file_path": "specifications.md",
                    "watch_files": ["demande.md", "management.md", "production.md", "evaluation.md"]
                }),
                "Suivi": SuiviAgent({
                    **base_config,
                    "file_path": "suivi.md",
                    "watch_files": ["demande.md", "specifications.md", "management.md", "production.md", "evaluation.md"],
                    "logs_buffer": self.logs_buffer
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
            self.log_message("Agents initialized successfully", level='success')
            
        except Exception as e:
            self.log_message(f"Error initializing agents: {str(e)}", level='error')
            raise

    def handle_content_change(self, file_path: str, content: str, panel_name: str = None, flash: bool = False):
        """Handle content change notifications"""
        try:
            # Format timestamp consistently
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Create notification with all required fields
            notification = {
                'type': 'info',
                'message': f'Content updated in {panel_name or os.path.basename(file_path)}',
                'timestamp': timestamp,
                'panel': panel_name or os.path.splitext(os.path.basename(file_path))[0],
                'status': os.path.basename(file_path),
                'operation': 'flash_tab',
                'id': len(self.notifications_queue)
            }
            
            # Add to notifications queue
            self.notifications_queue.append(notification)
            
            # Debug logs
            print(f"Added notification: {notification}")
            print(f"Current notifications queue: {self.notifications_queue}")
            
            # Update cache
            self.content_cache[file_path] = content
            self.last_modified[file_path] = time.time()
            
        except Exception as e:
            self.log_message(f"Error handling content change: {str(e)}", level='error')

    def setup_routes(self):
        @self.app.route('/api/test-data', methods=['POST'])
        def load_test_data():
            try:
                success = self.file_manager.write_file('demande', self.TEST_DATA)
                if success:
                    self.log_message("✨ Données de test chargées", level='success')
                    return jsonify({'status': 'success'})
                else:
                    return jsonify({'error': 'Failed to write test data'}), 500
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/reset', methods=['POST'])
        def reset_files():
            try:
                success = self.file_manager.reset_files()
                if success:
                    self.log_message("All files reset to initial state")
                    return jsonify({'status': 'success'})
                else:
                    return jsonify({'error': 'Failed to reset files'}), 500
            except Exception as e:
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

        @self.app.route('/')
        def home():
            # Initialize empty notifications list
            notifications = []  # Will be populated with any notifications to show
            return render_template('index.html', notifications=notifications, 
                tab_ids={
                    'demande.md': 'tab-demande',
                    'specifications.md': 'tab-specifications', 
                    'management.md': 'tab-management',
                    'production.md': 'tab-production',
                    'evaluation.md': 'tab-evaluation'
                })

        @self.app.route('/api/status')
        def get_status():
            return jsonify({
                'running': self.running,
                'agents': {name: agent.should_run() for name, agent in self.agents.items()}
            })

        @self.app.route('/api/content')
        def get_content():
            try:
                content = {}
                for file_name in self.file_paths:
                    try:
                        content[file_name] = self.file_manager.read_file(file_name)
                        # Mettre en cache le contenu
                        self.content_cache[file_name] = content[file_name]
                        self.last_modified[file_name] = time.time()
                    except Exception as e:
                        self.log_message(f"Error reading {file_name}: {str(e)}")
                        content[file_name] = ""
                        
                return jsonify(content)
            except Exception as e:
                self.log_message(f"Error getting content: {str(e)}")
                return jsonify({'error': str(e)}), 500

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
                
                # Format logs with timestamps, levels, and metadata
                formatted_logs = []
                for log in self.logs_buffer:
                    timestamp = log.get('timestamp', '')
                    level = log.get('level', 'info')
                    message = log.get('message', '')
                    agent = log.get('agent', '')
                    operation = log.get('operation', '')
                    status = log.get('status', '')
                    
                    # Build log line with all available information
                    log_parts = [f"[{timestamp}]", f"[{level.upper()}]"]
                    if agent:
                        log_parts.append(f"[{agent}]")
                    if operation:
                        log_parts.append(f"[{operation}]")
                    if status:
                        log_parts.append(f"[{status}]")
                    log_parts.append(message)
                    
                    formatted_logs.append(" ".join(log_parts))
                
                # Add header with export information
                header = [
                    "Parallagon Log Export",
                    f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    f"Total Entries: {len(self.logs_buffer)}",
                    "-" * 80
                ]
                
                # Combine header and logs
                full_content = "\n".join(header + [""] + formatted_logs)
                
                # Create response with file download
                response = make_response(full_content)
                response.headers["Content-Disposition"] = f"attachment; filename={filename}"
                response.headers["Content-Type"] = "text/plain"
                
                self.log_message("Logs exported successfully", level='success')
                return response
            except Exception as e:
                self.log_message(f"Error exporting logs: {str(e)}", level='error')
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/logs/clear', methods=['POST'])
        def clear_logs():
            try:
                self.logs_buffer.clear()
                return jsonify({'status': 'success'})
            except Exception as e:
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

        @self.app.route('/api/notifications', methods=['GET'])
        @self.limiter.limit("500 per minute")
        def get_notifications():
            """Get pending notifications"""
            try:
                # Récupérer les notifications en attente
                notifications = []
                
                # Ajouter les notifications de la queue
                while self.notifications_queue:
                    notification = self.notifications_queue.pop(0)
                    notifications.append(notification)
                    print(f"Sending notification: {notification}")  # Debug log
                    
                # Debug log
                if notifications:
                    print(f"Sending {len(notifications)} notifications to frontend")
                    
                return jsonify(notifications)
                
            except Exception as e:
                self.log_message(f"Error getting notifications: {str(e)}", level='error')
                # Retourner une liste vide au lieu d'une erreur 500
                return jsonify([])

        @self.app.route('/api/demande', methods=['POST'])
        def save_demande():
            try:
                data = request.get_json()
                if not data or 'content' not in data:
                    self.log_message("❌ Pas de contenu fourni pour la demande", level='error')
                    return jsonify({'error': 'No content provided'}), 400
                    
                # Vérifier que le contenu est une chaîne de caractères
                if not isinstance(data['content'], str):
                    self.log_message("❌ Le contenu de la demande doit être une chaîne de caractères", level='error')
                    return jsonify({'error': 'Content must be a string'}), 400

                # Essayer d'écrire le fichier
                try:
                    success = self.file_manager.write_file('demande', data['content'])
                    if success:
                        self.log_message("✓ Demande sauvegardée", level='success')
                        # Notifier du changement
                        self.handle_content_change(
                            'demande.md',
                            data['content'],
                            panel_name='Demande'
                        )
                        return jsonify({'status': 'success'})
                    else:
                        self.log_message("❌ Échec de sauvegarde de la demande", level='error')
                        return jsonify({'error': 'Failed to write demand file'}), 500
                        
                except Exception as write_error:
                    self.log_message(f"❌ Erreur d'écriture du fichier: {str(write_error)}", level='error')
                    return jsonify({'error': f'File write error: {str(write_error)}'}), 500
                    
            except Exception as e:
                self.log_message(f"❌ Erreur lors de la sauvegarde de la demande: {str(e)}", level='error')
                return jsonify({'error': str(e)}), 500

    def run(self, host='0.0.0.0', port=5000, **kwargs):
        """Run the Flask application with optional configuration parameters"""
        self.app.run(host=host, port=port, **kwargs)

    def start_agents(self):
        """Start all agents"""
        try:
            self.log_message("🚀 Démarrage des agents...", level='info')
            self.running = True
            
            # Start content update loop
            def update_loop():
                self.log_message("✓ Boucle de mise à jour démarrée", level='success')
                while self.running:
                    try:
                        self.check_content_updates()
                    except Exception as e:
                        self.log_message(f"❌ Erreur dans la boucle de mise à jour: {str(e)}", level='error')
                    time.sleep(1)  # Check every second
            
            # Start update loop in separate thread
            self.update_thread = threading.Thread(target=update_loop, daemon=True)
            self.update_thread.start()
            
            # Start agents in separate threads
            for name, agent in self.agents.items():
                try:
                    thread = threading.Thread(target=agent.run, daemon=True)
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
        self.running = False
        if hasattr(self, 'update_thread'):
            self.update_thread.join(timeout=2)  # Wait for update thread to finish
        for agent in self.agents.values():
            agent.stop()
        self.log_message("Agents stopped", level='info')

    def log_message(self, message, operation: str = None, status: str = None, level: str = 'info'):
        """Log a message with optional operation, status and color"""
        try:
            # Utiliser un format de date cohérent
            timestamp = datetime.now().strftime("%H:%M:%S")  # Format court HH:MM:SS
            
            # Determine color based on level
            color = self.LOG_COLORS.get(level, 'black')
            
            # Format log entry
            if operation and status:
                log_entry = {
                    'id': len(self.logs_buffer),
                    'timestamp': timestamp,
                    'message': f"{operation}: {status} - {message}",
                    'level': level,
                    'color': color
                }
            else:
                log_entry = {
                    'id': len(self.logs_buffer),
                    'timestamp': timestamp,
                    'message': message,
                    'level': level,
                    'color': color
                }
            
            # Add to logs buffer
            self.logs_buffer.append(log_entry)
            
            # Keep only last 100 logs
            if len(self.logs_buffer) > 100:
                self.logs_buffer = self.logs_buffer[-100:]
            
            # Print to console for debugging
            print(f"[{timestamp}] [{level}] {message}")
                
        except Exception as e:
            print(f"Error logging message: {str(e)}")

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
    # Use Flask's development server when running directly 
    app.run(debug=True)
