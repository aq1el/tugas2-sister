import asyncio
import logging
from typing import Dict, Optional
from abc import ABC, abstractmethod

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseNode(ABC):
    """Base class for all distributed nodes"""
    
    def __init__(self, node_id: str, host: str = "localhost", port: int = 8001):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.is_running = False
        self.neighbors: Dict[str, tuple] = {}
        self.state = "FOLLOWER"
        
    async def start(self):
        """Start the node"""
        self.is_running = True
        logger.info(f"Node {self.node_id} started on {self.host}:{self.port}")
        await self.run()
        
    async def stop(self):
        """Stop the node"""
        self.is_running = False
        logger.info(f"Node {self.node_id} stopped")
        
    @abstractmethod
    async def run(self):
        """Main node loop - to be implemented by subclasses"""
        pass
    
    def add_neighbor(self, node_id: str, host: str, port: int):
        """Add a neighboring node"""
        self.neighbors[node_id] = (host, port)
        logger.info(f"Node {self.node_id} added neighbor {node_id}")
        
    async def send_message(self, target_node_id: str, message: Dict):
        """Send message to another node"""
        if target_node_id not in self.neighbors:
            logger.warning(f"Node {target_node_id} not in neighbors")
            return False
            
        # Simulate network delay
        await asyncio.sleep(0.01)
        logger.debug(f"Node {self.node_id} sent message to {target_node_id}: {message}")
        return True
    
    def get_info(self) -> Dict:
        """Get node information"""
        return {
            "node_id": self.node_id,
            "host": self.host,
            "port": self.port,
            "state": self.state,
            "is_running": self.is_running,
            "neighbors": list(self.neighbors.keys())
        }