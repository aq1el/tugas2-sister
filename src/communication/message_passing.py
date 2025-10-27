import asyncio
import json
import logging
from typing import Dict, Any, Callable, Optional
from aiohttp import web

logger = logging.getLogger(__name__)


class MessagePassingSystem:
    """Message passing system for distributed nodes"""
    
    def __init__(self, node_id: str, host: str = "localhost", port: int = 8001):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.handlers: Dict[str, Callable] = {}
        self.app = web.Application()
        self.runner: Optional[web.AppRunner] = None
        
    def register_handler(self, message_type: str, handler: Callable):
        """Register a message handler"""
        self.handlers[message_type] = handler
        logger.info(f"Node {self.node_id}: Registered handler for {message_type}")
    
    async def start(self):
        """Start the message passing server"""
        self.app.router.add_post('/message', self._handle_message)
        self.app.router.add_get('/health', self._health_check)
        
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        site = web.TCPSite(self.runner, self.host, self.port)
        await site.start()
        
        logger.info(f"Node {self.node_id}: Message passing server started on {self.host}:{self.port}")
    
    async def stop(self):
        """Stop the message passing server"""
        if self.runner:
            await self.runner.cleanup()
        logger.info(f"Node {self.node_id}: Message passing server stopped")
    
    async def _handle_message(self, request: web.Request) -> web.Response:
        """Handle incoming message"""
        try:
            data = await request.json()
            message_type = data.get('type')
            
            if message_type in self.handlers:
                handler = self.handlers[message_type]
                result = await handler(data)
                
                return web.json_response({
                    'status': 'success',
                    'result': result
                })
            else:
                return web.json_response({
                    'status': 'error',
                    'message': f'Unknown message type: {message_type}'
                }, status=400)
                
        except Exception as e:
            logger.error(f"Node {self.node_id}: Error handling message: {e}")
            return web.json_response({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    async def _health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint"""
        return web.json_response({
            'status': 'healthy',
            'node_id': self.node_id
        })
    
    async def send_message(self, target_host: str, target_port: int, message: Dict[str, Any]) -> Optional[Dict]:
        """Send message to another node"""
        import aiohttp
        
        url = f"http://{target_host}:{target_port}/message"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=message, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result
                    else:
                        logger.warning(f"Node {self.node_id}: Failed to send message to {target_host}:{target_port}")
                        return None
        except Exception as e:
            logger.error(f"Node {self.node_id}: Error sending message: {e}")
            return None