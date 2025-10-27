import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Node Configuration
    node_id: str = os.getenv("NODE_ID", "node1")
    node_port: int = int(os.getenv("NODE_PORT", "8001"))
    cluster_nodes: str = os.getenv("CLUSTER_NODES", "node1:8001,node2:8002,node3:8003")
    
    # Redis Configuration
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    
    # Raft Configuration
    election_timeout_min: int = int(os.getenv("ELECTION_TIMEOUT_MIN", "150"))
    election_timeout_max: int = int(os.getenv("ELECTION_TIMEOUT_MAX", "300"))
    heartbeat_interval: int = int(os.getenv("HEARTBEAT_INTERVAL", "50"))
    
    # Cache Configuration
    cache_size: int = int(os.getenv("CACHE_SIZE", "1000"))
    cache_policy: str = os.getenv("CACHE_POLICY", "LRU")
    
    # Queue Configuration
    queue_persistence: bool = os.getenv("QUEUE_PERSISTENCE", "true").lower() == "true"
    replication_factor: int = int(os.getenv("REPLICATION_FACTOR", "2"))
    
    def get_cluster_nodes(self) -> List[tuple]:
        """Parse cluster nodes from environment"""
        nodes = []
        for node in self.cluster_nodes.split(","):
            if ":" in node:
                host, port = node.strip().split(":")
                nodes.append((host, int(port)))
        return nodes
    
    class Config:
        env_file = ".env"


settings = Settings()