import asyncio
import logging  
import signal
import sys
from aiohttp import web

from src.nodes.lock_manager import DistributedLockManager, LockType
from src.nodes.queue_node import DistributedQueue
from src.nodes.cache_node import DistributedCache
from src.consensus.raft import RaftNode
from src.communication.message_passing import MessagePassingSystem
from src.communication.failure_detector import FailureDetector
from src.utils.config import settings
from src.utils.metrics import metrics

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DistributedSystem:
    """Main distributed system orchestrator"""
    
    def __init__(self):
        self.node_id = settings.node_id
        self.port = settings.node_port
        
        # Initialize components
        self.lock_manager = DistributedLockManager(self.node_id, port=self.port)
        self.queue = DistributedQueue(self.node_id, port=self.port + 100)
        self.cache = DistributedCache(self.node_id, port=self.port + 200, capacity=settings.cache_size)
        
        # Initialize Raft consensus
        cluster_nodes = [node[0] for node in settings.get_cluster_nodes()]
        self.raft = RaftNode(self.node_id, cluster_nodes)
        
        # Initialize communication
        self.message_system = MessagePassingSystem(self.node_id, "0.0.0.0", self.port)
        self.failure_detector = FailureDetector(self.node_id)
        
        # Web server for API
        self.app = web.Application()
        self._setup_routes()
        
        self.is_running = False
    
    def _setup_routes(self):
        """Setup HTTP API routes"""
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/status', self.get_status)
        self.app.router.add_get('/metrics', self.get_metrics)
        
        # Lock endpoints
        self.app.router.add_post('/lock/acquire', self.acquire_lock)
        self.app.router.add_post('/lock/release', self.release_lock)
        self.app.router.add_get('/lock/status', self.lock_status)
        
        # Queue endpoints
        self.app.router.add_post('/queue/enqueue', self.enqueue_message)
        self.app.router.add_get('/queue/dequeue', self.dequeue_message)
        self.app.router.add_post('/queue/ack', self.ack_message)
        self.app.router.add_get('/queue/status', self.queue_status)
        
        # Cache endpoints
        self.app.router.add_get('/cache/get', self.cache_get)
        self.app.router.add_post('/cache/put', self.cache_put)
        self.app.router.add_delete('/cache/delete', self.cache_delete)
        self.app.router.add_get('/cache/stats', self.cache_stats)
    
    async def start(self):
        """Start the distributed system"""
        logger.info(f"Starting distributed system node: {self.node_id}")
        self.is_running = True
        
        # Start all components
        await self.message_system.start()
        await self.raft.start()
        
        # Start nodes in background
        asyncio.create_task(self.lock_manager.start())
        asyncio.create_task(self.queue.start())
        asyncio.create_task(self.cache.start())
        asyncio.create_task(self.failure_detector.start())
        
        # Setup neighbors
        for node_host, node_port in settings.get_cluster_nodes():
            if node_host != self.node_id:
                self.lock_manager.add_neighbor(node_host, node_host, node_port)
                self.queue.add_neighbor(node_host, node_host, node_port)
                self.cache.add_neighbor(node_host, node_host, node_port)
                self.failure_detector.add_node(node_host)
        
        # Start web server
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        
        logger.info(f"Distributed system node {self.node_id} started on port {self.port}")
        
        # Keep running
        while self.is_running:
            await asyncio.sleep(1)
    
    async def stop(self):
        """Stop the distributed system"""
        logger.info(f"Stopping distributed system node: {self.node_id}")
        self.is_running = False
        
        await self.lock_manager.stop()
        await self.queue.stop()
        await self.cache.stop()
        await self.message_system.stop()
        await self.failure_detector.stop()
    
    # API Handlers
    
    async def health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint"""
        return web.json_response({'status': 'healthy', 'node_id': self.node_id})
    
    async def get_status(self, request: web.Request) -> web.Response:
        """Get system status"""
        return web.json_response({
            'node_id': self.node_id,
            'port': self.port,
            'raft_state': self.raft.get_state(),
            'lock_manager': self.lock_manager.get_info(),
            'queue': self.queue.get_info(),
            'cache': self.cache.get_info(),
            'failed_nodes': list(self.failure_detector.get_failed_nodes())
        })
    
    async def get_metrics(self, request: web.Request) -> web.Response:
        """Get system metrics"""
        return web.Response(
            text=metrics.export_prometheus(),
            content_type='text/plain'
        )
    
    # Lock endpoints
    
    async def acquire_lock(self, request: web.Request) -> web.Response:
        """Acquire a distributed lock"""
        data = await request.json()
        resource_id = data.get('resource_id')
        lock_type = LockType.EXCLUSIVE if data.get('exclusive', True) else LockType.SHARED
        requester_id = data.get('requester_id', 'unknown')
        
        result = await self.lock_manager.acquire_lock(resource_id, lock_type, requester_id)
        
        return web.json_response({
            'success': result,
            'resource_id': resource_id,
            'lock_type': lock_type.value
        })
    
    async def release_lock(self, request: web.Request) -> web.Response:
        """Release a distributed lock"""
        data = await request.json()
        resource_id = data.get('resource_id')
        holder_id = data.get('holder_id', 'unknown')
        
        result = await self.lock_manager.release_lock(resource_id, holder_id)
        
        return web.json_response({
            'success': result,
            'resource_id': resource_id
        })
    
    async def lock_status(self, request: web.Request) -> web.Response:
        """Get lock status"""
        return web.json_response(self.lock_manager.get_lock_status())
    
    # Queue endpoints
    
    async def enqueue_message(self, request: web.Request) -> web.Response:
        """Enqueue a message"""
        data = await request.json()
        msg_id = data.get('msg_id')
        msg_data = data.get('data')
        priority = data.get('priority', 0)
        
        result = await self.queue.enqueue(msg_id, msg_data, priority)
        
        return web.json_response({
            'success': result,
            'msg_id': msg_id
        })
    
    async def dequeue_message(self, request: web.Request) -> web.Response:
        """Dequeue a message"""
        consumer_id = request.query.get('consumer_id', 'unknown')
        
        message = await self.queue.dequeue(consumer_id)
        
        if message:
            return web.json_response({
                'success': True,
                'message': {
                    'msg_id': message.msg_id,
                    'data': message.data,
                    'priority': message.priority
                }
            })
        else:
            return web.json_response({
                'success': False,
                'message': 'Queue is empty'
            })
    
    async def ack_message(self, request: web.Request) -> web.Response:
        """Acknowledge message processing"""
        data = await request.json()
        msg_id = data.get('msg_id')
        
        result = await self.queue.acknowledge(msg_id)
        
        return web.json_response({
            'success': result,
            'msg_id': msg_id
        })
    
    async def queue_status(self, request: web.Request) -> web.Response:
        """Get queue status"""
        return web.json_response(self.queue.get_queue_status())
    
    # Cache endpoints
    
    async def cache_get(self, request: web.Request) -> web.Response:
        """Get value from cache"""
        key = request.query.get('key')
        
        value = await self.cache.get(key)
        
        if value is not None:
            return web.json_response({
                'success': True,
                'key': key,
                'value': value
            })
        else:
            return web.json_response({
                'success': False,
                'message': 'Key not found'
            }, status=404)
    
    async def cache_put(self, request: web.Request) -> web.Response:
        """Put value in cache"""
        data = await request.json()
        key = data.get('key')
        value = data.get('value')
        
        result = await self.cache.put(key, value)
        
        return web.json_response({
            'success': result,
            'key': key
        })
    
    async def cache_delete(self, request: web.Request) -> web.Response:
        """Delete key from cache"""
        key = request.query.get('key')
        
        result = await self.cache.delete(key)
        
        return web.json_response({
            'success': result,
            'key': key
        })
    
    async def cache_stats(self, request: web.Request) -> web.Response:
        """Get cache statistics"""
        return web.json_response(self.cache.get_cache_stats())


async def main():
    """Main entry point"""
    system = DistributedSystem()
    
    # Setup signal handlers
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        asyncio.create_task(system.stop())
    
# Setup signal handlers (Windows compatible)
if sys.platform != 'win32':
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)
else:
    # Windows: use signal.signal instead
    import signal as sig_module
    sig_module.signal(sig_module.SIGTERM, lambda s, f: signal_handler())
    sig_module.signal(sig_module.SIGINT, lambda s, f: signal_handler())

if __name__ == '__main__':
    asyncio.run(main())