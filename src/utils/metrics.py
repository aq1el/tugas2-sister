import time
import asyncio
from typing import Dict, List
from collections import defaultdict, deque
from datetime import datetime
from prometheus_client import Counter, Histogram, Gauge, generate_latest


class MetricsCollector:
    """Collect and track system metrics"""
    
    def __init__(self):
        self.request_count = Counter('requests_total', 'Total requests')
        self.request_latency = Histogram('request_latency_seconds', 'Request latency')
        self.active_locks = Gauge('active_locks', 'Number of active locks')
        self.queue_size = Gauge('queue_size', 'Current queue size')
        self.cache_hits = Counter('cache_hits_total', 'Total cache hits')
        self.cache_misses = Counter('cache_misses_total', 'Total cache misses')
        
        # Custom metrics storage
        self.metrics_data = defaultdict(list)
        self.latencies = deque(maxlen=1000)
        self.throughput_samples = deque(maxlen=100)
        self.start_time = time.time()
        
    def record_request(self, duration: float):
        """Record a request with its duration"""
        self.request_count.inc()
        self.request_latency.observe(duration)
        self.latencies.append(duration)
        
    def record_cache_hit(self):
        """Record a cache hit"""
        self.cache_hits.inc()
        
    def record_cache_miss(self):
        """Record a cache miss"""
        self.cache_misses.inc()
        
    def set_active_locks(self, count: int):
        """Set current number of active locks"""
        self.active_locks.set(count)
        
    def set_queue_size(self, size: int):
        """Set current queue size"""
        self.queue_size.set(size)
        
    def get_stats(self) -> Dict:
        """Get current statistics"""
        uptime = time.time() - self.start_time
        
        avg_latency = sum(self.latencies) / len(self.latencies) if self.latencies else 0
        p95_latency = sorted(self.latencies)[int(len(self.latencies) * 0.95)] if self.latencies else 0
        p99_latency = sorted(self.latencies)[int(len(self.latencies) * 0.99)] if self.latencies else 0
        
        return {
            "uptime_seconds": uptime,
            "total_requests": self.request_count._value.get(),
            "avg_latency_ms": avg_latency * 1000,
            "p95_latency_ms": p95_latency * 1000,
            "p99_latency_ms": p99_latency * 1000,
            "cache_hit_rate": self._calculate_cache_hit_rate(),
            "active_locks": self.active_locks._value.get(),
            "queue_size": self.queue_size._value.get(),
        }
    
    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        hits = self.cache_hits._value.get()
        misses = self.cache_misses._value.get()
        total = hits + misses
        return (hits / total * 100) if total > 0 else 0.0
    
    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format"""
        return generate_latest().decode('utf-8')


# Global metrics instance
metrics = MetricsCollector()