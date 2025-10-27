import asyncio
import time
import logging
from typing import Dict, Set

logger = logging.getLogger(__name__)


class FailureDetector:
    """Heartbeat-based failure detector"""
    
    def __init__(self, node_id: str, timeout: float = 5.0, check_interval: float = 1.0):
        self.node_id = node_id
        self.timeout = timeout
        self.check_interval = check_interval
        
        # Track heartbeats
        self.last_heartbeat: Dict[str, float] = {}
        self.failed_nodes: Set[str] = set()
        self.monitored_nodes: Set[str] = set()
        
        self.is_running = False
    
    def add_node(self, node_id: str):
        """Add a node to monitor"""
        self.monitored_nodes.add(node_id)
        self.last_heartbeat[node_id] = time.time()
        logger.info(f"Failure detector: Monitoring node {node_id}")
    
    def remove_node(self, node_id: str):
        """Remove a node from monitoring"""
        self.monitored_nodes.discard(node_id)
        if node_id in self.last_heartbeat:
            del self.last_heartbeat[node_id]
        self.failed_nodes.discard(node_id)
    
    def receive_heartbeat(self, node_id: str):
        """Receive heartbeat from a node"""
        self.last_heartbeat[node_id] = time.time()
        
        # Mark as recovered if it was failed
        if node_id in self.failed_nodes:
            self.failed_nodes.remove(node_id)
            logger.info(f"Failure detector: Node {node_id} recovered")
    
    async def start(self):
        """Start the failure detector"""
        self.is_running = True
        logger.info(f"Failure detector started for node {self.node_id}")
        
        while self.is_running:
            await self._check_failures()
            await asyncio.sleep(self.check_interval)
    
    async def stop(self):
        """Stop the failure detector"""
        self.is_running = False
        logger.info(f"Failure detector stopped for node {self.node_id}")
    
    async def _check_failures(self):
        """Check for failed nodes"""
        current_time = time.time()
        
        for node_id in self.monitored_nodes:
            if node_id not in self.last_heartbeat:
                continue
            
            time_since_heartbeat = current_time - self.last_heartbeat[node_id]
            
            if time_since_heartbeat > self.timeout:
                if node_id not in self.failed_nodes:
                    self.failed_nodes.add(node_id)
                    logger.warning(f"Failure detector: Node {node_id} suspected as failed")
    
    def is_node_alive(self, node_id: str) -> bool:
        """Check if a node is alive"""
        return node_id not in self.failed_nodes
    
    def get_failed_nodes(self) -> Set[str]:
        """Get set of failed nodes"""
        return self.failed_nodes.copy()
    
    def get_alive_nodes(self) -> Set[str]:
        """Get set of alive nodes"""
        return self.monitored_nodes - self.failed_nodes