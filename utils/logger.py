import os
import sys
from datetime import datetime
from typing import Optional
from utils.path_manager import PathManager

class Logger:
    # ANSI color codes
    COLORS = {
        'info': '\033[94m',     # Blue
        'success': '\033[92m',  # Green
        'warning': '\033[93m',  # Yellow
        'error': '\033[91m',    # Red
        'debug': '\033[90m',    # Gray
        'critical': '\033[95m', # Magenta
        'redacteur': '\033[95m', # Purple
        'reset': '\033[0m'      # Reset to default
    }
    
    def __init__(self, force_color=None):
        # Détection plus robuste de l'environnement coloré
        self.is_tty = sys.stdout.isatty()
        self.force_color = force_color
        self._name = "KinOSLogger"

    def _should_colorize(self):
        """Déterminer si les couleurs doivent être appliquées"""
        # Conditions pour forcer la couleur
        if self.force_color is True:
            return True
        
        # Conditions pour désactiver la couleur
        if self.force_color is False:
            return False
        
        # Détection automatique
        return (
            self.is_tty or 
            'TERM' in os.environ or 
            os.name == 'nt' or  # Windows support
            sys.platform == 'win32' or 
            sys.platform == 'cygwin'
        )

    def log(self, message: str, level: str = 'info', **kwargs):
        """Main logging method that handles all logging cases"""
        try:
            # Get timestamp
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Prepare log message
            formatted_message = f"[{timestamp}] [{level.upper()}] {message}"
            
            # Colorize if appropriate
            if self._should_colorize():
                color = self.COLORS.get(level, self.COLORS['info'])
                reset = self.COLORS['reset']
                colored_message = f"{color}{formatted_message}{reset}"
                print(colored_message)
            else:
                # Plain text for non-TTY or when color is disabled
                print(formatted_message)
            
            # Optional file logging
            file_path = kwargs.get('file_path', os.path.join(PathManager.get_logs_path(), 'agent_operations.log'))
            
            # Ensure log directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(f"{formatted_message}\n")
                
        except Exception as e:
            # Fallback logging
            print(f"Logging error: {e}")
            print(f"Original message: {message}")

def configure_cli_logger(force_color=None):
    """
    Configure CLI logger with intelligent color detection
    
    Args:
        force_color (bool, optional): 
            - True: Force color output
            - False: Disable color output
            - None: Auto-detect
    
    Returns:
        Logger instance with appropriate color configuration
    """
    # Check environment variables first
    if os.environ.get('NO_COLOR') is not None:
        force_color = False
    elif os.environ.get('FORCE_COLOR') is not None:
        force_color = True
    
    # Create logger instance
    logger = Logger(force_color)
    
    return logger

def configure_cli_logger(force_color=None):
    """
    Configure CLI logger with intelligent color detection
    
    Args:
        force_color (bool, optional): 
            - True: Force color output
            - False: Disable color output
            - None: Auto-detect
    
    Returns:
        Logger instance with appropriate color configuration
    """
    # Check environment variables first
    if os.environ.get('NO_COLOR') is not None:
        force_color = False
    elif os.environ.get('FORCE_COLOR') is not None:
        force_color = True
    
    # Create logger instance
    logger = Logger(force_color)
    
    return logger
    
    def _should_colorize(self):
        """Determine if colors should be applied"""
        return self.force_color or (self.is_tty and 'TERM' in os.environ)
    
    def __str__(self):
        return self._name
        
    def __repr__(self):
        return self._name
    
    def log(self, message: str, level: str = 'info', **kwargs):
        """Main logging method that handles all cases"""
        try:
            # Always remove level from kwargs to prevent duplicates
            kwargs.pop('level', None)
            
            # Extract file_path from kwargs
            file_path = kwargs.pop('file_path', None)
            
            # Get timestamp
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Prepare log message
            formatted_message = f"[{timestamp}] [{level.upper()}] {message}"
            
            # Colorize if appropriate
            if self._should_colorize():
                color = self.COLORS.get(level, self.COLORS['info'])
                reset = self.COLORS['reset']
                colored_message = f"{color}{formatted_message}{reset}"
                print(colored_message)
            else:
                # Plain text for non-TTY or when color is disabled
                print(formatted_message)
            
            # File logging remains the same
            if not file_path:
                file_path = os.path.join(PathManager.get_logs_path(), 'agent_operations.log')
                
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(f"{formatted_message}\n")
                
        except Exception as e:
            # Fallback logging
            print(f"Logging error: {e}")
            print(f"Original message: {message}")
    
    def __call__(self, message: str, level: str = 'info', **kwargs):
        """Unified call method that handles all logging patterns"""
        # Remove level from kwargs to avoid duplicate
        kwargs.pop('level', None)
        self.log(message, level, **kwargs)

    def log_path_operation(self, operation: str, path: str, success: bool, error: Optional[str] = None):
        """
        Log file/path operations with consistent formatting
        
        Args:
            operation: Type of operation (read/write/create/etc)
            path: Path being operated on
            success: Whether operation succeeded
            error: Optional error message
        """
        try:
            # Format relative path for cleaner output
            rel_path = os.path.relpath(path, os.getcwd())
            
            if success:
                self.log(f"✓ {operation}: {rel_path}", 'success')
            else:
                error_msg = f" ({error})" if error else ""
                self.log(f"❌ {operation} failed: {rel_path}{error_msg}", 'error')
                
        except Exception as e:
            # Fallback to full path if relative path fails
            if success:
                self.log(f"✓ {operation}: {path}", 'success')
            else:
                error_msg = f" ({error})" if error else ""
                self.log(f"❌ {operation} failed: {path}{error_msg}", 'error')

    def log_path_validation(self, path: str, valid: bool, reason: Optional[str] = None):
        """
        Log path validation results
        
        Args:
            path: Path being validated
            valid: Whether path is valid
            reason: Optional reason for invalid path
        """
        try:
            rel_path = os.path.relpath(path, os.getcwd())
            
            if valid:
                self.log(f"✓ Valid path: {rel_path}", 'success')
            else:
                reason_msg = f" ({reason})" if reason else ""
                self.log(f"❌ Invalid path: {rel_path}{reason_msg}", 'error')
                
        except Exception as e:
            # Fallback to full path
            if valid:
                self.log(f"✓ Valid path: {path}", 'success')
            else:
                reason_msg = f" ({reason})" if reason else ""
                self.log(f"❌ Invalid path: {path}{reason_msg}", 'error')

    def log_path_change(self, old_path: str, new_path: str, success: bool, error: Optional[str] = None):
        """
        Log path change operations
        
        Args:
            old_path: Original path
            new_path: New path
            success: Whether change succeeded
            error: Optional error message
        """
        try:
            rel_old = os.path.relpath(old_path, os.getcwd())
            rel_new = os.path.relpath(new_path, os.getcwd())
            
            if success:
                self.log(f"✓ Path changed: {rel_old} → {rel_new}", 'success')
            else:
                error_msg = f" ({error})" if error else ""
                self.log(f"❌ Path change failed: {rel_old} → {rel_new}{error_msg}", 'error')
                
        except Exception as e:
            # Fallback to full paths
            if success:
                self.log(f"✓ Path changed: {old_path} → {new_path}", 'success')
            else:
                error_msg = f" ({error})" if error else ""
                self.log(f"❌ Path change failed: {old_path} → {new_path}{error_msg}", 'error')

    def _log(self, message: str, level: str = 'info', **kwargs):
        """Internal logging method"""
        # Remove level from kwargs to avoid duplicate
        kwargs.pop('level', None)
        # Call log() without explicitly passing level as kwarg
        self.log(message, level, **kwargs)
