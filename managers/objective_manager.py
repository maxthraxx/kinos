import os
from utils.logger import Logger
import openai
from dotenv import load_dotenv

class ObjectiveManager:
    """Manager class for generating agent-specific objectives."""
    
    def __init__(self):
        self.logger = Logger()
        load_dotenv()
        openai.api_key = os.getenv('OPENAI_API_KEY')
        if not openai.api_key:
            raise ValueError("OpenAI API key not found in environment variables")

    def generate_objective(self, mission_filepath=".aider.mission.md", agent_filepath=None):
        """
        Generate a specific objective for an agent based on mission and agent configuration.
        
        Args:
            mission_filepath (str): Path to mission specification file
            agent_filepath (str): Path to agent configuration file
            
        Raises:
            ValueError: If required files are invalid or missing
            IOError: If there are file operation issues
        """
        try:
            self.logger.info(f"🎯 Generating objective for agent: {agent_filepath}")
            
            # Validate input files
            if not all(self._validate_file(f) for f in [mission_filepath, agent_filepath]):
                raise ValueError("Invalid or missing input files")
                
            # Extract agent name from filepath
            agent_name = self._extract_agent_name(agent_filepath)
            
            # Load content from files
            mission_content = self._read_file(mission_filepath)
            agent_content = self._read_file(agent_filepath)
            
            # Generate objective via GPT
            objective = self._generate_objective_content(mission_content, agent_content, agent_name)
        
            # Generate summary for logging
            summary = self._generate_summary(objective, agent_name)
            self.logger.success(summary)
        
            # Save objective
            output_path = f".aider.objective.{agent_name}.md"
            self._save_objective(output_path, objective)
        
            self.logger.info(f"✅ Successfully generated objective for {agent_name}")
            
        except Exception as e:
            self.logger.error(f"❌ Objective generation failed: {str(e)}")
            raise

    def _validate_file(self, filepath):
        """Validate file exists and is readable."""
        return filepath and os.path.exists(filepath) and os.access(filepath, os.R_OK)

    def _extract_agent_name(self, agent_filepath):
        """Extract agent name from filepath."""
        basename = os.path.basename(agent_filepath)
        return basename.replace('.aider.agent.', '').replace('.md', '')

    def _read_file(self, filepath):
        """Read content from file."""
        try:
            with open(filepath, 'r') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Error reading file {filepath}: {str(e)}")
            raise

    def _generate_objective_content(self, mission_content, agent_content, agent_name):
        """Generate objective content using GPT."""
        try:
            client = openai.OpenAI()
            prompt = self._create_objective_prompt(mission_content, agent_content, agent_name)
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": """
## System Prompt

You are an objective generation agent within KinOS, an autonomous AI operating system. Your role is to analyze mission contexts and agent capabilities to generate a clear, actionable next objective.

Key principles:
- Create a specific, measurable objective
- Ensure alignment with agent capabilities
- Maintain clear scope boundaries
- Define explicit success criteria

When generating objectives:
1. Consider current mission state
2. Match agent capabilities
3. Ensure measurable outcomes
4. Keep scope focused

Your outputs will be used by Aider to execute specific tasks, so clarity and precision are essential.                   
"""},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"GPT API call failed: {str(e)}")
            raise  # Fail fast - no fallback

    def _create_objective_prompt(self, mission_content, agent_content, agent_name):
        """Create prompt for objective generation."""
        
        # Load recent chat history
        chat_history = ""
        chat_file = f".aider.chat.{agent_name}.md"
        try:
            if os.path.exists(chat_file):
                with open(chat_file, 'r') as f:
                    content = f.read()
                    # Get last 25000 chars of chat history
                    chat_history = content[-25000:] if len(content) > 25000 else content
        except Exception as e:
            self.logger.warning(f"⚠️ Could not load chat history: {str(e)}")
            # Fail fast - don't proceed without history context
            raise

        return f"""
Based on the following contexts, generate a clear objective for the {agent_name} agent that will guide its next Aider operation.

# Reference Materials
- Mission Context in `.aider.mission.md`:
{mission_content}

- Agent Configuration in `.aider.agent.{agent_name}.md`:
{agent_content}

- Recent Chat History:
{chat_history}

# Breadth-First Pattern
- Review previous objectives from chat history
- Generate an objective that explores a NEW aspect of the mission
- Avoid repeating or deepening previous work
- Focus on unexplored areas of responsibility
- Maintain breadth-first exploration pattern

# Required Output
Create an objective in markdown format that specifies:

1. **Action Statement**
   - Single, specific task to accomplish
   - Clear relation to current mission state
   - Within agent's documented capabilities

2. **Source Files**
   - Which specific files to analyze
   - Which sections are relevant
   - Which dependencies matter

3. **Target Changes**
   - Which files to modify
   - Nature of expected changes
   - Impact on system state

4. **Validation Points**
   - How to verify success
   - What output to check
   - Which states to validate

5. **Operation Bounds**
   - Resource limitations
   - Scope restrictions
   - Dependency requirements

6. **Recherche**
   - Si la tâche nécessite une recherche sur Perplexity, ajouter une section "Recherche :" avec la recherche précise à effectuer
   - Ne pas inclure cette section si aucune recherche n'est nécessaire

The objective must be:
- Limited to one clear operation
- Executable with current capabilities
- Specific about file changes
- Clear on completion checks
- Self-contained (no follow-up needed)
- Different from previous objectives

Ask Aider to make the edits now, without asking for clarification, and using the required SEARCH/REPLACE format.
"""


    def _generate_summary(self, objective, agent_name):
        """Generate a one-line summary of the objective."""
        try:
            client = openai.OpenAI()
            prompt = f"""
Résume en une seule phrase ce que l'agent va essayer de faire, en suivant strictement ce format:
"L'agent [emoji d'agent] {agent_name} va [action] [cible] [détail optionnel]"

Utilise des emojis appropriés en fonction du type d'action:
- 📝 pour l'écriture/documentation
- 🔧 pour les modifications techniques
- 🎨 pour le design/style
- 🧪 pour les tests
- 📊 pour l'analyse
- 🔍 pour la revue
- 🏗️ pour l'architecture
- 🚀 pour les déploiements
- etc.

Emojis d'agent : 
- specification : 📋
- management : 🎯
- redaction : ✍️
- evaluation : 🔍
- duplication : 🔄
- chroniqueur : 📝
- redondance : 🎭
- production : ⚙️

Voici l'objectif complet à résumer:
{objective}

Réponds uniquement avec la phrase formatée, rien d'autre.
"""
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Tu es un assistant qui résume des objectifs en une phrase concise avec des emojis appropriés."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=100
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            self.logger.error(f"Failed to generate summary: {str(e)}")
            # Return a basic fallback summary
            return f"L'agent {agent_name} 🤖 va exécuter une nouvelle tâche"

    def _save_objective(self, filepath, content):
        """Save objective content to file."""
        try:
            with open(filepath, 'w') as f:
                f.write(content)
        except Exception as e:
            self.logger.error(f"Error saving objective to {filepath}: {str(e)}")
            raise
