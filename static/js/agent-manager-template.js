export default `
    <div class="agent-manager">
        <div v-if="error" class="error-message">{{ error }}</div>
        <div v-if="loading" class="loading">Loading...</div>
        
        <div v-if="teams && teams.length" class="teams-container">
            <div v-for="team in teams" :key="team.id" class="team-section">
                <h3>{{ team.name || 'Unnamed Team' }}</h3>
                <div v-if="getTeamMetrics(team.id)" class="team-metrics">
                    <div>Total Agents: {{ getTeamMetrics(team.id).totalAgents || 0 }}</div>
                    <div>Active Agents: {{ getTeamMetrics(team.id).activeAgents || 0 }}</div>
                    <div>Health: {{ getTeamMetrics(team.id).health ? (getTeamMetrics(team.id).health * 100).toFixed(1) + '%' : 'N/A' }}</div>
                </div>
                <div v-if="team.agents && team.agents.length" class="agents-list">
                    <div v-for="agent in team.agents" :key="agent.name" class="agent-item">
                        {{ agent.name || 'Unnamed Agent' }}
                    </div>
                </div>
                <div v-else class="no-agents-message">
                    No agents in this team.
                </div>
            </div>
        </div>
        <div v-else class="no-teams-message">
            No teams available for this mission.
        </div>
    </div>
`;