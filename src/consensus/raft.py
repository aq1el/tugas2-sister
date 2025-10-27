import asyncio
import random
import logging
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class NodeState(Enum):
    """Raft node states"""
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


class LogEntry:
    """Represents a log entry in Raft"""
    
    def __init__(self, term: int, command: Any):
        self.term = term
        self.command = command


class RaftNode:
    """Simplified Raft Consensus Algorithm Implementation"""
    
    def __init__(self, node_id: str, cluster_nodes: List[str]):
        self.node_id = node_id
        self.cluster_nodes = cluster_nodes
        self.state = NodeState.FOLLOWER
        
        # Persistent state
        self.current_term = 0
        self.voted_for: Optional[str] = None
        self.log: List[LogEntry] = []
        
        # Volatile state
        self.commit_index = 0
        self.last_applied = 0
        
        # Leader state
        self.next_index: Dict[str, int] = {}
        self.match_index: Dict[str, int] = {}
        
        # Timers
        self.election_timeout = self._random_election_timeout()
        self.last_heartbeat = asyncio.get_event_loop().time()
        self.heartbeat_interval = 0.05  # 50ms
        
        # Statistics
        self.elections_started = 0
        self.votes_received = 0
        
    def _random_election_timeout(self) -> float:
        """Generate random election timeout"""
        return random.uniform(0.15, 0.30)  # 150-300ms
    
    async def start(self):
        """Start the Raft node"""
        logger.info(f"Raft node {self.node_id} started")
        
        # Start main loop
        asyncio.create_task(self._main_loop())
    
    async def _main_loop(self):
        """Main Raft consensus loop"""
        while True:
            if self.state == NodeState.FOLLOWER:
                await self._follower_loop()
            elif self.state == NodeState.CANDIDATE:
                await self._candidate_loop()
            elif self.state == NodeState.LEADER:
                await self._leader_loop()
            
            await asyncio.sleep(0.01)
    
    async def _follower_loop(self):
        """Follower state loop"""
        current_time = asyncio.get_event_loop().time()
        
        # Check for election timeout
        if current_time - self.last_heartbeat > self.election_timeout:
            logger.info(f"Node {self.node_id}: Election timeout, becoming candidate")
            await self._become_candidate()
    
    async def _candidate_loop(self):
        """Candidate state loop"""
        # Start election
        self.current_term += 1
        self.voted_for = self.node_id
        self.elections_started += 1
        self.votes_received = 1  # Vote for self
        
        logger.info(f"Node {self.node_id}: Starting election for term {self.current_term}")
        
        # Request votes from other nodes
        votes = await self._request_votes()
        
        # Check if won election (majority)
        if votes > len(self.cluster_nodes) / 2:
            logger.info(f"Node {self.node_id}: Won election with {votes} votes")
            await self._become_leader()
        else:
            # Election failed, reset timeout
            self.election_timeout = self._random_election_timeout()
            self.last_heartbeat = asyncio.get_event_loop().time()
            self.state = NodeState.FOLLOWER
    
    async def _leader_loop(self):
        """Leader state loop"""
        # Send heartbeats to followers
        await self._send_heartbeats()
        await asyncio.sleep(self.heartbeat_interval)
    
    async def _become_candidate(self):
        """Transition to candidate state"""
        self.state = NodeState.CANDIDATE
        self.election_timeout = self._random_election_timeout()
    
    async def _become_leader(self):
        """Transition to leader state"""
        self.state = NodeState.LEADER
        
        # Initialize leader state
        for node in self.cluster_nodes:
            if node != self.node_id:
                self.next_index[node] = len(self.log) + 1
                self.match_index[node] = 0
        
        logger.info(f"Node {self.node_id}: Became leader for term {self.current_term}")
    
    async def _request_votes(self) -> int:
        """Request votes from other nodes"""
        # In real implementation, this would send RequestVote RPCs
        # For simulation, assume some nodes vote for us
        votes = 1  # Self vote
        
        for node in self.cluster_nodes:
            if node != self.node_id:
                # Simulate vote response (simplified)
                if random.random() > 0.3:  # 70% chance of getting vote
                    votes += 1
        
        return votes
    
    async def _send_heartbeats(self):
        """Send heartbeat messages to all followers"""
        for node in self.cluster_nodes:
            if node != self.node_id:
                # Send AppendEntries RPC (heartbeat)
                logger.debug(f"Node {self.node_id}: Sending heartbeat to {node}")
    
    def receive_heartbeat(self, term: int, leader_id: str):
        """Receive heartbeat from leader"""
        if term >= self.current_term:
            self.current_term = term
            self.state = NodeState.FOLLOWER
            self.last_heartbeat = asyncio.get_event_loop().time()
            logger.debug(f"Node {self.node_id}: Received heartbeat from {leader_id}")
    
    async def append_entry(self, command: Any) -> bool:
        """Append entry to log (only leader can do this)"""
        if self.state != NodeState.LEADER:
            return False
        
        entry = LogEntry(self.current_term, command)
        self.log.append(entry)
        
        # Replicate to followers
        await self._replicate_log()
        
        return True
    
    async def _replicate_log(self):
        """Replicate log entries to followers"""
        # In real implementation, this would send AppendEntries RPCs
        logger.debug(f"Node {self.node_id}: Replicating log to followers")
    
    def is_leader(self) -> bool:
        """Check if this node is the leader"""
        return self.state == NodeState.LEADER
    
    def get_state(self) -> Dict:
        """Get current Raft state"""
        return {
            "node_id": self.node_id,
            "state": self.state.value,
            "current_term": self.current_term,
            "log_length": len(self.log),
            "commit_index": self.commit_index,
            "elections_started": self.elections_started,
            "is_leader": self.is_leader()
        }