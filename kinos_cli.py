import sys
import threading
import queue
import time
from typing import List, Dict
import os
import json
from datetime import datetime
from utils.logger import Logger
from services.agent_service import AgentService

def load_team_config(team_name: str) -> List[str]:
    """Load agent names from team config"""
    try:
        config_path = os.path.join("teams", team_name, "config.json")
        with open(config_path, 'r') as f:
            config = json.load(f)
            return [agent['name'] if isinstance(agent, dict) else agent 
                   for agent in config.get('agents', [])]
    except Exception as e:
        print(f"Error loading team config: {e}")
        return []

class AgentRunner(threading.Thread):
    """Thread class for running an agent and capturing output"""
    def __init__(self, agent_service: AgentService, team_agents: List[str], 
                 output_queue: queue.Queue, logger: Logger):
        super().__init__(daemon=True)
        self.agent_service = agent_service
        self.team_agents = team_agents
        self.output_queue = output_queue
        self.logger = logger
        self.running = True

    def run(self):
        while self.running:
            try:
                # Capture start time
                start_time = datetime.now()
                
                # Run agent and capture output
                self.agent_service.run_random_agent(self.team_agents)
                
                # Calculate duration
                duration = (datetime.now() - start_time).total_seconds()
                
                # Put completion message in queue
                self.output_queue.put({
                    'thread_id': threading.get_ident(),
                    'status': 'completed',
                    'duration': duration,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                self.output_queue.put({
                    'thread_id': threading.get_ident(),
                    'status': 'error',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
                time.sleep(5)  # Brief pause on error

def run_team_loop(team_name: str):
    """Main team execution loop"""
    logger = Logger()
    agent_service = AgentService(None)
    
    # Load team configuration
    agents = load_team_config(team_name)
    if not agents:
        logger.log(f"No agents found for team: {team_name}", 'error')
        return
        
    logger.log(f"Starting team {team_name} with agents: {', '.join(agents)}")
    
    # Create output queue and active threads dict
    output_queue = queue.Queue()
    active_threads: Dict[int, AgentRunner] = {}
    
    try:
        while True:  # Main loop
            # Start new threads until we have 3
            while len(active_threads) < 3:
                runner = AgentRunner(agent_service, agents, output_queue, logger)
                runner.start()
                active_threads[runner.ident] = runner
                logger.log(f"Started new agent runner (total: {len(active_threads)})")

            try:
                # Check queue for messages with timeout
                try:
                    msg = output_queue.get(timeout=0.1)
                    thread_id = msg['thread_id']
                    
                    # Log message based on status
                    if msg['status'] == 'completed':
                        logger.log(
                            f"Agent completed (duration: {msg['duration']:.1f}s)", 
                            'success'
                        )
                    elif msg['status'] == 'error':
                        logger.log(
                            f"Agent error: {msg['error']}", 
                            'error'
                        )
                    
                    # Remove completed/failed thread and start new one
                    if thread_id in active_threads:
                        active_threads[thread_id].running = False
                        del active_threads[thread_id]
                        
                except queue.Empty:
                    pass  # No messages
                    
            except KeyboardInterrupt:
                raise  # Re-raise to outer try
                
            except Exception as e:
                logger.log(f"Error processing agent output: {str(e)}", 'error')
                
            # Brief sleep to prevent CPU spinning
            time.sleep(0.1)
                
    except KeyboardInterrupt:
        logger.log("Stopping team execution...")
        
        # Stop all threads
        for runner in active_threads.values():
            runner.running = False
            
        # Wait for threads to finish
        for runner in active_threads.values():
            runner.join(timeout=1.0)
            
def main():
    """CLI entry point"""
    if len(sys.argv) != 2:
        print("Usage: kin <team_name>")
        return
        
    team_name = sys.argv[1]
    run_team_loop(team_name)

if __name__ == "__main__":
    main()
