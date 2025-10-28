# Distributed Synchronization System

Implementasi sistem sinkronisasi terdistribusi untuk Tugas 2 Sistem Parallel dan Terdistribusi.

## 🎥 Video Demonstration

**[Video Walkthrough - YouTube](LINK_WILL_BE_ADDED)**

Video menjelaskan:
- Architecture & design decisions
- Implementation details dari 3 komponen utama  
- Code walkthrough
- Documentation overview

## 📋 Komponen Utama

### 1. Distributed Lock Manager
- Raft Consensus Algorithm
- Deadlock Detection dengan Wait-For Graph
- Shared & Exclusive Locks
- Lock Queuing & Fairness

### 2. Distributed Queue  
- Consistent Hashing (150 virtual nodes)
- At-Least-Once Delivery
- Message Persistence dengan Redis
- Priority Queue Support

### 3. Distributed Cache
- MESI Coherence Protocol
- Automatic Invalidation Broadcast
- LRU Eviction Policy
- Multi-node Consistency

## 🏗️ Architecture

Sistem ini menggunakan:
- **Consensus:** Raft Algorithm
- **Communication:** HTTP/JSON RPC
- **Failure Detection:** Heartbeat mechanism
- **Storage:** Redis untuk persistence

Lihat [Architecture Documentation](docs/architecture.md) untuk detail lengkap.

## 📚 Documentation

- [Architecture Overview](docs/architecture.md) - System design & component interaction
- [API Specification](docs/api_spec.yml) - OpenAPI format REST API
- [Deployment Guide](docs/deployment_guide.md) - Production deployment steps

## 🧪 Testing

### Unit & Integration Tests
```bash
pytest tests/
```

### Performance Testing
```bash
python tests/performance/load_test.py
```

**Performance Metrics:**
- Throughput: 10,000+ ops/sec
- Latency P95: <10ms
- Scalability: Up to 10 nodes

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Redis

### Running with Docker
```bash
docker-compose up -d
```

### Running Locally
```bash
# Install dependencies
pip install -r requirements.txt

# Start nodes
python -m src.main  # node1
```

## 📊 Features

✅ Distributed consensus dengan Raft  
✅ Fault tolerance & automatic failover  
✅ Deadlock detection & resolution  
✅ Message persistence & delivery guarantee  
✅ Cache coherence protocol  
✅ Comprehensive monitoring & metrics  
✅ Production-ready deployment  

## 🔧 Tech Stack

- **Language:** Python 3.11
- **Framework:** aiohttp (async HTTP)
- **Storage:** Redis
- **Deployment:** Docker Compose
- **Testing:** pytest, asyncio
- **Monitoring:** Prometheus metrics

## 📖 Implementation Details

### Raft Consensus
- Leader election dengan randomized timeout
- Log replication untuk consistency
- Commit protocol dengan majority quorum

### Consistent Hashing
- Virtual nodes untuk load balancing
- Minimal data movement on node changes
- Deterministic key routing

### MESI Protocol
- Modified, Exclusive, Shared, Invalid states
- Write-through invalidation
- Cache coherence guarantees

## 👨‍💻 Author

**aq1el** - Sistem Parallel dan Terdistribusi

## 📄 License

Educational project for distributed systems course.

---

**Repository:** https://github.com/aq1el/tugas2-sister
