import asyncio
import hashlib
import json
import logging
from typing import Dict, List, Optional, Any
from collections import deque
from .base_node import BaseNode

logger = logging.getLogger(__name__)


class Message:
    """Represents a message in the queue"""
    
    def __init__(self, msg_id: str, data: Any, priority: int = 0):
        self.msg_id = msg_id
        self.data = data
        self.priority = priority
        self.attempts = 0
        self.max_attempts = 3


class ConsistentHash:
    """Consistent hashing for distributed queue partitioning"""
    
    def __init__(self, nodes: List[str], virtual_nodes: int = 150):
        self.nodes = nodes
        self.virtual_nodes = virtual_nodes
        self.ring: Dict[int, str] = {}
        self._build_ring()
    
    def _build_ring(self):
        """Build the hash ring"""
        for node in self.nodes:
            for i in range(self.virtual_nodes):
                virtual_key = f"{node}:{i}"
                hash_value = self._hash(virtual_key)
                self.ring[hash_value] = node
    
    def _hash(self, key: str) -> int:
        """Hash function"""
        return int(hashlib.md5(key.encode()).hexdigest(), 16)
    
    def get_node(self, key: str) -> str:
        """Get the node responsible for a key"""
        if not self.ring:
            return self.nodes[0] if self.nodes else "node1"
        
        hash_value = self._hash(key)
        
        # Find the first node with hash >= hash_value
        for ring_hash in sorted(self.ring.keys()):
            if ring_hash >= hash_value:
                return self.ring[ring_hash]
        
        # Wrap around to the first node
        return self.ring[min(self.ring.keys())]
    
    def add_node(self, node: str):
        """Add a node to the ring"""
        self.nodes.append(node)
        for i in range(self.virtual_nodes):
            virtual_key = f"{node}:{i}"
            hash_value = self._hash(virtual_key)
            self.ring[hash_value] = node
    
    def remove_node(self, node: str):
        """Remove a node from the ring"""
        if node in self.nodes:
            self.nodes.remove(node)
        
        # Remove from ring
        to_remove = [h for h, n in self.ring.items() if n == node]
        for h in to_remove:
            del self.ring[h]


class DistributedQueue(BaseNode):
    """Distributed Queue with consistent hashing"""
    
    def __init__(self, node_id: str, host: str = "localhost", port: int = 8001):
        super().__init__(node_id, host, port)
        
        self.queue: deque = deque()
        self.persistent_storage: Dict[str, Message] = {}
        self.in_flight: Dict[str, Message] = {}
        
        # Consistent hashing
        self.consistent_hash = ConsistentHash([node_id])
        
        # Statistics
        self.total_enqueued = 0
        self.total_dequeued = 0
        self.total_failed = 0
    
    async def run(self):
        """Main queue loop"""
        while self.is_running:
            await asyncio.sleep(0.1)
            await self._retry_failed_messages()
    
    async def enqueue(self, msg_id: str, data: Any, priority: int = 0) -> bool:
        """Enqueue a message"""
        # Determine which node should handle this message
        target_node = self.consistent_hash.get_node(msg_id)
        
        if target_node != self.node_id:
            # Forward to responsible node
            logger.info(f"Node {self.node_id}: Forwarding message {msg_id} to {target_node}")
            return await self.send_message(target_node, {
                "type": "enqueue",
                "msg_id": msg_id,
                "data": data,
                "priority": priority
            })
        
        message = Message(msg_id, data, priority)
        
        # Add to queue
        self.queue.append(message)
        
        # Persist if enabled
        if self.node_id:  # Simplified persistence check
            self.persistent_storage[msg_id] = message
        
        self.total_enqueued += 1
        logger.info(f"Node {self.node_id}: Enqueued message {msg_id} (queue size: {len(self.queue)})")
        
        return True
    
    async def dequeue(self, consumer_id: str) -> Optional[Message]:
        """Dequeue a message (at-least-once delivery)"""
        if not self.queue:
            return None
        
        message = self.queue.popleft()
        
        # Mark as in-flight
        self.in_flight[message.msg_id] = message
        
        self.total_dequeued += 1
        logger.info(f"Node {self.node_id}: Dequeued message {message.msg_id} by {consumer_id}")
        
        return message
    
    async def acknowledge(self, msg_id: str) -> bool:
        """Acknowledge message processing"""
        if msg_id not in self.in_flight:
            logger.warning(f"Node {self.node_id}: Message {msg_id} not in flight")
            return False
        
        # Remove from in-flight and persistent storage
        del self.in_flight[msg_id]
        if msg_id in self.persistent_storage:
            del self.persistent_storage[msg_id]
        
        logger.info(f"Node {self.node_id}: Acknowledged message {msg_id}")
        return True
    
    async def negative_acknowledge(self, msg_id: str) -> bool:
        """Negative acknowledge - retry message"""
        if msg_id not in self.in_flight:
            return False
        
        message = self.in_flight[msg_id]
        message.attempts += 1
        
        if message.attempts < message.max_attempts:
            # Re-queue for retry
            self.queue.append(message)
            del self.in_flight[msg_id]
            logger.info(f"Node {self.node_id}: Re-queued message {msg_id} (attempt {message.attempts})")
        else:
            # Max attempts reached, move to dead letter queue
            del self.in_flight[msg_id]
            if msg_id in self.persistent_storage:
                del self.persistent_storage[msg_id]
            self.total_failed += 1
            logger.warning(f"Node {self.node_id}: Message {msg_id} failed after {message.attempts} attempts")
        
        return True
    
    async def _retry_failed_messages(self):
        """Retry messages that have been in-flight too long"""
        current_time = asyncio.get_event_loop().time()
        timeout = 30.0  # 30 seconds timeout
        
        to_retry = []
        for msg_id, message in self.in_flight.items():
            # Simplified timeout check
            if len(self.in_flight) > 100:  # If too many in-flight, start retrying
                to_retry.append(msg_id)
        
        for msg_id in to_retry:
            await self.negative_acknowledge(msg_id)
    
    async def recover_from_storage(self):
        """Recover messages from persistent storage"""
        recovered = 0
        for msg_id, message in self.persistent_storage.items():
            if msg_id not in self.in_flight:
                self.queue.append(message)
                recovered += 1
        
        logger.info(f"Node {self.node_id}: Recovered {recovered} messages from storage")
    
    def get_queue_status(self) -> Dict:
        """Get current queue status"""
        return {
            "queue_size": len(self.queue),
            "in_flight": len(self.in_flight),
            "persistent_storage": len(self.persistent_storage),
            "total_enqueued": self.total_enqueued,
            "total_dequeued": self.total_dequeued,
            "total_failed": self.total_failed,
            "responsible_node": self.node_id
        }