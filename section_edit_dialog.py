"""
SectionEditDialog - Dialog for editing section content
"""
import tkinter as tk
from tkinter import ttk
from section import Section

class SectionEditDialog:
    def __init__(self, parent, section: Section):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Edit {section.title}")
        self.section = section
        self.result = None
        
        # Content area
        content_frame = ttk.LabelFrame(self.dialog, text="Content")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.content_text = tk.Text(content_frame, height=10, wrap=tk.WORD)
        self.content_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        if section.content:
            self.content_text.insert("1.0", section.content)
            
        # Constraints display
        if section.constraints:
            constraints_frame = ttk.LabelFrame(self.dialog, text="Constraints")
            constraints_frame.pack(fill=tk.X, padx=5, pady=5)
            ttk.Label(
                constraints_frame,
                text=section.constraints,
                wraplength=550
            ).pack(padx=5, pady=5)
            
        # Add todos area
        if section.todo:
            todos_frame = ttk.LabelFrame(self.dialog, text="Tâches à faire")
            todos_frame.pack(fill=tk.X, padx=5, pady=5)
            
            for task in section.todo:
                ttk.Label(
                    todos_frame, 
                    text=f"• {task}", 
                    wraplength=550
                ).pack(anchor=tk.W, padx=5, pady=2)
            
        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(
            button_frame,
            text="Cancel",
            command=self.dialog.destroy
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Save",
            command=self._save
        ).pack(side=tk.RIGHT)
        
        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        parent.wait_window(self.dialog)
        
    def _save(self):
        """Save changes and close dialog"""
        self.result = self.content_text.get("1.0", tk.END).strip()
        self.dialog.destroy()
