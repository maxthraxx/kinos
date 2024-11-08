"""
Foundation for autonomous file-focused agents.

Each agent is responsible for:
- Monitoring and updating its dedicated file
- Analyzing changes in related files
- Making independent decisions
- Adapting its execution rhythm

Key behaviors:
- File-based state persistence
- Self-regulated execution cycles
- Automatic error recovery
- Activity-based timing adjustments
"""
from typing import Dict, Any, Optional, List
import re
import time
import openai
import anthropic
import os
from datetime import datetime, timedelta
from functools import wraps

class KinOSAgent:
    """
    Foundation for autonomous file-focused agents.
    
    Each agent is responsible for:
    - Monitoring and updating its dedicated file
    - Analyzing changes in related files
    - Making independent decisions
    - Adapting its execution rhythm
    
    Key behaviors:
    - File-based state persistence
    - Self-regulated execution cycles
    - Automatic error recovery
    - Activity-based timing adjustments
    """
    
    # Default intervals for each agent type (in seconds)
    DEFAULT_INTERVALS = {
        'SpecificationsAgent': 40,  # Specifications change less frequently
        'ProductionAgent': 16,      # Medium reactivity
        'ManagementAgent': 30,      # Coordination needs less frequency
        'EvaluationAgent': 36,      # Allow changes to accumulate
        'SuiviAgent': 20,          # More reactive monitoring
        'DocumentalisteAgent': 45,  # Documentation updates less frequent
        'DuplicationAgent': 50      # Code analysis needs more time
    }

    def __init__(self, config: Dict[str, Any]):
        """
        Initialise l'agent avec sa configuration.
        
        Args:
            config: Dictionnaire contenant:
                - anthropic_api_key: Clé API Anthropic
                - openai_api_key: Clé API OpenAI 
                - file_path: Chemin du fichier principal
                - watch_files: Liste des fichiers à surveiller
                - check_interval: Intervalle de vérification
                - logger: Fonction de logging
        """
        # Validation de la configuration
        if not config.get("anthropic_api_key"):
            raise ValueError("anthropic_api_key manquante dans la configuration")
        if not config.get("openai_api_key"):
            raise ValueError("openai_api_key manquante dans la configuration")
            
        self.config = config
        self.file_path = config["file_path"]
        self.other_files = config.get("other_files", [])
        # Make sure file_path is in other_files if not already
        if self.file_path not in self.other_files:
            self.other_files.append(self.file_path)
        
        # Initialisation des clients API avec les clés validées
        self.client = anthropic.Client(api_key=config["anthropic_api_key"])
        self.openai_client = openai.OpenAI(api_key=config["openai_api_key"])
        
        # Initialize other_files
        self.other_files = {}
        
        # Use agent-specific rhythm or default value
        agent_type = self.__class__.__name__
        self.check_interval = config.get(
            "check_interval", 
            self.DEFAULT_INTERVALS.get(agent_type, 10)
        )
        
        self.running = False
        self.logger = config.get("logger", print)
        self.last_run = None
        self.last_change = None
        self.consecutive_no_changes = 0


    def start(self) -> None:
        """
        Démarre l'agent.
        
        - Active le flag running
        - Réinitialise les métriques
        - Prépare l'agent pour l'exécution
        """
        self.running = True
        # Reset metrics
        self.last_run = None
        self.last_change = None
        self.consecutive_no_changes = 0


    def stop(self) -> None:
        """
        Arrête l'agent proprement.
        
        - Désactive le flag running
        - Termine les opérations en cours
        - Sauvegarde l'état final
        """
        self.running = False
        # Clean up any pending operations
        if hasattr(self, 'current_content'):
            self.write_file(self.current_content)
            
    def recover_from_error(self):
        """
        Tente de récupérer après une erreur.
        
        - Réinitialise l'état interne
        - Recharge les fichiers
        - Journalise la tentative
        
        Returns:
            bool: True si récupération réussie, False sinon
        """
        try:
            self.logger(f"[{self.__class__.__name__}] Attempting recovery...")
            
            # Reset internal state
            self.last_run = None
            self.last_change = None
            self.consecutive_no_changes = 0
            
            # Re-initialize file monitoring
            self.list_files()
            
            # Log recovery attempt
            self.logger(f"[{self.__class__.__name__}] Recovery complete")
            return True
            
        except Exception as e:
            self.logger(f"[{self.__class__.__name__}] Recovery failed: {str(e)}")
            return False

    def update_paths(self, file_path: str, other_files: List[str]) -> None:
        """
        Met à jour les chemins des fichiers quand la mission change.
        
        Args:
            file_path: Nouveau chemin principal
            other_files: Nouvelle liste de fichiers à surveiller
            
        - Met à jour les chemins
        - Recharge les fichiers
        """
        try:
            self.file_path = file_path
            self.other_files = other_files
            
            # Re-initialize file monitoring with new paths
            self.list_files()
            
        except Exception as e:
            print(f"Error updating paths for {self.__class__.__name__}: {e}")

    def should_run(self) -> bool:
        """
        Détermine si l'agent doit s'exécuter.
        
        Returns:
            bool: True si l'agent doit s'exécuter
            
        Facteurs considérés:
        - Temps depuis dernière exécution
        - Niveau d'activité récent
        - Ajustements dynamiques du timing
        """
        now = datetime.now()
        
        # First run
        if self.last_run is None:
            return True
            
        # Calculate dynamic delay
        delay = self.calculate_dynamic_interval()
        
        # Check if enough time has elapsed
        return (now - self.last_run) >= timedelta(seconds=delay)


    def calculate_dynamic_interval(self) -> float:
        """
        Calcule l'intervalle optimal entre les exécutions.
        
        Returns:
            float: Intervalle calculé en secondes
            
        Facteurs pris en compte:
        - Fréquence récente des changements
        - Niveau d'activité système
        - Utilisation des ressources
        - Exigences temporelles spécifiques
        """
        base_interval = self.check_interval
        
        # If no recent changes, increase interval more aggressively
        if self.last_change and self.consecutive_no_changes > 0:
            # Increase up to 10x base rhythm
            multiplier = min(10, 1 + (self.consecutive_no_changes * 1.0))
            return base_interval * multiplier
            
        return base_interval

    def run(self) -> None:
        """
        Boucle principale de l'agent.
        
        Cycle d'exécution:
        1. Vérifie si doit s'exécuter
        2. Sauvegarde état précédent
        3. Execute aider
        4. Pause adaptative
        
        Gère:
        - Arrêts propres
        - Récupération d'erreurs
        - Métriques d'exécution
        """
        self.running = True
        while self.running:
            try:
                if not self.should_run():
                    time.sleep(1)
                    continue
                    
                # Vérifier le contenu avant modification
                current_content = None
                if os.path.exists(self.file_path):
                    with open(self.file_path, 'r', encoding='utf-8') as f:
                        current_content = f.read()
                    self.logger(f"[{self.__class__.__name__}] Current content size: {len(current_content) if current_content else 0}")
                
                # Save state before modifications
                previous_content = self.current_content if hasattr(self, 'current_content') else None
                
                # Exécuter Aider avec le prompt de l'agent
                if hasattr(self, '_run_aider'):
                    result = self._run_aider(self.prompt)
                    if result:
                        self.last_change = datetime.now()
                        self.consecutive_no_changes = 0
                    else:
                        self.consecutive_no_changes += 1
                
                # Update metrics
                self.last_run = datetime.now()
                
                # Adaptive pause
                time.sleep(self.calculate_dynamic_interval())
                
            except Exception as e:
                self.logger(f"Error in agent loop: {e}")
                if not self.running:
                    break
