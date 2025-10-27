import asyncio
import time
import aiohttp
from typing import List, Dict


class LoadTester:
    """Load testing for distributed system"""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.results: List[float] = []
    
    async def test_lock_throughput(self, num_requests: int = 1000):
        """Test lock acquire/release throughput"""
        print(f"\n=== Testing Lock Throughput ({num_requests} requests) ===")
        
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            
            tasks = []
            for i in range(num_requests):
                tasks.append(self._lock_operation(session, f"resource_{i % 100}"))
            
            await asyncio.gather(*tasks)
            
            duration = time.time() - start_time
            throughput = num_requests / duration
            
            print(f"Duration: {duration:.2f}s")
            print(f"Throughput: {throughput:.2f} ops/sec")
            
            return throughput
    
    async def _lock_operation(self, session: aiohttp.ClientSession, resource_id: str):
        """Perform lock acquire and release"""
        request_start = time.time()
        
        try:
            # Acquire lock
            async with session.post(f"{self.base_url}/lock/acquire", json={
                "resource_id": resource_id,
                "requester_id": "test_client",
                "exclusive": True
            }) as resp:
                await resp.json()
            
            # Simulate some work
            await asyncio.sleep(0.001)
            
            # Release lock
            async with session.post(f"{self.base_url}/lock/release", json={
                "resource_id": resource_id,
                "holder_id": "test_client"
            }) as resp:
                await resp.json()
            
            duration = time.time() - request_start
            self.results.append(duration)
            
        except Exception as e:
            print(f"Error in lock operation: {e}")
    
    async def test_queue_throughput(self, num_messages: int = 1000):
        """Test queue enqueue/dequeue throughput"""
        print(f"\n=== Testing Queue Throughput ({num_messages} messages) ===")
        
        async with aiohttp.ClientSession() as session:
            # Enqueue
            start_time = time.time()
            tasks = []
            for i in range(num_messages):
                tasks.append(self._enqueue_message(session, f"msg_{i}", {"data": f"test_{i}"}))
            
            await asyncio.gather(*tasks)
            enqueue_duration = time.time() - start_time
            
            # Dequeue
            start_time = time.time()
            tasks = []
            for i in range(num_messages):
                tasks.append(self._dequeue_message(session))
            
            await asyncio.gather(*tasks)
            dequeue_duration = time.time() - start_time
            
            print(f"Enqueue Duration: {enqueue_duration:.2f}s")
            print(f"Enqueue Throughput: {num_messages/enqueue_duration:.2f} msgs/sec")
            print(f"Dequeue Duration: {dequeue_duration:.2f}s")
            print(f"Dequeue Throughput: {num_messages/dequeue_duration:.2f} msgs/sec")
            
            return num_messages/enqueue_duration, num_messages/dequeue_duration
    
    async def _enqueue_message(self, session: aiohttp.ClientSession, msg_id: str, data: Dict):
        """Enqueue a message"""
        try:
            async with session.post(f"{self.base_url}/queue/enqueue", json={
                "msg_id": msg_id,
                "data": data,
                "priority": 0
            }) as resp:
                await resp.json()
        except Exception as e:
            print(f"Error enqueuing: {e}")
    
    async def _dequeue_message(self, session: aiohttp.ClientSession):
        """Dequeue a message"""
        try:
            async with session.get(f"{self.base_url}/queue/dequeue?consumer_id=test") as resp:
                result = await resp.json()
                if result.get('success'):
                    msg_id = result['message']['msg_id']
                    # Acknowledge
                    async with session.post(f"{self.base_url}/queue/ack", json={"msg_id": msg_id}) as ack_resp:
                        await ack_resp.json()
        except Exception as e:
            print(f"Error dequeuing: {e}")
    
    async def test_cache_throughput(self, num_operations: int = 1000):
        """Test cache get/put throughput"""
        print(f"\n=== Testing Cache Throughput ({num_operations} operations) ===")
        
        async with aiohttp.ClientSession() as session:
            # Put operations
            start_time = time.time()
            tasks = []
            for i in range(num_operations):
                tasks.append(self._cache_put(session, f"key_{i % 100}", f"value_{i}"))
            
            await asyncio.gather(*tasks)
            put_duration = time.time() - start_time
            
            # Get operations
            start_time = time.time()
            tasks = []
            for i in range(num_operations):
                tasks.append(self._cache_get(session, f"key_{i % 100}"))
            
            await asyncio.gather(*tasks)
            get_duration = time.time() - start_time
            
            print(f"Put Duration: {put_duration:.2f}s")
            print(f"Put Throughput: {num_operations/put_duration:.2f} ops/sec")
            print(f"Get Duration: {get_duration:.2f}s")
            print(f"Get Throughput: {num_operations/get_duration:.2f} ops/sec")
            
            return num_operations/put_duration, num_operations/get_duration
    
    async def _cache_put(self, session: aiohttp.ClientSession, key: str, value: str):
        """Put value in cache"""
        try:
            async with session.post(f"{self.base_url}/cache/put", json={
                "key": key,
                "value": value
            }) as resp:
                await resp.json()
        except Exception as e:
            print(f"Error in cache put: {e}")
    
    async def _cache_get(self, session: aiohttp.ClientSession, key: str):
        """Get value from cache"""
        try:
            async with session.get(f"{self.base_url}/cache/get?key={key}") as resp:
                await resp.json()
        except Exception as e:
            pass  # Expected for cache misses
    
    def print_latency_stats(self):
        """Print latency statistics"""
        if not self.results:
            return
        
        sorted_results = sorted(self.results)
        n = len(sorted_results)
        
        print(f"\n=== Latency Statistics ===")
        print(f"Min: {min(sorted_results)*1000:.2f}ms")
        print(f"Max: {max(sorted_results)*1000:.2f}ms")
        print(f"Mean: {sum(sorted_results)/n*1000:.2f}ms")
        print(f"P50: {sorted_results[n//2]*1000:.2f}ms")
        print(f"P95: {sorted_results[int(n*0.95)]*1000:.2f}ms")
        print(f"P99: {sorted_results[int(n*0.99)]*1000:.2f}ms")


async def main():
    """Run all load tests"""
    tester = LoadTester()
    
    # Wait for system to be ready
    print("Waiting for system to be ready...")
    await asyncio.sleep(2)
    
    # Run tests
    await tester.test_lock_throughput(1000)
    await tester.test_queue_throughput(1000)
    await tester.test_cache_throughput(1000)
    
    tester.print_latency_stats()


if __name__ == '__main__':
    asyncio.run(main())