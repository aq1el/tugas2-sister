import asyncio
import time
import logging
from typing import Dict, Set, Optional
from enum import Enum
from .base_node import BaseNode

logger = logging.getLogger(__name__)


class LockType(Enum):
    """Types of distributed locks"""
    SHARED = "shared"
    EXCLUSIVE = "exclusive"


class LockRequest:
    """Represents a lock request"""
    
    def __init__(self, resource_id: str, lock_type: LockType, requester_id: str):
        self.resource_id = resource_id
        self.lock_type = lock_type
        self.requester_id = requester_id
        self.timestamp = time.time()
        self.granted = False


class DistributedLockManager(BaseNode):
    """Distributed Lock Manager using simplified Raft consensus"""
    
    def __init__(self, node_id: str, host: str = "localhost", port: int = 8001):
        super().__init__(node_id, host, port)
        
        # Lock state
        self.locks: Dict[str, Set[str]] = {}  # resource_id -> set of holder_ids
        self.lock_types: Dict[str, LockType] = {}  # resource_id -> lock_type
        self.pending_requests: list = []
        
        # Raft state
        self.current_term = 0
        self.voted_for: Optional[str] = None
        self.is_leader = False
        
        # Deadlock detection
        self.wait_for_graph: Dict[str, Set[str]] = {}  # requester -> set of holders
        
    async def run(self):
        """Main lock manager loop"""
        while self.is_running:
            await asyncio.sleep(0.1)
            
            # Process pending requests if leader
            if self.is_leader:
                await self._process_pending_requests()
                await self._detect_deadlocks()
    
    async def acquire_lock(self, resource_id: str, lock_type: LockType, requester_id: str) -> bool:
        """Acquire a lock on a resource"""
        logger.info(f"Node {self.node_id}: Lock request for {resource_id} by {requester_id} ({lock_type.value})")
        
        # Check if lock can be granted immediately
        if self._can_grant_lock(resource_id, lock_type, requester_id):
            self._grant_lock(resource_id, lock_type, requester_id)
            logger.info(f"Node {self.node_id}: Lock granted for {resource_id} to {requester_id}")
            return True
        
        # Add to pending requests
        request = LockRequest(resource_id, lock_type, requester_id)
        self.pending_requests.append(request)
        
        # Update wait-for graph for deadlock detection
        if resource_id in self.locks:
            self.wait_for_graph[requester_id] = self.locks[resource_id].copy()
        
        logger.info(f"Node {self.node_id}: Lock request queued for {resource_id} by {requester_id}")
        return False
    
    async def release_lock(self, resource_id: str, holder_id: str) -> bool:
        """Release a lock on a resource"""
        if resource_id not in self.locks or holder_id not in self.locks[resource_id]:
            logger.warning(f"Node {self.node_id}: No lock held on {resource_id} by {holder_id}")
            return False
        
        self.locks[resource_id].remove(holder_id)
        
        # Clean up if no more holders
        if not self.locks[resource_id]:
            del self.locks[resource_id]
            if resource_id in self.lock_types:
                del self.lock_types[resource_id]
        
        # Remove from wait-for graph
        if holder_id in self.wait_for_graph:
            del self.wait_for_graph[holder_id]
        
        logger.info(f"Node {self.node_id}: Lock released for {resource_id} by {holder_id}")
        
        # Try to grant pending requests
        await self._process_pending_requests()
        
        return True
    
    def _can_grant_lock(self, resource_id: str, lock_type: LockType, requester_id: str) -> bool:
        """Check if a lock can be granted"""
        # No existing locks
        if resource_id not in self.locks:
            return True
        
        # Shared lock request and only shared locks exist
        if lock_type == LockType.SHARED and self.lock_types.get(resource_id) == LockType.SHARED:
            return True
        
        # Already holding the lock
        if requester_id in self.locks[resource_id]:
            return True
        
        return False
    
    def _grant_lock(self, resource_id: str, lock_type: LockType, holder_id: str):
        """Grant a lock to a requester"""
        if resource_id not in self.locks:
            self.locks[resource_id] = set()
        
        self.locks[resource_id].add(holder_id)
        self.lock_types[resource_id] = lock_type
    
    async def _process_pending_requests(self):
        """Process pending lock requests"""
        granted = []
        
        for request in self.pending_requests:
            if self._can_grant_lock(request.resource_id, request.lock_type, request.requester_id):
                self._grant_lock(request.resource_id, request.lock_type, request.requester_id)
                granted.append(request)
                logger.info(f"Node {self.node_id}: Pending lock granted for {request.resource_id} to {request.requester_id}")
        
        # Remove granted requests
        for request in granted:
            self.pending_requests.remove(request)
            
            # Remove from wait-for graph
            if request.requester_id in self.wait_for_graph:
                del self.wait_for_graph[request.requester_id]
    
    async def _detect_deadlocks(self):
        """Detect deadlocks using cycle detection in wait-for graph"""
        visited = set()
        rec_stack = set()
        
        def has_cycle(node: str) -> bool:
            """DFS to detect cycle"""
            visited.add(node)
            rec_stack.add(node)
            
            if node in self.wait_for_graph:
                for neighbor in self.wait_for_graph[node]:
                    if neighbor not in visited:
                        if has_cycle(neighbor):
                            return True
                    elif neighbor in rec_stack:
                        return True
            
            rec_stack.remove(node)
            return False
        
        # Check all nodes in wait-for graph
        for node in list(self.wait_for_graph.keys()):
            if node not in visited:
                if has_cycle(node):
                    logger.warning(f"Node {self.node_id}: Deadlock detected involving {node}")
                    await self._resolve_deadlock(node)
    
    async def _resolve_deadlock(self, node_id: str):
        """Resolve deadlock by aborting youngest transaction"""
        # Find youngest request (highest timestamp)
        youngest_request = None
        youngest_time = 0
        
        for request in self.pending_requests:
            if request.requester_id == node_id and request.timestamp > youngest_time:
                youngest_request = request
                youngest_time = request.timestamp
        
        if youngest_request:
            self.pending_requests.remove(youngest_request)
            if node_id in self.wait_for_graph:
                del self.wait_for_graph[node_id]
            logger.info(f"Node {self.node_id}: Aborted request from {node_id} to resolve deadlock")
    
    def get_lock_status(self) -> Dict:
        """Get current lock status"""
        return {
            "active_locks": len(self.locks),
            "pending_requests": len(self.pending_requests),
            "locks": {
                resource_id: {
                    "holders": list(holders),
                    "type": self.lock_types.get(resource_id).value if resource_id in self.lock_types else None
                }
                for resource_id, holders in self.locks.items()
            }
        }