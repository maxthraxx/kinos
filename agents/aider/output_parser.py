"""
AiderOutputParser - Parses and processes Aider command output
"""
import subprocess
from typing import Optional, Dict, Any, List
from utils.logger import Logger

class AiderOutputParser:
    """Parses Aider command output"""
    
    # Commit type icons
    COMMIT_ICONS = {
        'feat': '✨',     # New feature
        'fix': '🐛',      # Bug fix
        'docs': '📚',     # Documentation
        'style': '💎',    # Style/formatting
        'refactor': '♻️',  # Refactoring
        'perf': '⚡️',     # Performance
        'test': '🧪',     # Tests
        'build': '📦',    # Build/dependencies
        'ci': '🔄',       # CI/CD
        'chore': '🔧',    # Maintenance
        'revert': '⏪',    # Revert changes
        'merge': '🔗',    # Merge changes
        'update': '📝',   # Content updates
        'add': '➕',      # Add content/files
        'remove': '➖',    # Remove content/files
        'move': '🚚',     # Move/rename content
        'cleanup': '🧹',  # Code cleanup
        'format': '🎨',   # Formatting changes
        'optimize': '🚀'  # Optimizations
    }
    
    def __init__(self, logger: Logger):
        """Initialize with logger"""
        self.logger = logger
        
    def _parse_file_changes(self, output: str) -> Dict[str, Any]:
        """
        Parse file changes from output
        
        Args:
            output: Command output string
            
        Returns:
            Dict with changes info
        """
        changes = {
            'modified_files': set(),
            'added_files': set(),
            'deleted_files': set()
        }
        
        try:
            for line in output.splitlines():
                if "Wrote " in line:
                    file_path = line.split("Wrote ")[1].split()[0]
                    changes['modified_files'].add(file_path)
                elif "Created " in line:
                    file_path = line.split("Created ")[1].split()[0]
                    changes['added_files'].add(file_path)
                elif "Deleted " in line:
                    file_path = line.split("Deleted ")[1].split()[0]
                    changes['deleted_files'].add(file_path)
                    
            return changes
            
        except Exception as e:
            self.logger.log(f"Error parsing file changes: {str(e)}", 'error')
            return changes

    def _parse_error_messages(self, output: str) -> List[str]:
        """
        Extract error messages from output
        
        Args:
            output: Command output string
            
        Returns:
            List of error messages
        """
        errors = []
        
        try:
            for line in output.splitlines():
                lower_line = line.lower()
                if any(err in lower_line for err in [
                    'error', 'exception', 'failed', 'can\'t initialize'
                ]):
                    errors.append(line.strip())
                    
            return errors
            
        except Exception as e:
            self.logger.log(f"Error parsing errors: {str(e)}", 'error')
            return errors

    def _format_commit_message(self, commit_type: str, message: str) -> str:
        """
        Format commit message with icon
        
        Args:
            commit_type: Type of commit
            message: Commit message
            
        Returns:
            Formatted message with icon
        """
        icon = self.COMMIT_ICONS.get(commit_type, '🔨')
        return f"{icon} {message}"

    def parse_output(self, process: subprocess.Popen) -> Optional[str]:
        """
        Parse Aider command output
        
        Args:
            process: Running Aider process
            
        Returns:
            Optional[str]: Parsed output or None on error
        """
        output_lines = []
        
        try:
            # Read output while process is running
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                    
                line = line.rstrip()
                if not line:
                    continue
                    
                # Handle Windows console warning
                if "No Windows console found" in line:
                    self.logger.log(
                        "Windows console initialization warning - non-critical",
                        'warning'
                    )
                    continue
                    
                # Parse commit messages
                if "Commit" in line:
                    self._parse_commit_line(line)
                    
                output_lines.append(line)
                
            # Get return code
            return_code = process.wait(timeout=5)
            
            # Combine output
            output = "\n".join(output_lines)
            
            # Parse changes and errors
            changes = self._parse_file_changes(output)
            errors = self._parse_error_messages(output)
            
            # Log results
            if changes['modified_files']:
                self.logger.log(f"Modified files: {changes['modified_files']}", 'info')
            if changes['added_files']:
                self.logger.log(f"Added files: {changes['added_files']}", 'info')
            if changes['deleted_files']:
                self.logger.log(f"Deleted files: {changes['deleted_files']}", 'info')
                
            if errors:
                self.logger.log(f"Errors detected:\n" + "\n".join(errors), 'error')
                return None
                
            if return_code != 0:
                self.logger.log(f"Process failed with code {return_code}", 'error')
                return None
                
            return output
            
        except Exception as e:
            self.logger.log(f"Error parsing output: {str(e)}", 'error')
            return None
            
    def _parse_commit_line(self, line: str) -> None:
        """Parse and log a commit line"""
        try:
            # Extract commit hash and message
            parts = line.split()
            commit_hash = parts[1]
            message = ' '.join(parts[2:])
            
            # Detect commit type
            commit_type = None
            for known_type in self.COMMIT_ICONS:
                if message.lower().startswith(f"{known_type}:"):
                    commit_type = known_type
                    message = message[len(known_type)+1:].strip()
                    break
                    
            # Get icon
            icon = self.COMMIT_ICONS.get(commit_type, '🔨')
            
            # Log commit
            self.logger.log(
                f"{icon} {commit_hash}: {message}",
                'success'
            )
            
        except Exception as e:
            self.logger.log(f"Error parsing commit: {str(e)}", 'error')