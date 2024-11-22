import os
import asyncio
import logging
from pathlib import Path
import fnmatch
from utils.logger import Logger
import openai
import tiktoken
from dotenv import load_dotenv

class MapManager:
    """
    Manager class for generating and maintaining project structure maps.
    
    Responsible for:
    - Generating hierarchical maps of project structure
    - Maintaining global project map
    - Analyzing file roles and relationships
    - Tracking structural changes
    
    Attributes:
        logger (Logger): Logging utility instance
        tokenizer (tiktoken.Encoding): GPT tokenizer for content analysis
        api_semaphore (asyncio.Semaphore): Rate limiter for API calls
    """
    
    def __init__(self):
        """Initialize the map manager with required components."""
        self.logger = Logger()
        load_dotenv()
        openai.api_key = os.getenv('OPENAI_API_KEY')
        if not openai.api_key:
            raise ValueError("OpenAI API key not found in environment variables")
        self.tokenizer = tiktoken.encoding_for_model("gpt-4")
        self.api_semaphore = asyncio.Semaphore(10)
    def _analyze_folder_level(self, folder_path: str, files_content: dict, 
                            subfolders: list, mission_content: str, 
                            objective_content: str) -> dict:
        """
        Analyze a single folder level with its files and immediate subfolders.
        
        Args:
            folder_path (str): Path to current folder
            files_content (dict): Dictionary of filename to file content
            subfolders (list): List of immediate subfolder names
            mission_content (str): Overall mission context
            objective_content (str): Current objective context
            
        Returns:
            dict: Folder analysis including:
                - path: Folder path
                - purpose: Folder's purpose
                - files: List of file analyses
                - relationships: Dict of folder relationships
        """
        try:
            # Get folder context including purpose and relationships
            folder_context = self._get_folder_context(
                folder_path=folder_path,
                files=list(files_content.keys()),
                subfolders=subfolders,
                mission_content=mission_content,
                objective_content=objective_content
            )
            
            # Analyze each file in the folder
            analyzed_files = []
            for filename in files_content:
                try:
                    file_analysis = self._analyze_file(filename, folder_context)
                    analyzed_files.append(file_analysis)
                except Exception as e:
                    self.logger.warning(f"Failed to analyze file {filename}: {str(e)}")
                    analyzed_files.append({
                        'name': filename,
                        'role': '⚠️ ERROR',
                        'description': f'Analysis failed: {str(e)}'
                    })
            
            return {
                'path': folder_path,
                'purpose': folder_context['purpose'],
                'files': analyzed_files,
                'relationships': folder_context['relationships']
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze folder level {folder_path}: {str(e)}")
            raise

    def _analyze_folder_hierarchy(self, folder_path: str, mission_content: str, objective_content: str) -> dict:
        """
        Analyze folder and all its subfolders recursively, with complete context.
        
        Args:
            folder_path (str): Current folder to analyze
            mission_content (str): Overall mission context
            objective_content (str): Current objective context
            
        Returns:
            dict: Complete folder analysis including:
                - Folder purpose
                - File categorizations
                - Subfolder relationships
                - Structural context
                
        Raises:
            ValueError: If folder_path is invalid
            OSError: If folder cannot be accessed
            Exception: For other unexpected errors
        """
        if not folder_path:
            raise ValueError("folder_path cannot be empty")
            
        if not os.path.exists(folder_path):
            raise ValueError(f"Folder does not exist: {folder_path}")
            
        if not os.path.isdir(folder_path):
            raise ValueError(f"Path is not a directory: {folder_path}")
            
        try:
            # Get immediate files and their contents
            files_content = {}
            for file in self._get_folder_files(folder_path):
                try:
                    file_path = os.path.join(folder_path, file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        files_content[file] = f.read()
                except (OSError, UnicodeDecodeError) as e:
                    self.logger.warning(f"Could not read {file}: {str(e)}")
                    files_content[file] = ""
                except Exception as e:
                    self.logger.error(f"Unexpected error reading {file}: {str(e)}")
                    files_content[file] = ""

            # Get subfolder structure
            subfolders = self._get_subfolders(folder_path)
            
            # Generate complete folder context
            folder_analysis = self._analyze_folder_level(
                folder_path=folder_path,
                files_content=files_content,
                subfolders=subfolders,
                mission_content=mission_content,
                objective_content=objective_content
            )

            # Recursively analyze subfolders
            folder_analysis['subfolders'] = {}
            for subfolder in subfolders:
                try:
                    subfolder_path = os.path.join(folder_path, subfolder)
                    folder_analysis['subfolders'][subfolder] = self._analyze_folder_hierarchy(
                        folder_path=subfolder_path,
                        mission_content=mission_content,
                        objective_content=objective_content
                    )
                except Exception as e:
                    self.logger.error(f"Failed to analyze subfolder {subfolder}: {str(e)}")
                    folder_analysis['subfolders'][subfolder] = {
                        'path': subfolder_path,
                        'purpose': f'Analysis failed: {str(e)}',
                        'files': [],
                        'relationships': {},
                        'subfolders': {}
                    }

            return folder_analysis

        except Exception as e:
            self.logger.error(f"Failed to analyze folder hierarchy for {folder_path}: {str(e)}")
            raise

    def _get_folder_files(self, folder_path: str) -> list:
        """Get list of files in folder, respecting ignore patterns."""
        ignore_patterns = self._get_ignore_patterns()
        files = []
        
        for entry in os.scandir(folder_path):
            if entry.is_file():
                rel_path = os.path.relpath(entry.path, '.')
                if not self._should_ignore(rel_path, ignore_patterns):
                    files.append(entry.name)
                    
        return sorted(files)

    def _get_subfolders(self, folder_path: str) -> list:
        """Get list of subfolders, respecting ignore patterns."""
        ignore_patterns = self._get_ignore_patterns()
        folders = []
        
        for entry in os.scandir(folder_path):
            if entry.is_dir():
                rel_path = os.path.relpath(entry.path, '.')
                if not self._should_ignore(rel_path, ignore_patterns):
                    folders.append(entry.name)
                    
        return sorted(folders)

    def _create_folder_context_prompt(self, folder_path: str, files: list, 
                                    subfolders: list, mission_content: str, 
                                    objective_content: str) -> str:
        """
        Create prompt for analyzing folder context.
        
        Args:
            folder_path (str): Path to current folder
            files (list): List of files in folder
            subfolders (list): List of subfolders
            mission_content (str): Overall mission context
            objective_content (str): Current objective context
            
        Returns:
            str: Formatted prompt for GPT analysis
        """
        return f"""Analyze this folder's purpose and relationships:

Current Folder: {folder_path}

Files Present:
{chr(10).join(f'- {f}' for f in files)}

Subfolders:
{chr(10).join(f'- {f}' for f in subfolders)}

Mission Context:
{mission_content}

Current Objective:
{objective_content}

Analyze and provide:
1. FOLDER PURPOSE
   - Main purpose of this folder
   - How it supports the mission
   - Why files are grouped here

2. FILE ANALYSIS
   - Role of each file
   - How files work together
   - Critical vs. supporting files

3. RELATIONSHIPS
   - Parent: How this connects to parent folder
   - Siblings: Relationship with peer folders
   - Children: Purpose of subfolders

Format response with these exact headers:
Purpose: [folder purpose]
Parent: [parent relationship]
Siblings: [sibling relationships]
Children: [children relationships]"""

    def _get_folder_context(self, folder_path: str, files: list, subfolders: list,
                          mission_content: str, objective_content: str) -> dict:
        """
        Get folder purpose and relationships using GPT.
        
        Args:
            folder_path (str): Path to current folder
            files (list): List of files in folder
            subfolders (list): List of subfolders
            mission_content (str): Overall mission context
            objective_content (str): Current objective context
            
        Returns:
            dict: Folder context including purpose and relationships
            
        Raises:
            ValueError: If input parameters are invalid
            Exception: For API or parsing errors
        """
        if not folder_path:
            raise ValueError("folder_path cannot be empty")
            
        try:
            client = openai.OpenAI()
            prompt = self._create_folder_context_prompt(
                folder_path, files, subfolders,
                mission_content, objective_content
            )
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a technical architect analyzing project structure and organization."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            # Parse response into structure
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from GPT")
                
            context = {
                'purpose': '',
                'relationships': {
                    'parent': '',
                    'siblings': '',
                    'children': ''
                }
            }
            
            # Parse response line by line
            for line in content.split('\n'):
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith('Purpose:'):
                    context['purpose'] = line.replace('Purpose:', '').strip()
                elif line.startswith('Parent:'):
                    context['relationships']['parent'] = line.replace('Parent:', '').strip()
                elif line.startswith('Siblings:'):
                    context['relationships']['siblings'] = line.replace('Siblings:', '').strip()
                elif line.startswith('Children:'):
                    context['relationships']['children'] = line.replace('Children:', '').strip()
            
            # Validate parsed content
            if not context['purpose']:
                raise ValueError("Failed to parse folder purpose from response")
                
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to get folder context for {folder_path}: {str(e)}")
            raise

    def _analyze_file(self, filename: str, folder_context: dict) -> dict:
        """
        Analyze single file's role and purpose.
        
        Args:
            filename (str): Name of file to analyze
            folder_context (dict): Context information about the containing folder
            
        Returns:
            dict: Analysis containing:
                - name: Filename
                - role: Technical role with emoji
                - description: Purpose description
        """
        try:
            client = openai.OpenAI()
            prompt = self._create_file_analysis_prompt(filename, folder_context)
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a technical analyst identifying file roles and purposes."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            # Parse response into structure
            content = response.choices[0].message.content
            parts = content.split(' - ', 1)
            
            return {
                'name': filename,
                'role': parts[0].strip(),
                'description': parts[1].strip() if len(parts) > 1 else ''
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze file {filename}: {str(e)}")
            raise

    def _generate_map_content(self, hierarchy: dict) -> str:
        """
        Generate map content from folder hierarchy.
        """
        def _format_folder(folder_data: dict, level: int = 0) -> str:
            indent = "  " * level
            content = []
            
            # Add folder header and purpose
            content.append(f"{indent}## {folder_data['path']}")
            content.append(f"{indent}Purpose: {folder_data['purpose']}\n")
            
            # Add files
            for file in folder_data['files']:
                content.append(f"{indent}- {file['name']} ({file['role']}) - {file['description']}")
            
            # Add relationships if not root
            if level > 0:
                content.append(f"\n{indent}Relationships:")
                content.append(f"{indent}- Parent: {folder_data['relationships']['parent']}")
                content.append(f"{indent}- Siblings: {folder_data['relationships']['siblings']}")
                if folder_data['subfolders']:
                    content.append(f"{indent}- Children: {folder_data['relationships']['children']}")
            
            # Recursively add subfolders
            for subfolder_name, subfolder_data in folder_data['subfolders'].items():
                content.append("\n" + _format_folder(subfolder_data, level + 1))
                
            return "\n".join(content)
        
        return "# Project Map\n\n" + _format_folder(hierarchy)
    def _create_file_analysis_prompt(self, filename: str, folder_context: dict) -> str:
        """Create prompt for analyzing a single file's role."""
        return f"""Analyze this file's role in its folder:

Filename: {filename}
Folder Purpose: {folder_context['purpose']}

Determine the file's:
1. Technical role (using emoji categories below)
2. Specific purpose in this folder
3. How it supports the folder's purpose

Core Project Files:
* PRIMARY DELIVERABLE (📊) - Final output files
* SPECIFICATION (📋) - Requirements and plans
* IMPLEMENTATION (⚙️) - Core functionality
* DOCUMENTATION (📚) - User guides and docs

Support Files:
* CONFIGURATION (⚡) - Settings and configs
* UTILITY (🛠️) - Helper functions
* TEST (🧪) - Test cases
* BUILD (📦) - Build scripts

Working Files:
* WORK DOCUMENT (✍️) - Active files
* DRAFT (📝) - In-progress work
* TEMPLATE (📄) - Reusable patterns
* ARCHIVE (📂) - Historical versions

Data Files:
* SOURCE DATA (💾) - Input data
* GENERATED (⚡) - Created outputs
* CACHE (💫) - Temporary data
* BACKUP (💿) - System backups

Return in format:
[EMOJI ROLE] - [Purpose description]"""
    def _format_files_content(self, files_content: dict) -> str:
        """Format files content for prompt, with reasonable length limits."""
        formatted = []
        for filename, content in files_content.items():
            # Truncate very large files
            if len(content) > 1000:
                content = content[:1000] + "...[truncated]"
            formatted.append(f"## {filename}\n```\n{content}\n```")
        return "\n\n".join(formatted)

    def _parse_folder_analysis(self, analysis_text: str) -> dict:
        """Parse GPT analysis response into structured format."""
        sections = {
            'purpose': '',
            'files': [],
            'relationships': {'parent': '', 'siblings': '', 'children': ''}
        }
        
        current_section = None
        current_file = None
        
        for line in analysis_text.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('1. FOLDER PURPOSE'):
                current_section = 'purpose'
            elif line.startswith('2. FILE ANALYSIS'):
                current_section = 'files'
            elif line.startswith('3. RELATIONSHIPS'):
                current_section = 'relationships'
            elif current_section == 'purpose' and line.startswith('-'):
                sections['purpose'] += line[1:].strip() + ' '
            elif current_section == 'files' and line.startswith('-'):
                # Parse file entry: "- filename.ext (📊 ROLE) - description"
                parts = line[1:].split(' - ', 1)
                if len(parts) == 2:
                    name_role = parts[0].split(' (')
                    if len(name_role) == 2:
                        sections['files'].append({
                            'name': name_role[0].strip(),
                            'role': name_role[1].rstrip(')'),
                            'description': parts[1].strip()
                        })
            elif current_section == 'relationships':
                if line.startswith('- Parent:'):
                    sections['relationships']['parent'] = line.split(':', 1)[1].strip()
                elif line.startswith('- Siblings:'):
                    sections['relationships']['siblings'] = line.split(':', 1)[1].strip()
                elif line.startswith('- Children:'):
                    sections['relationships']['children'] = line.split(':', 1)[1].strip()
                    
        return sections
