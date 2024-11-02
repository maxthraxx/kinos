"""
ProductionAgent - Agent responsible for code implementation and technical tasks
"""
from parallagon_agent import ParallagonAgent
from search_replace import SearchReplace
import anthropic
import re
from datetime import datetime

class ProductionAgent(ParallagonAgent):
    """Agent handling code production and implementation"""
    
    def __init__(self, config):
        super().__init__(config)
        self.client = anthropic.Anthropic(api_key=config["anthropic_api_key"])

    def determine_actions(self) -> None:
        """
        Analyze requirements and implement needed code changes
        """
        print(f"[{self.__class__.__name__}] Analyzing...")
        
        # Prepare context for LLM
        context = {
            "production": self.current_content,
            "other_files": self.other_files
        }
        
        # Get LLM response
        response = self._get_llm_response(context)
        
        # Validate response format
        if not response.startswith("# État Actuel"):
            print(f"[{self.__class__.__name__}] Invalid response format, ignoring")
            return
            
        # Log comparison
        print(f"[{self.__class__.__name__}] Comparing responses...")
        if response == self.current_content:
            print(f"[{self.__class__.__name__}] No changes needed")
        else:
            print(f"[{self.__class__.__name__}] Changes detected, updating content")
            
            # Log the differences (first 100 chars)
            print(f"[{self.__class__.__name__}] Current content starts with: {self.current_content[:100]}")
            print(f"[{self.__class__.__name__}] New content starts with: {response[:100]}")
        
        if response != self.current_content:
            # Update État Actuel section
            result = SearchReplace.section_replace(
                self.current_content,
                "État Actuel",
                self._extract_section(response, "État Actuel")
            )
            print(f"[{self.__class__.__name__}] État Actuel replace: {'✓' if result.success else '❌'} - {result.message}")
            if result.success:
                self.current_content = result.new_content

            # Update Signaux section
            result = SearchReplace.section_replace(
                self.current_content,
                "Signaux",
                self._extract_section(response, "Signaux")
            )
            print(f"[{self.__class__.__name__}] Signaux replace: {'✓' if result.success else '❌'} - {result.message}")
            if result.success:
                self.current_content = result.new_content

            # Update Contenu Principal section
            result = SearchReplace.section_replace(
                self.current_content,
                "Contenu Principal",
                self._extract_section(response, "Contenu Principal")
            )
            print(f"[{self.__class__.__name__}] Contenu Principal replace: {'✓' if result.success else '❌'} - {result.message}")
            if result.success:
                self.current_content = result.new_content

            # Update Historique section
            result = SearchReplace.section_replace(
                self.current_content,
                "Historique",
                self._extract_section(response, "Historique")
            )
            print(f"[{self.__class__.__name__}] Historique replace: {'✓' if result.success else '❌'} - {result.message}")
            if result.success:
                self.current_content = result.new_content

            # Set new content for update
            self.new_content = self.current_content

    def _get_llm_response(self, context: dict) -> str:
        """Get LLM response for implementation decisions"""
        try:
            print(f"[{self.__class__.__name__}] Calling LLM API...")  # Debug log
            prompt = f"""You are the Production Agent in the Parallagon framework. Your role is to implement code and handle technical tasks.

Current production content:
{context['production']}

Other files content:
{self._format_other_files(context['other_files'])}

Your task:
1. Review specifications and management requirements
2. Update current implementation status
3. Document technical decisions and progress
4. Respond to technical questions
5. Signal any blocking issues or needs

Focus on:
- Clear implementation steps
- Technical documentation
- Code structure and organization
- Testing requirements
- Dependencies and integration points

Important:
- Return ONLY the markdown content, starting with "# État Actuel"
- Keep all existing sections in exact order:
  1. État Actuel
  2. Signaux
  3. Contenu Principal
  4. Historique
- Maintain exact markdown formatting
- Do not include any explanatory text
- Do not start with phrases like "Based on my review" or "After analyzing"
- The response must be a valid markdown document that can directly replace the current content

Example format:
# État Actuel
[status: STATUS]
Implementation progress...

# Signaux
- Signal 1
- Signal 2

# Contenu Principal
Technical details...

# Historique
- [Timestamp] Implementation step

If changes are needed, return the complete updated content.
If no changes are needed, return the exact current content.
"""
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                temperature=0,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            print(f"[{self.__class__.__name__}] LLM response received")  # Debug log
            return response.content[0].text
        except Exception as e:
            print(f"[{self.__class__.__name__}] Error calling LLM: {str(e)}")  # Error log
            import traceback
            print(traceback.format_exc())
            return context['production']

    def _extract_section(self, content: str, section_name: str) -> str:
        """Extract content of a specific section"""
        pattern = f"# {section_name}\n(.*?)(?=\n#|$)"
        matches = list(re.finditer(pattern, content, re.DOTALL))
        
        if len(matches) == 0:
            print(f"[{self.__class__.__name__}] Section '{section_name}' not found")
            return ""
        elif len(matches) > 1:
            print(f"[{self.__class__.__name__}] Warning: Multiple '{section_name}' sections found, using first one")
            
        return matches[0].group(1).strip()

    def _format_other_files(self, files: dict) -> str:
        """Format other files content for the prompt"""
        result = []
        for file_path, content in files.items():
            result.append(f"=== {file_path} ===\n{content}\n")
        return "\n".join(result)
