"""
search_replace.py - Implementation of the SEARCH/REPLACE pattern for Parallagon

Key features:
- Exact text matching with validation
- Section-based content updates
- Safe atomic replacements
- Content normalization
"""
from typing import Tuple, Optional
import re
from dataclasses import dataclass

@dataclass
class SearchReplaceResult:
    """Result of a search/replace operation"""
    success: bool
    message: str
    new_content: Optional[str] = None
    occurrences: int = 0

class SearchReplace:
    """Handles safe search/replace operations in markdown files"""

    @staticmethod
    def _normalize_text(text: str) -> str:
        """
        Normalise le texte pour une comparaison très permissive:
        - Supprime tous les espaces et sauts de ligne
        - Convertit en minuscules
        - Retire tous les caractères spéciaux et accents
        - Ne garde que les caractères alphanumériques
        """
        import unicodedata
        import re
        
        # Convertir en minuscules
        text = text.lower()
        
        # Retirer les accents
        text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
        
        # Retirer TOUS les caractères non alphanumériques (espaces, ponctuation, etc.)
        text = re.sub(r'[^a-z0-9]', '', text)
        
        return text

    @staticmethod
    def validate_replacement(content: str, old_str: str) -> Tuple[bool, str, int]:
        """
        Validate text replacement with permissive matching.
        
        Checks:
        - Text exists in content
        - Exactly one occurrence found
        - Match corresponds to search text
        
        Args:
            content: Full document content
            old_str: Text to find and replace
            
        Returns:
            Tuple[bool, str, int]: Success, message, occurrences
        """
        try:
            # Normalise le contenu et la recherche
            normalized_content = SearchReplace._normalize_text(content)
            normalized_search = SearchReplace._normalize_text(old_str)
            
            # Crée un pattern plus permissif
            # Permet des différences d'espaces et de sauts de ligne
            pattern = ''.join(
                f'\\s*{re.escape(word)}\\s*'
                for word in normalized_search.split()
            )
            
            # Recherche toutes les occurrences
            matches = list(re.finditer(pattern, normalized_content, re.MULTILINE | re.DOTALL))
            count = len(matches)
            
            if count == 0:
                return False, "Texte à remplacer non trouvé", 0
            elif count > 1:
                return False, f"Le texte à remplacer apparaît {count} fois (doit être unique)", count
                
            # Vérifie que le match trouvé correspond bien au contenu recherché
            match_text = matches[0].group(0)
            if SearchReplace._normalize_text(match_text) == normalized_search:
                return True, "Remplacement valide", 1
            else:
                return False, "Le texte trouvé ne correspond pas exactement", 0
                
        except Exception as e:
            return False, f"Erreur lors de la validation: {str(e)}", 0

    @staticmethod 
    def section_replace(content: str, section_name: str, new_section_content: str) -> SearchReplaceResult:
        """
        Replace content of a markdown section.
        
        Operations:
        - Find section by name
        - Handle section deletion
        - Create missing sections
        - Replace section content
        - Preserve document structure
        
        Args:
            content: Full document content
            section_name: Name of section to update
            new_section_content: New content for section
            
        Returns:
            SearchReplaceResult: Operation result and updated content
        """
        try:
            # Handle section deletion if specified
            if new_section_content.strip() == "(to delete)":
                # Échapper les caractères spéciaux dans le titre de section, sauf les #
                escaped_name = re.escape(section_name).replace(r'\#', '#')
                # Pattern qui capture la section entière jusqu'à la prochaine section
                pattern = fr"({escaped_name}\n.*?)(?=\n#{{1,6}}\s|$)"
                matches = list(re.finditer(pattern, content, re.DOTALL))
                
                if not matches:
                    return SearchReplaceResult(False, f"Section '{section_name}' not found", content, 0)
                    
                # Supprimer la section et les lignes vides qui suivent
                new_content = content[:matches[0].start()].rstrip() + content[matches[0].end():].lstrip()
                return SearchReplaceResult(True, f"Section '{section_name}' deleted", new_content, 1)

            # Regular section replacement
            # Échapper les caractères spéciaux dans le titre de section, sauf les #
            escaped_name = re.escape(section_name).replace(r'\#', '#')
            # Utiliser un raw string pour l'expression régulière
            pattern = fr"{escaped_name}\n(.*?)(?=\n#{{1,6}}\s|$)"
            matches = list(re.finditer(pattern, content, re.DOTALL))
            
            if not matches:
                # Si la section n'existe pas, on l'ajoute à la fin du document
                if content.strip() == "En attente de contenu à produire..." or not content.strip():
                    # Si le document est vide ou contient juste le message d'attente
                    new_content = f"{section_name}\n{new_section_content}"
                else:
                    # Sinon on ajoute après une ligne vide
                    new_content = f"{content.rstrip()}\n\n{section_name}\n{new_section_content}"
                return SearchReplaceResult(True, f"Section '{section_name}' created", new_content, 1)
            
            if len(matches) > 1:
                return SearchReplaceResult(False, f"Multiple '{section_name}' sections found", content, len(matches))
                
            # Log section content for debugging
            print(f"Replacing section {section_name}:")
            print(f"Old: {matches[0].group(1).strip()}")
            print(f"New: {new_section_content}")
            
            new_content = content[:matches[0].start()] + f"{section_name}\n{new_section_content}" + content[matches[0].end():]
            return SearchReplaceResult(True, "Section replaced successfully", new_content, 1)
            
        except Exception as e:
            return SearchReplaceResult(False, f"Error in section_replace: {str(e)}", content, 0)

    @staticmethod
    def exact_replace(content: str, old_str: str, new_str: str) -> SearchReplaceResult:
        """
        Perform exact text replacement with validation.
        
        Process:
        - Normalize content for search
        - Find exact match
        - Validate single occurrence
        - Replace while preserving format
        
        Args:
            content: Full document content
            old_str: Text to find
            new_str: Replacement text
            
        Returns:
            SearchReplaceResult: Operation result and updated content
        """
        try:
            # Normalise pour la recherche
            normalized_content = SearchReplace._normalize_text(content)
            normalized_search = SearchReplace._normalize_text(old_str)
            
            # Crée un pattern permissif
            pattern = ''.join(
                f'\\s*{re.escape(word)}\\s*'
                for word in normalized_search.split()
            )
            
            # Trouve le match
            match = re.search(pattern, normalized_content, re.MULTILINE | re.DOTALL)
            if not match:
                return SearchReplaceResult(False, "Texte à remplacer non trouvé", content, 0)
                
            # Récupère le texte exact qui a matché
            exact_match = match.group(0)
            
            # Effectue le remplacement en préservant le formatage du nouveau texte
            new_content = content.replace(exact_match, new_str)
            return SearchReplaceResult(True, "Remplacement effectué avec succès", new_content, 1)
            
        except Exception as e:
            return SearchReplaceResult(False, f"Erreur lors du remplacement: {str(e)}", content, 0)

    @staticmethod
    def add_to_section(content: str, section_name: str, new_entry: str, 
                      position: str = "end") -> SearchReplaceResult:
        """
        Add content to a specific section.
        
        Features:
        - Add at start or end of section
        - Preserve section formatting
        - Handle missing sections
        - Validate section uniqueness
        
        Args:
            content: Full document content
            section_name: Target section name
            new_entry: Content to add
            position: Where to add ("start" or "end")
            
        Returns:
            SearchReplaceResult: Operation result and updated content
        """
        pattern = f"# {section_name}\n(.*?)(?=\n# |$)"
        matches = list(re.finditer(pattern, content, re.DOTALL))
        
        if len(matches) == 0:
            return SearchReplaceResult(False, f"Section '{section_name}' not found", None, 0)
        elif len(matches) > 1:
            return SearchReplaceResult(False, f"Multiple sections named '{section_name}' found", None, len(matches))
        
        match = matches[0]
        current_content = match.group(1).strip()
        
        if position == "start":
            new_section_content = f"{new_entry}\n{current_content}"
        else:  # end
            new_section_content = f"{current_content}\n{new_entry}"
        
        replacement = f"# {section_name}\n{new_section_content}"
        new_content = content[:match.start()] + replacement + content[match.end():]
        
        return SearchReplaceResult(True, "Content added successfully", new_content, 1)

def test_search_replace():
    """Unit tests for SearchReplace functionality"""
    # Test exact replacement
    content = "status: DRAFT\nsome content"
    result = SearchReplace.exact_replace(content, "status: DRAFT", "status: REVIEW")
    assert result.success
    assert "status: REVIEW" in result.new_content
    
    # Test section replacement
    content = "# Section1\nold content\n# Section2\nother content"
    result = SearchReplace.section_replace(content, "Section1", "new content")
    assert result.success
    assert "new content" in result.new_content
    
    # Test adding to section
    content = "# Signals\n- Old signal\n# Other"
    result = SearchReplace.add_to_section(content, "Signals", "- New signal")
    assert result.success
    assert "- Old signal\n- New signal" in result.new_content

if __name__ == "__main__":
    test_search_replace()
from dataclasses import dataclass
from typing import Optional

@dataclass
class SearchReplaceResult:
    success: bool
    message: str
    new_content: Optional[str] = None

class SearchReplace:
    @staticmethod
    def section_replace(content: str, section_name: str, new_content: str) -> SearchReplaceResult:
        """Replace a section's content in the markdown file"""
        try:
            # Find section boundaries
            section_start = content.find(f"# {section_name}")
            if section_start == -1:
                return SearchReplaceResult(False, f"Section '{section_name}' not found")
                
            next_section = content.find("\n# ", section_start + 1)
            section_end = next_section if next_section != -1 else len(content)
            
            # Replace the section
            updated_content = (
                content[:section_start] + 
                new_content + 
                content[section_end:]
            )
            
            return SearchReplaceResult(True, "Section updated", updated_content)
            
        except Exception as e:
            return SearchReplaceResult(False, f"Error replacing section: {str(e)}")

    @staticmethod
    def remove_section(content: str, section_name: str) -> SearchReplaceResult:
        """Remove a section from the markdown content"""
        try:
            # Find section boundaries
            section_start = content.find(f"# {section_name}")
            if section_start == -1:
                return SearchReplaceResult(False, f"Section '{section_name}' not found")
                
            next_section = content.find("\n# ", section_start + 1)
            section_end = next_section if next_section != -1 else len(content)
            
            # Remove the section
            updated_content = content[:section_start] + content[section_end:]
            
            return SearchReplaceResult(True, "Section removed", updated_content)
            
        except Exception as e:
            return SearchReplaceResult(False, f"Error removing section: {str(e)}")
"""
SearchReplace - Utility class for handling search and replace operations in markdown files
"""
from dataclasses import dataclass
from typing import Optional

@dataclass
class SearchReplaceResult:
    """Result of a search/replace operation"""
    success: bool
    content: str = ""
    message: str = ""

class SearchReplace:
    """Handles search and replace operations in markdown files"""
    
    @staticmethod
    def _normalize_text(text: str) -> str:
        """
        Normalise le texte pour une comparaison plus permissive:
        - Supprime tous les espaces
        - Convertit en minuscules
        - Retire les caractères spéciaux
        - Retire les accents
        """
        import unicodedata
        import re
        
        # Convertir en minuscules
        text = text.lower()
        
        # Retirer les accents
        text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
        
        # Retirer tous les caractères spéciaux et espaces
        text = re.sub(r'[^a-z0-9]', '', text)
        
        return text

    @staticmethod
    def section_replace(content: str, section_name: str, new_content: str) -> SearchReplaceResult:
        """Replace a section's content in the markdown file"""
        try:
            # Normaliser le texte pour la recherche
            normalized_content = SearchReplace._normalize_text(content)
            normalized_section = SearchReplace._normalize_text(section_name)
            
            # Trouver la section dans le contenu original
            section_start = -1
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if SearchReplace._normalize_text(line) == normalized_section:
                    section_start = i
                    break
                    
            if section_start == -1:
                return SearchReplaceResult(False, message=f"Section '{section_name}' not found")
                
            # Trouver la fin de la section
            section_end = len(lines)
            for i in range(section_start + 1, len(lines)):
                if lines[i].startswith('#'):
                    section_end = i
                    break
                    
            # Remplacer le contenu
            result = lines[:section_start + 1]  # Inclure le titre de la section
            result.extend([new_content] if new_content else [''])
            result.extend(lines[section_end:])
            
            return SearchReplaceResult(True, content='\n'.join(result))
            
        except Exception as e:
            return SearchReplaceResult(False, message=f"Error during replacement: {str(e)}")
