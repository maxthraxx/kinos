// Debounce utility function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func.apply(this, args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

const ParallagonApp = {
    delimiters: ['${', '}'],  // Use different delimiters to avoid Jinja2 conflicts
    data() {
        return {
            logCounter: 0,  // Counter for unique log IDs
            running: false,
            loading: false,
            error: null,
            suiviEntries: [], // Store suivi entries
            missionSidebarCollapsed: false,
            currentMission: null,
            missions: [], // Will be loaded from API
            isCreatingMission: false,
            newMissionName: '',
            missionIdCounter: 3, // Start after existing missions
            runningAgents: new Set(), // Track which agents are running
            notifications: [],
            connectionStatus: 'disconnected',
            activeTab: 'demande',
            tabIds: {
                'demande.md': 'demande',
                'specifications.md': 'specifications',
                'management.md': 'management',
                'production.md': 'production',
                'evaluation.md': 'evaluation',
                'suivi.md': 'suivi'
            },
            tabs: [
                { id: 'demande', name: 'Demande', icon: 'mdi mdi-file-document-outline' },
                { id: 'specifications', name: 'Specifications', icon: 'mdi mdi-file-tree' },
                { id: 'management', name: 'Management', icon: 'mdi mdi-account-supervisor' },
                { id: 'production', name: 'Production', icon: 'mdi mdi-code-braces' },
                { id: 'evaluation', name: 'Evaluation', icon: 'mdi mdi-check-circle' },
                { id: 'suivi', name: 'Suivi', icon: 'mdi mdi-history' },
                { id: 'contexte', name: 'Contexte', icon: 'mdi mdi-file-tree-outline' },
                { id: 'suivi-mission', name: 'Logs', icon: 'mdi mdi-console-line' }
            ],
            content: {
                demande: '',
                specifications: '',
                management: '',
                production: '',
                evaluation: '',
                suivi: ''
            },
            previousContent: {},
            suiviUpdateInterval: null,
            panels: [
                { id: 'specifications', name: 'Specifications', icon: 'mdi mdi-file-tree', updating: false },
                { id: 'management', name: 'Management', icon: 'mdi mdi-account-supervisor', updating: false },
                { id: 'production', name: 'Production', icon: 'mdi mdi-code-braces', updating: false },
                { id: 'evaluation', name: 'Evaluation', icon: 'mdi mdi-check-circle', updating: false }
            ],
            logs: [],
            demandeChanged: false,
            updateInterval: null,
            previousContent: {},
            ws: null
        }
    },
    methods: {
        async updateSuiviEntries() {
            try {
                console.log('Fetching suivi entries...');
                const response = await fetch('/api/suivi');
                if (!response.ok) {
                    throw new Error('Failed to fetch suivi entries');
                }
                const data = await response.json();
                
                if (!data.content) {
                    console.warn('No content in suivi data');
                    this.suiviEntries = [];
                    return;
                }

                // Split content into lines and filter empty lines
                const lines = data.content.split('\n').filter(line => line.trim());
                console.log('Raw lines:', lines);

                // Parse entries with more flexible timestamp matching
                const entries = [];
                let currentEntry = null;

                for (const line of lines) {
                    const timestampMatch = line.match(/^\[(\d{2}:\d{2}:\d{2})\](.*)/);
                    
                    if (timestampMatch) {
                        // If we have a previous entry, save it
                        if (currentEntry) {
                            entries.push(currentEntry);
                        }
                        
                        // Start new entry
                        const [, timestamp, message] = timestampMatch;
                        currentEntry = {
                            id: `suivi-${entries.length}`,
                            timestamp,
                            message: message.trim(),
                            type: 'info'  // Default type
                        };

                        // Determine type based on content
                        if (message.includes('réinitialisé')) {
                            currentEntry.type = 'warning';
                        } else if (message.includes('✓')) {
                            currentEntry.type = 'success';
                        } else if (message.includes('❌')) {
                            currentEntry.type = 'error';
                        } else if (message.includes('⚠️')) {
                            currentEntry.type = 'warning';
                        }
                    } else if (currentEntry) {
                        // Add line to current entry's message
                        currentEntry.message += '\n' + line.trim();
                    }
                }

                // Don't forget to add the last entry
                if (currentEntry) {
                    entries.push(currentEntry);
                }

                console.log('Parsed entries:', entries);
                this.suiviEntries = entries;

            } catch (error) {
                console.error('Error updating suivi entries:', error);
                this.addNotification('error', 'Failed to update suivi entries');
            }
        },

        async linkExternalMission() {
            try {
                // Utiliser l'API moderne de sélection de dossier
                const directoryHandle = await window.showDirectoryPicker();
                console.log('Selected directory:', directoryHandle.name);
                
                // Obtenir le chemin complet via une requête spéciale
                const response = await fetch('/api/missions/get-directory-path', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ 
                        name: directoryHandle.name,
                        type: 'directory'
                    })
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.error || 'Failed to get directory path');
                }

                const { path } = await response.json();
                console.log('Resolved path:', path);
                
                // Créer le lien avec le chemin complet
                const linkResponse = await fetch('/api/missions/link', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ path })
                });
                
                if (linkResponse.ok) {
                    const mission = await linkResponse.json();
                    this.missions.unshift(mission);
                    this.addNotification('success', `Dossier externe lié avec succès`);
                } else {
                    const error = await linkResponse.json();
                    throw new Error(error.error);
                }
                
            } catch (error) {
                // Ignorer l'erreur si l'utilisateur annule la sélection
                if (error.name === 'AbortError') {
                    return;
                }
                console.error('Error linking external mission:', error);
                this.addNotification('error', `Erreur lors de la liaison: ${error.message}`);
            }
        },

        toggleMissionSidebar() {
            this.missionSidebarCollapsed = !this.missionSidebarCollapsed;
        },
        
        async loadMissionContent(missionId) {
            try {
                const response = await fetch(`/api/missions/${missionId}/content`);
                if (!response.ok) {
                    throw new Error('Failed to load mission content');
                }
                const content = await response.json();
                
                // Update content in all panels
                this.content = content;
                
                // Update UI to show we're viewing this mission
                this.currentMission = this.missions.find(m => m.id === missionId);
                
                this.addNotification('success', `Loaded content for mission "${this.currentMission.name}"`);
                
            } catch (error) {
                console.error('Error loading mission content:', error);
                this.addNotification('error', `Failed to load mission content: ${error.message}`);
            }
        },

        async selectMission(mission) {
            try {
                // Store previous mission state
                const wasRunning = this.running;
                
                // Stop agents if running
                if (wasRunning) {
                    await fetch('/api/stop', { method: 'POST' });
                    this.running = false;
                }
                
                this.currentMission = mission;
                await this.loadMissionContent(mission.id);
                
                // Restart agents if they were running
                if (wasRunning) {
                    await fetch('/api/start', { method: 'POST' });
                    this.running = true;
                }
                
                this.addNotification('success', `Mission "${mission.name}" selected`);
                
            } catch (error) {
                console.error('Error selecting mission:', error);
                this.addNotification('error', `Error selecting mission: ${error.message}`);
            }
        },

        startCreatingMission() {
            this.isCreatingMission = true;
            this.$nextTick(() => {
                this.$refs.newMissionInput.focus();
            });
        },

        cancelCreatingMission() {
            this.isCreatingMission = false;
            this.newMissionName = '';
        },

        async loadMissions() {
            try {
                this.loading = true;  // Add loading state
                const response = await fetch('/api/missions');
            
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
            
                const missions = await response.json();
            
                if (Array.isArray(missions)) {
                    this.missions = missions;
                    if (missions.length > 0) {
                        this.addNotification('success', 'Missions loaded successfully');
                    } else {
                        this.addNotification('info', 'No missions available. Please create a new mission.');
                    }
                } else {
                    throw new Error('Invalid missions data received');
                }
            
            } catch (error) {
                console.error('Error loading missions:', error);
                this.addNotification('error', `Failed to load missions: ${error.message}`);
                this.missions = [];  // Reset missions on error
            
            } finally {
                this.loading = false;  // Clear loading state
            }
        },

        async createMission() {
            if (!this.newMissionName.trim()) {
                this.addNotification('error', 'Mission name cannot be empty');
                return;
            }

            try {
                const response = await fetch('/api/missions', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        name: this.newMissionName.trim()
                    })
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.error || 'Failed to create mission');
                }

                const mission = await response.json();
                this.missions.unshift(mission);
                await this.selectMission(mission);
                this.isCreatingMission = false;
                this.newMissionName = '';
                this.addNotification('success', `Mission "${mission.name}" created`);

            } catch (error) {
                console.error('Error creating mission:', error);
                this.addNotification('error', error.message);
                this.isCreatingMission = false;
                this.newMissionName = '';
            }
        },

        async loadInitialContent() {
            try {
                this.loading = true;
                
                // Si une mission est sélectionnée, charger son contenu
                if (this.currentMission) {
                    const response = await fetch(`/api/missions/${this.currentMission.id}/content`);
                    if (!response.ok) {
                        throw new Error('Failed to load mission content');
                    }
                    const data = await response.json();
                    this.content = data;
                    this.previousContent = { ...data };
                    
                    this.addNotification('success', `Mission "${this.currentMission.name}" content loaded`);
                } else {
                    // Si aucune mission n'est sélectionnée, charger la première mission disponible
                    const missionsResponse = await fetch('/api/missions');
                    if (missionsResponse.ok) {
                        const missions = await missionsResponse.json();
                        if (missions.length > 0) {
                            this.currentMission = missions[0];
                            await this.loadMissionContent(missions[0].id);
                        }
                    }
                }
            } catch (error) {
                console.error('Error loading initial content:', error);
                this.addNotification('error', `Failed to load content: ${error.message}`);
            } finally {
                this.loading = false;
            }
        },

        async updateSuiviContent() {
            try {
                const response = await fetch('/api/suivi');
                if (response.ok) {
                    const data = await response.json();
                    if (data.content !== undefined) {
                        this.content.suivi = data.content;
                    }
                }
            } catch (error) {
                console.error('Error updating suivi content:', error);
            }
        },

        async saveDemande() {
            try {
                // Vérification explicite de la mission
                if (!this.currentMission || !this.currentMission.id) {
                    console.error('No mission selected or invalid mission');
                    this.addNotification('error', 'Please select a mission first');
                    throw new Error('No mission selected');
                }

                if (!this.content.demande) {
                    this.addNotification('error', 'No demand content to save');
                    return;
                }

                // Log pour debug
                console.log('Saving demand for mission:', this.currentMission);

                const response = await fetch('/api/demande', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        content: this.content.demande,
                        missionId: this.currentMission.id,
                        missionName: this.currentMission.name // Ajout du nom de la mission
                    })
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    console.error('Server error:', errorData);
                    throw new Error(errorData.error || 'Failed to save demand');
                }

                const result = await response.json();
                if (result.success) {
                    this.demandeChanged = false;
                    this.addNotification('success', 'Demand saved successfully');
                } else {
                    throw new Error('Server indicated save failure');
                }
            } catch (error) {
                console.error('Error saving demand:', error);
                this.addNotification('error', `Failed to save demand: ${error.message}`);
                throw error;
            }
        },
        notificationIcon(type) {
            switch (type) {
                case 'success':
                    return 'mdi mdi-check-circle';
                case 'error':
                    return 'mdi mdi-alert-circle';
                case 'warning':
                    return 'mdi mdi-alert';
                default:
                    return 'mdi mdi-information';
            }
        },

        async startAgents() {
            try {
                this.loading = true;
                await fetch('/api/start', { method: 'POST' });
                this.running = true;
                this.startUpdateLoop();
                // Changer cette ligne pour activer l'onglet suivi au lieu de suivi-mission
                this.activeTab = 'suivi';
                this.addNotification('success', 'Agents started successfully');
                // Start logs update
                this.startLogsUpdate();
            } catch (error) {
                this.error = error.message;
                this.addNotification('error', `Failed to start agents: ${error.message}`);
            } finally {
                this.loading = false;
            }
        },

        startLogsUpdate() {
            if (!this.logsInterval) {
                this.logsInterval = setInterval(async () => {
                    try {
                        const response = await fetch('/api/logs');
                        const data = await response.json();
                        if (data.logs && Array.isArray(data.logs)) {
                            this.logs = data.logs;
                            // Auto-scroll to bottom
                            this.$nextTick(() => {
                                const logsContent = document.querySelector('.suivi-mission-content');
                                if (logsContent) {
                                    logsContent.scrollTop = logsContent.scrollHeight;
                                }
                            });
                        }
                    } catch (error) {
                        console.error('Failed to fetch logs:', error);
                    }
                }, 1000);
            }
        },

        addNotification(type, message) {
            console.log("Adding notification:", type, message);
            const id = Date.now();
            const notification = {
                id,
                type,
                message,
                class: `notification-${type}`
            };
            
            this.notifications.push(notification);
            console.log("Current notifications:", this.notifications);
            
            // Auto-remove after 5 seconds
            setTimeout(() => {
                this.notifications = this.notifications.filter(n => n.id !== id);
            }, 5000);
        },

        async stopAgents() {
            try {
                await fetch('/api/stop', { method: 'POST' });
                this.running = false;
                this.stopUpdateLoop();
                // Stop logs update
                if (this.logsInterval) {
                    clearInterval(this.logsInterval);
                    this.logsInterval = null;
                }
            } catch (error) {
                console.error('Failed to stop agents:', error);
                this.addLog('error', 'Failed to stop agents: ' + error.message);
            }
        },

        async resetFiles() {
            try {
                if (!this.currentMission) {
                    this.addNotification('error', 'Veuillez sélectionner une mission');
                    return;
                }

                if (confirm('Are you sure you want to reset all files to their initial state?')) {
                    const response = await fetch(`/api/missions/${this.currentMission.id}/reset`, {
                        method: 'POST'
                    });
                    
                    if (response.ok) {
                        this.addNotification('success', 'Files reset successfully');
                        await this.loadMissionContent(this.currentMission.id);
                    } else {
                        throw new Error('Failed to reset files');
                    }
                }
            } catch (error) {
                console.error('Failed to reset files:', error);
                this.addNotification('error', `Failed to reset files: ${error.message}`);
            }
        },

        startPolling() {
            setInterval(async () => {
                if (this.running) {
                    try {
                        const response = await fetch('/api/content');
                        const data = await response.json();
                        
                        this.previousContent = { ...this.content };
                        this.content = data;

                        // Check for changes and update UI
                        this.panels.forEach(panel => {
                            const hasChanged = this.previousContent[panel.id] !== this.content[panel.id];
                            panel.updating = hasChanged;
                            if (hasChanged) {
                                this.addLog('info', `${panel.name} content updated`);
                            }
                        });
                    } catch (error) {
                        console.error('Failed to poll content:', error);
                        this.addLog('error', 'Failed to update content: ' + error.message);
                    }
                }
            }, 1000); // Poll every second
        },

        async updateContent() {
            try {
                // Ne pas mettre à jour le contenu de la demande si une modification est en cours
                if (this.demandeChanged) {
                    console.debug('Skipping demande update due to pending changes');
                    return;
                }

                // Get content updates
                const contentResponse = await fetch('/api/content');
                const contentData = await contentResponse.json();
                
                // Get notifications
                const notificationsResponse = await fetch('/api/notifications');
                const notificationsData = await notificationsResponse.json();
                
                // Process notifications
                if (Array.isArray(notificationsData)) {
                    notificationsData.forEach(notification => {
                        this.addNotification(notification.type, notification.message);
                    });
                }
                
                // Mise à jour sélective du contenu
                this.previousContent = { ...this.content };
                Object.keys(contentData).forEach(key => {
                    if (key !== 'demande' || !this.demandeChanged) {
                        this.content[key] = contentData[key];
                    }
                });

                // Check for changes and update UI
                this.panels.forEach(panel => {
                    const hasChanged = this.previousContent[panel.id] !== this.content[panel.id];
                    panel.updating = hasChanged;
                    if (hasChanged) {
                        this.addLog('info', `${panel.name} content updated`);
                    }
                });
            } catch (error) {
                console.error('Failed to update content:', error);
                this.addLog('error', 'Failed to update content: ' + error.message);
            }
        },


        debouncedSaveDemande: debounce(async function() {
            try {
                await this.saveDemande();
            } catch (error) {
                // Error already handled in saveDemande
                console.debug('Debounced save failed:', error);
            }
        }, 1000),

        onDemandeInput() {
            this.demandeChanged = true;
            this.debouncedSaveDemande();
        },

        computeDiff(oldLines, newLines) {
            const diff = [];
            let i = 0, j = 0;
            
            while (i < oldLines.length || j < newLines.length) {
                if (i >= oldLines.length) {
                    diff.push({ added: true, value: newLines[j] });
                    j++;
                } else if (j >= newLines.length) {
                    diff.push({ removed: true, value: oldLines[i] });
                    i++;
                } else if (oldLines[i] !== newLines[j]) {
                    diff.push({ removed: true, value: oldLines[i] });
                    diff.push({ added: true, value: newLines[j] });
                    i++;
                    j++;
                } else {
                    diff.push({ value: oldLines[i] });
                    i++;
                    j++;
                }
            }
            
            return diff;
        },

        setActiveTab(tabId) {
            this.activeTab = tabId;
        },
        
        highlightContent(panelId) {
            const oldContent = this.previousContent[panelId] || '';
            const newContent = this.content[panelId] || '';
            
            if (oldContent === newContent) return newContent;

            const diff = this.computeDiff(
                oldContent.split('\n'),
                newContent.split('\n')
            );

            return diff.map(part => {
                if (part.added) {
                    return `<span class="highlight-add">${this.escapeHtml(part.value)}</span>`;
                }
                if (part.removed) {
                    return `<span class="highlight-remove">${this.escapeHtml(part.value)}</span>`;
                }
                return this.escapeHtml(part.value);
            }).join('\n');
        },

        escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        },

        async exportLogs() {
            try {
                const response = await fetch('/api/logs/export');
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
                
                a.href = url;
                a.download = `parallagon-logs-${timestamp}.txt`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
                this.addNotification('success', 'Logs exported successfully');
            } catch (error) {
                console.error('Failed to export logs:', error);
                this.addNotification('error', `Failed to export logs: ${error.message}`);
            }
        },

        async clearLogs() {
            try {
                const response = await fetch('/api/logs/clear', { method: 'POST' });
                if (!response.ok) {
                    throw new Error('Failed to clear logs');
                }
                this.logs = [];
                this.addNotification('success', 'Logs cleared successfully');
            } catch (error) {
                console.error('Failed to clear logs:', error);
                this.addNotification('error', `Failed to clear logs: ${error.message}`);
            }
        },

        async loadTestData() {
            try {
                if (!this.currentMission) {
                    this.addNotification('error', 'Veuillez sélectionner une mission');
                    return;
                }

                const response = await fetch(`/api/missions/${this.currentMission.id}/test-data`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                
                if (response.ok) {
                    this.addNotification('success', 'Données de test chargées');
                    await this.loadMissionContent(this.currentMission.id); // Recharger le contenu
                } else {
                    const error = await response.json();
                    throw new Error(error.error || 'Failed to load test data');
                }
            } catch (error) {
                console.error('Failed to load test data:', error);
                this.addNotification('error', `Failed to load test data: ${error.message}`);
            }
        },

        isAgentTab(tabId) {
            return ['specifications', 'management', 'production', 'evaluation', 'suivi', 'contexte'].includes(tabId);
        },

        isAgentRunning(tabId) {
            return this.runningAgents.has(tabId);
        },

        updateAgentsStatus(status) {
            // Mettre à jour runningAgents basé sur le statut
            this.runningAgents.clear();
            for (const [agentId, agentStatus] of Object.entries(status)) {
                if (agentStatus.running) {
                    this.runningAgents.add(agentId);
                }
            }
        },

        isAgentTab(tabId) {
            return ['specifications', 'management', 'production', 'evaluation', 'suivi'].includes(tabId);
        },

        isAgentRunning(tabId) {
            return this.runningAgents.has(tabId);
        },

        async toggleAgent(agentId) {
            try {
                // Convertir la première lettre en majuscule
                const formattedAgentId = agentId.charAt(0).toUpperCase() + agentId.slice(1);
                
                // Ne pas ajouter "Mission" au nom
                const agentName = formattedAgentId;
                
                console.log(`Toggling agent ${agentName}`); // Debug log
                
                const action = this.isAgentRunning(agentId) ? 'stop' : 'start';
                
                const response = await fetch(`/api/agent/${agentName}/${action}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    console.error('Server error:', errorData); // Debug log
                    throw new Error(`Failed to ${action} agent: ${errorData.error || 'Unknown error'}`);
                }

                // Mise à jour optimiste de l'état
                if (action === 'start') {
                    this.runningAgents.add(agentId);
                } else {
                    this.runningAgents.delete(agentId);
                }

                this.addNotification('success', `Agent ${agentId} ${action}ed successfully`);
                
            } catch (error) {
                console.error(`Error toggling agent ${agentId}:`, error);
                this.addNotification('error', `Error toggling agent ${agentId}: ${error.message}`);
                throw error;
            }
        },

        async refreshAgentsStatus() {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 5000);  // 5s timeout
                
                const response = await fetch('/api/agents/status', {
                    signal: controller.signal
                });
                
                clearTimeout(timeoutId);
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const status = await response.json();
                this.updateAgentsStatus(status);
                
            } catch (error) {
                if (error.name === 'AbortError') {
                    console.warn('Agents status request timed out');
                } else {
                    console.error('Failed to refresh agents status:', error);
                }
                // Don't update status on error
            }
        },

        addLog(level, message, operation = null, status = null) {
            const timestamp = new Date().toISOString();
            const logEntry = {
                id: `${this.logCounter}_${Date.now()}`,  // Unique ID combining counter and timestamp
                timestamp,
                level,
                message,
                operation,
                status
            };
            
            // Format message with operation and status if present
            if (operation && status) {
                logEntry.formattedMessage = `${operation}: ${status} - ${message}`;
            } else {
                logEntry.formattedMessage = message;
            }
            
            this.logs.push(logEntry);
            this.logCounter++;  // Increment counter after use

            // Keep only last 100 logs using slice
            if (this.logs.length > 100) {
                this.logs = this.logs.slice(-100);
            }

            // Auto-scroll logs
            this.$nextTick(() => {
                const logsContent = document.querySelector('.logs-content');
                if (logsContent) {
                    logsContent.scrollTop = logsContent.scrollHeight;
                }
            });
        },

        async updateLogs() {
            try {
                const response = await fetch('/api/logs');
                const data = await response.json();
                if (data.logs && Array.isArray(data.logs)) {
                    this.logs = data.logs;
                }
            } catch (error) {
                console.error('Failed to fetch logs:', error);
            }
        },

        async checkForChanges() {
            if (!this.running) {
                console.debug('App not running, skipping change check');
                return;
            }
            
            try {
                const response = await fetch('/api/changes');
                const changes = await response.json();
                
                changes.forEach(change => {
                    if (change.operation === 'flash_tab' && change.status) {
                        const tabId = this.tabIds[change.status];
                        if (tabId) {
                            const tab = document.querySelector(`.tab-item[data-tab="${tabId}"]`);
                            if (tab) {
                                tab.classList.remove('flash-tab');
                                void tab.offsetWidth; // Force reflow
                                tab.classList.add('flash-tab');
                                
                                setTimeout(() => {
                                    tab.classList.remove('flash-tab');
                                }, 1000);
                            }
                        }
                    }
                });
            } catch (error) {
                console.error('Error checking changes:', error);
            }
        },

        startUpdateLoop() {
            // Vérifier les notifications plus fréquemment
            this.notificationsInterval = setInterval(() => {
                this.checkNotifications();
            }, 500);  // Toutes les 500ms
            
            // Autres mises à jour moins fréquentes
            this.updateInterval = setInterval(() => {
                this.updateContent();
                this.updateLogs();
                this.checkForChanges();
            }, 1000);
        },

        async checkNotifications() {
            try {
                const response = await fetch('/api/notifications');
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const notifications = await response.json();
                
                if (Array.isArray(notifications) && notifications.length > 0) {
                    console.log('Received notifications:', notifications);
                    
                    notifications.forEach(notification => {
                        console.log('Processing notification:', notification);
                    
                        // Add visual notification
                        this.addNotification(notification.type, notification.message);
                    
                        // Handle tab flash if requested
                        if (notification.flash && notification.panel) {
                            const panelName = notification.panel.toLowerCase();
                            const tabFile = `${panelName}.md`;
                            console.log('Looking for tab:', tabFile, 'in', this.tabIds);
                        
                            const tabId = this.tabIds[tabFile];
                            if (tabId) {
                                console.log('Found tab ID:', tabId);
                                const tab = document.querySelector(`.tab-item[data-tab="${tabId}"]`);
                            
                                if (tab) {
                                    console.log('Flashing tab:', tabId);
                                    // Remove any existing flash
                                    tab.classList.remove('flash-tab');
                                    // Force reflow
                                    void tab.offsetWidth;
                                    // Add flash class
                                    tab.classList.add('flash-tab');
                                
                                    // Remove flash class after animation completes
                                    setTimeout(() => {
                                        tab.classList.remove('flash-tab');
                                    }, 1000);
                                
                                    // Also update content if available
                                    if (notification.content) {
                                        this.content[panelName] = notification.content;
                                    }
                                } else {
                                    console.log('Tab element not found for ID:', tabId);
                                }
                            } else {
                                console.log('No tab ID found for:', tabFile);
                            }
                        }
                    });
                }
            } catch (error) {
                console.error('Failed to check notifications:', error);
            }
        },

        stopUpdateLoop() {
            if (this.updateInterval) {
                clearInterval(this.updateInterval);
                this.updateInterval = null;
            }
            if (this.notificationsInterval) {
                clearInterval(this.notificationsInterval);
                this.notificationsInterval = null;
            }
        },

        formatMarkdown(content) {
            if (!content) return '';
            try {
                // First process with marked for markdown conversion
                const htmlContent = marked.parse(content, {
                    gfm: true,  // GitHub Flavored Markdown
                    breaks: true,  // Convert line breaks to <br>
                    sanitize: true // Sanitize HTML input
                });
                return htmlContent;
            } catch (error) {
                console.error('Error formatting markdown:', error);
                return content; // Return original content if parsing fails
            }
        }
    },

    
    async refreshAgentsStatus() {
        try {
            const response = await fetch('/api/agents/status');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const status = await response.json();
            this.updateAgentsStatus(status);
        } catch (error) {
            console.error('Failed to refresh agents status:', error);
            // Ne pas propager l'erreur, juste logger
        }
    },

    mounted() {
        // Add notifications container to body
        const notificationsContainer = document.createElement('div');
        notificationsContainer.className = 'notifications-container';
        document.body.appendChild(notificationsContainer);

        // Add suivi updates
        setInterval(() => {
            if (this.running) {
                this.updateSuiviEntries();
            }
        }, 1000);
        
        // Load missions first, then content
        this.loadMissions()
            .then(async () => {
                // Select first mission if available
                if (this.missions.length > 0) {
                    // Attendre que la sélection de mission soit terminée
                    await this.selectMission(this.missions[0]);
                    // Vérifier que la mission a bien été sélectionnée
                    if (!this.currentMission) {
                        throw new Error('Failed to select mission');
                    }
                } else {
                    this.addNotification('warning', 'No missions available. Please create a new mission.');
                }
            })
            .then(() => {
                // Ne démarrer le polling que si une mission est sélectionnée
                if (this.currentMission) {
                    this.startPolling();
                    // Start suivi content updates
                    this.suiviUpdateInterval = setInterval(() => {
                        this.updateSuiviContent();
                    }, 5000);
                    
                    // Refresh agents status every 5 seconds
                    setInterval(() => {
                        if (this.running) {
                            this.refreshAgentsStatus();
                        }
                    }, 5000);
                    
                    this.addLog('info', 'Application initialized with mission: ' + this.currentMission.name);
                }
            })
            .catch(error => {
                console.error('Error in mounted:', error);
                this.addNotification('error', 'Failed to initialize application');
            });
    },
    
    beforeUnmount() {
        this.stopUpdateLoop();
        if (this.suiviUpdateInterval) {
            clearInterval(this.suiviUpdateInterval);
        }
    }
};

Vue.createApp(ParallagonApp).mount('#app');
