"""
search_replace.py - Implementation of the SEARCH/REPLACE pattern for Parallagon
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
        """Normalise le texte pour une comparaison plus permissive"""
        # Supprime les espaces multiples et les remplace par un seul espace
        text = re.sub(r'\s+', ' ', text)
        # Supprime les espaces en début et fin
        text = text.strip()
        # Normalise les sauts de ligne
        text = re.sub(r'\r\n|\r|\n', '\n', text)
        # Supprime les espaces en début et fin de chaque ligne
        text = '\n'.join(line.strip() for line in text.split('\n'))
        return text

    @staticmethod
    def validate_replacement(content: str, old_str: str) -> Tuple[bool, str, int]:
        """
        Valide que le texte à remplacer apparaît exactement une fois
        avec une comparaison permissive
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
        try:
            # Échapper les caractères spéciaux dans le titre de section, sauf les #
            escaped_name = re.escape(section_name).replace(r'\#', '#')
            # Utiliser un raw string pour l'expression régulière
            pattern = fr"{escaped_name}\n(.*?)(?=\n#{{1,6}}\s|$)"
            matches = list(re.finditer(pattern, content, re.DOTALL))
            
            if not matches:
                return SearchReplaceResult(False, f"Section '{section_name}' not found", content, 0)
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
        Effectue un remplacement exact avec validation permissive
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
        Add content to a section (at start or end)
        
        Example:
        >>> old_content = "# Signals\\n- Old signal"
        >>> new_content = search_replace.add_to_section(old_content, "Signals", "- New signal")
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
