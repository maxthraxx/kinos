"""
LogManager - Centralized logging management for Parallagon GUI
"""
from datetime import datetime
import tkinter as tk
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum, auto

class LogLevel(Enum):
    """Log levels with their associated symbols and colors"""
    SUCCESS = ("✓", "#4CAF50")
    ERROR = ("❌", "#f44336")
    INFO = ("ℹ", "#2196F3")
    RESET = ("✨", "#FF9800")
    CHANGES = ("↻", "#9C27B0")
    NO_CHANGES = ("≡", "#808080")
    WARNING = ("⚠️", "#FFC107")

@dataclass
class LogEntry:
    """Represents a single log entry"""
    timestamp: str
    message: str
    level: LogLevel
    agent: Optional[str] = None

class LogManager:
    """Manages logging display and formatting in the GUI"""
    
    MAX_LOGS = 1000  # Maximum number of logs to keep in memory
    
    def __init__(self, text_widget: tk.Text):
        """Initialize the log manager with a text widget"""
        self.text_widget = text_widget
        self.logs: list[LogEntry] = []
        self.setup_tags()
        
    def setup_tags(self):
        """Configure text tags for different message types"""
        # Base tag for timestamps
        self.text_widget.tag_config('timestamp', foreground='#a0a0a0')
        
        # Tags for each log level
        for level in LogLevel:
            self.text_widget.tag_config(
                level.name.lower(),
                foreground=level.value[1]
            )
    
    def _determine_log_level(self, message: str) -> LogLevel:
        """Determine the log level based on message content"""
        if "❌" in message:
            return LogLevel.ERROR
        elif "⚠️" in message:
            return LogLevel.WARNING
        elif "✓" in message:
            return LogLevel.SUCCESS if "Aucun changement" not in message else LogLevel.NO_CHANGES
        elif "✨" in message:
            return LogLevel.RESET
        elif any(panel in message for panel in [
            "Specification", "Evaluation", "Management", 
            "Production", "Demande"
        ]):
            return LogLevel.CHANGES
        return LogLevel.INFO

    def _extract_agent_name(self, message: str) -> Optional[str]:
        """Extract agent name from message if present"""
        import re
        match = re.search(r'\[([\w]+Agent)\]', message)
        return match.group(1) if match else None

    def _format_log_entry(self, entry: LogEntry) -> str:
        """Format a log entry for display"""
        agent_prefix = f"[{entry.agent}] " if entry.agent else ""
        return f"[{entry.timestamp}] {agent_prefix}{entry.message}\n"

    def log(self, message: str):
        """Add a formatted log message with timestamp"""
        # Create log entry
        entry = LogEntry(
            timestamp=datetime.now().strftime("%H:%M:%S"),
            message=message,
            level=self._determine_log_level(message),
            agent=self._extract_agent_name(message)
        )
        
        # Add to logs list with size limit
        self.logs.append(entry)
        if len(self.logs) > self.MAX_LOGS:
            self.logs.pop(0)
        
        # Insert timestamp
        self.text_widget.insert(tk.END, f"[{entry.timestamp}] ", 'timestamp')
        
        # Insert message with appropriate tag
        self.text_widget.insert(
            tk.END,
            f"{message}\n",
            entry.level.name.lower()
        )
        
        # Auto-scroll to latest message
        self.text_widget.see(tk.END)
    
    def clear(self):
        """Clear all log messages"""
        self.logs.clear()
        self.text_widget.delete("1.0", tk.END)
    
    def get_logs_by_level(self, level: LogLevel) -> list[LogEntry]:
        """Get all logs of a specific level"""
        return [log for log in self.logs if log.level == level]
    
    def get_logs_by_agent(self, agent_name: str) -> list[LogEntry]:
        """Get all logs from a specific agent"""
        return [log for log in self.logs if log.agent == agent_name]
"""
LogManager - Centralized logging management for Parallagon GUI
"""
from datetime import datetime
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum, auto

class LogLevel(Enum):
    """Log levels with their associated symbols and colors"""
    SUCCESS = ("✓", "#4CAF50")
    ERROR = ("❌", "#f44336")
    INFO = ("ℹ", "#2196F3")
    RESET = ("✨", "#FF9800")
    CHANGES = ("↻", "#9C27B0")
    NO_CHANGES = ("≡", "#808080")
    WARNING = ("⚠️", "#FFC107")

@dataclass
class LogEntry:
    """Represents a single log entry"""
    timestamp: str
    message: str
    level: LogLevel
    agent: Optional[str] = None

class LogManager:
    """Manages logging display and formatting in the GUI"""
    
    MAX_LOGS = 1000  # Maximum number of logs to keep in memory
    
    def __init__(self, text_widget: tk.Text):
        """Initialize the log manager with a text widget"""
        self.text_widget = text_widget
        self.logs: list[LogEntry] = []
        self.setup_tags()
        
    def setup_tags(self):
        """Configure text tags for different message types"""
        # Base tag for timestamps
        self.text_widget.tag_config('timestamp', foreground='#a0a0a0')
        
        # Tags for each log level
        for level in LogLevel:
            self.text_widget.tag_config(
                level.name.lower(),
                foreground=level.value[1]
            )
    
    def _determine_log_level(self, message: str) -> LogLevel:
        """Determine the log level based on message content"""
        if "❌" in message:
            return LogLevel.ERROR
        elif "⚠️" in message:
            return LogLevel.WARNING
        elif "✓" in message:
            return LogLevel.SUCCESS if "Aucun changement" not in message else LogLevel.NO_CHANGES
        elif "✨" in message:
            return LogLevel.RESET
        elif any(panel in message for panel in [
            "Specification", "Evaluation", "Management", 
            "Production", "Demande"
        ]):
            return LogLevel.CHANGES
        return LogLevel.INFO

    def _extract_agent_name(self, message: str) -> Optional[str]:
        """Extract agent name from message if present"""
        import re
        match = re.search(r'\[([\w]+Agent)\]', message)
        return match.group(1) if match else None

    def _format_log_entry(self, entry: LogEntry) -> str:
        """Format a log entry for display"""
        agent_prefix = f"[{entry.agent}] " if entry.agent else ""
        return f"[{entry.timestamp}] {agent_prefix}{entry.message}\n"

    def log(self, message: str):
        """Add a timestamped message to logs"""
        # Create log entry
        entry = LogEntry(
            timestamp=datetime.now().strftime("%H:%M:%S"),
            message=message,
            level=self._determine_log_level(message),
            agent=self._extract_agent_name(message)
        )
        
        # Add to logs list with size limit
        self.logs.append(entry)
        if len(self.logs) > self.MAX_LOGS:
            self.logs.pop(0)
        
        # Insert timestamp
        self.text_widget.insert(tk.END, f"[{entry.timestamp}] ", 'timestamp')
        
        # Insert message with appropriate tag
        self.text_widget.insert(
            tk.END,
            f"{message}\n",
            entry.level.name.lower()
        )
        
        # Auto-scroll to latest message
        self.text_widget.see(tk.END)
    
    def clear(self):
        """Clear all log messages"""
        self.logs.clear()
        self.text_widget.delete("1.0", tk.END)
    
    def export_logs(self, default_filename: str = "parallagon_logs.txt") -> bool:
        """Export logs to a text file"""
        try:
            filepath = filedialog.asksaveasfilename(
                defaultextension=".txt",
                initialfile=default_filename,
                filetypes=[
                    ("Text files", "*.txt"),
                    ("Log files", "*.log"),
                    ("All files", "*.*")
                ]
            )
            
            if not filepath:  # User cancelled
                return False
            
            with open(filepath, 'w', encoding='utf-8') as f:
                for entry in self.logs:
                    f.write(self._format_log_entry(entry))
                    
            self.log(f"✨ Logs exported successfully to: {Path(filepath).name}")
            return True
            
        except Exception as e:
            self.log(f"❌ Error exporting logs: {str(e)}")
            return False
            
    def get_logs_by_level(self, level: LogLevel) -> list[LogEntry]:
        """Get all logs of a specific level"""
        return [log for log in self.logs if log.level == level]
    
    def get_logs_by_agent(self, agent_name: str) -> list[LogEntry]:
        """Get all logs from a specific agent"""
        return [log for log in self.logs if log.agent == agent_name]
