import asyncio
import logging
from typing import Dict, Optional, Any
from enum import Enum
from collections import OrderedDict
from .base_node import BaseNode

logger = logging.getLogger(__name__)


class CacheState(Enum):
    """MESI Cache Coherence Protocol States"""
    MODIFIED = "M"  # Modified - dirty, exclusive
    EXCLUSIVE = "E"  # Exclusive - clean, exclusive
    SHARED = "S"    # Shared - clean, may be in other caches
    INVALID = "I"   # Invalid - not valid


class CacheEntry:
    """Represents a cache entry"""
    
    def __init__(self, key: str, value: Any, state: CacheState = CacheState.INVALID):
        self.key = key
        self.value = value
        self.state = state
        self.version = 0


class LRUCache:
    """LRU Cache implementation"""
    
    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self.cache: OrderedDict = OrderedDict()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key not in self.cache:
            return None
        
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        return self.cache[key]
    
    def put(self, key: str, value: Any):
        """Put value in cache"""
        if key in self.cache:
            self.cache.move_to_end(key)
        
        self.cache[key] = value
        
        # Evict if over capacity
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)
    
    def remove(self, key: str):
        """Remove key from cache"""
        if key in self.cache:
            del self.cache[key]
    
    def __len__(self):
        return len(self.cache)
    
    def __contains__(self, key):
        return key in self.cache


class DistributedCache(BaseNode):
    """Distributed Cache with MESI coherence protocol"""
    
    def __init__(self, node_id: str, host: str = "localhost", port: int = 8001, capacity: int = 1000):
        super().__init__(node_id, host, port)
        
        self.cache = LRUCache(capacity)
        self.cache_states: Dict[str, CacheState] = {}
        self.cache_entries: Dict[str, CacheEntry] = {}
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.invalidations = 0
        self.evictions = 0
    
    async def run(self):
        """Main cache loop"""
        while self.is_running:
            await asyncio.sleep(0.1)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache (read operation)"""
        # Check local cache
        if key in self.cache:
            entry = self.cache_entries.get(key)
            
            if entry and entry.state != CacheState.INVALID:
                self.hits += 1
                logger.info(f"Node {self.node_id}: Cache HIT for key {key}")
                return entry.value
        
        # Cache miss - fetch from other nodes or storage
        self.misses += 1
        logger.info(f"Node {self.node_id}: Cache MISS for key {key}")
        
        # Fetch from neighbors
        value = await self._fetch_from_neighbors(key)
        
        if value is not None:
            # Store in cache with SHARED state
            await self.put(key, value, broadcast=False)
            entry = self.cache_entries[key]
            entry.state = CacheState.SHARED
            self.cache_states[key] = CacheState.SHARED
        
        return value
    
    async def put(self, key: str, value: Any, broadcast: bool = True) -> bool:
        """Put value in cache (write operation)"""
        # Create or update cache entry
        if key in self.cache_entries:
            entry = self.cache_entries[key]
            entry.value = value
            entry.version += 1
        else:
            entry = CacheEntry(key, value)
            self.cache_entries[key] = entry
        
        # Set to MODIFIED state (dirty)
        entry.state = CacheState.MODIFIED
        self.cache_states[key] = CacheState.MODIFIED
        
        # Update LRU cache
        self.cache.put(key, value)
        
        logger.info(f"Node {self.node_id}: Put key {key} in cache (state: MODIFIED)")
        
        # Broadcast invalidation to other nodes
        if broadcast:
            await self._broadcast_invalidation(key)
        
        return True
    
    async def delete(self, key: str, broadcast: bool = True) -> bool:
        """Delete key from cache"""
        if key in self.cache:
            self.cache.remove(key)
        
        if key in self.cache_entries:
            del self.cache_entries[key]
        
        if key in self.cache_states:
            del self.cache_states[key]
        
        logger.info(f"Node {self.node_id}: Deleted key {key} from cache")
        
        # Broadcast invalidation
        if broadcast:
            await self._broadcast_invalidation(key)
        
        return True
    
    async def invalidate(self, key: str):
        """Invalidate a cache entry (called by other nodes)"""
        if key in self.cache_entries:
            entry = self.cache_entries[key]
            
            # If modified, need to write back first
            if entry.state == CacheState.MODIFIED:
                await self._writeback(key, entry.value)
            
            # Set to INVALID
            entry.state = CacheState.INVALID
            self.cache_states[key] = CacheState.INVALID
            
            self.invalidations += 1
            logger.info(f"Node {self.node_id}: Invalidated key {key}")
    
    async def _broadcast_invalidation(self, key: str):
        """Broadcast invalidation message to all neighbors"""
        message = {
            "type": "invalidate",
            "key": key,
            "sender": self.node_id
        }
        
        for neighbor_id in self.neighbors.keys():
            await self.send_message(neighbor_id, message)
        
        logger.debug(f"Node {self.node_id}: Broadcasted invalidation for key {key}")
    
    async def _fetch_from_neighbors(self, key: str) -> Optional[Any]:
        """Fetch value from neighbor nodes"""
        # In real implementation, this would query neighbors
        # For simulation, return None
        return None
    
    async def _writeback(self, key: str, value: Any):
        """Write back modified value to persistent storage"""
        # In real implementation, this would write to database
        logger.info(f"Node {self.node_id}: Wrote back key {key} to storage")
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0.0
        
        return {
            "cache_size": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "invalidations": self.invalidations,
            "evictions": self.evictions,
            "states": {
                key: state.value for key, state in self.cache_states.items()
            }
        }