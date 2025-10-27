#!/usr/bin/env python3
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.performance.load_test import LoadTester


async def run_all_benchmarks():
    """Run all performance benchmarks"""
    print("=" * 60)
    print("DISTRIBUTED SYNCHRONIZATION SYSTEM - PERFORMANCE BENCHMARKS")
    print("=" * 60)
    
    tester = LoadTester()
    
    # Wait for system startup
    print("\nWaiting for system to be ready...")
    await asyncio.sleep(3)
    
    # Run benchmarks with different loads
    loads = [100, 500, 1000, 5000]
    
    results = {
        'lock': [],
        'queue': [],
        'cache': []
    }
    
    for load in loads:
        print(f"\n{'='*60}")
        print(f"TESTING WITH LOAD: {load} operations")
        print(f"{'='*60}")
        
        # Lock benchmark
        lock_throughput = await tester.test_lock_throughput(load)
        results['lock'].append((load, lock_throughput))
        
        # Queue benchmark
        enqueue_tp, dequeue_tp = await tester.test_queue_throughput(load)
        results['queue'].append((load, enqueue_tp, dequeue_tp))
        
        # Cache benchmark
        put_tp, get_tp = await tester.test_cache_throughput(load)
        results['cache'].append((load, put_tp, get_tp))
        
        # Print latency stats
        tester.print_latency_stats()
        tester.results.clear()
    
    # Print summary
    print(f"\n{'='*60}")
    print("BENCHMARK SUMMARY")
    print(f"{'='*60}")
    
    print("\n--- Lock Manager ---")
    for load, throughput in results['lock']:
        print(f"Load: {load:5d} | Throughput: {throughput:8.2f} ops/sec")
    
    print("\n--- Queue System ---")
    for load, enq_tp, deq_tp in results['queue']:
        print(f"Load: {load:5d} | Enqueue: {enq_tp:8.2f} msgs/sec | Dequeue: {deq_tp:8.2f} msgs/sec")
    
    print("\n--- Cache System ---")
    for load, put_tp, get_tp in results['cache']:
        print(f"Load: {load:5d} | Put: {put_tp:8.2f} ops/sec | Get: {get_tp:8.2f} ops/sec")
    
    print(f"\n{'='*60}")
    print("BENCHMARKS COMPLETED")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    try:
        asyncio.run(run_all_benchmarks())
    except KeyboardInterrupt:
        print("\nBenchmarks interrupted by user")
    except Exception as e:
        print(f"\nError running benchmarks: {e}")
        sys.exit(1)