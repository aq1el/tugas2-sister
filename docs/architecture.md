# Architecture Documentation

## System Overview

The Distributed Synchronization System is designed to provide reliable coordination between multiple nodes in a distributed environment. It implements three core components:

1. **Distributed Lock Manager** - Prevents race conditions
2. **Distributed Queue** - Ensures message ordering and delivery
3. **Distributed Cache** - Provides fast data access with coherence

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                   Load Balancer / API Gateway            │
└─────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐       ┌────▼────┐       ┌────▼────┐
   │ Node 1  │◄─────►│ Node 2  │◄─────►│ Node 3  │
   └─────────┘       └─────────┘       └─────────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                    ┌──────▼──────┐
                    │    Redis    │
                    │  (Storage)  │
                    └─────────────┘
```

## Component Architecture

### 1. Node Architecture

Each node consists of:

```
Node
├── Lock Manager
│   ├── Raft Consensus
│   ├── Lock State Machine
│   └── Deadlock Detector
│
├── Queue Manager
│   ├── Consistent Hash Ring
│   ├── Message Storage
│   └── Delivery Tracker
│
├── Cache Manager
│   ├── MESI Protocol Handler
│   ├── LRU Eviction
│   └── Invalidation Manager
│
└── Communication Layer
    ├── Message Passing
    ├── Failure Detector
    └── RPC Handler
```

### 2. Distributed Lock Manager

**Algorithm**: Raft Consensus with majority voting

**Features**:
- Shared and Exclusive locks
- Deadlock detection using wait-for graph
- Automatic deadlock resolution

**Lock States**:
```python
LOCKED (Exclusive) → Only one holder
SHARED → Multiple readers allowed
PENDING → Waiting for lock
```

**Deadlock Detection**:
- Cycle detection in wait-for graph
- Resolution: Abort youngest transaction

### 3. Distributed Queue

**Algorithm**: Consistent Hashing for partitioning

**Features**:
- At-least-once delivery guarantee
- Message persistence
- Automatic retry with exponential backoff
- Dead letter queue for failed messages

**Consistent Hashing**:
- 150 virtual nodes per physical node
- Minimal data movement on node addition/removal

**Message Flow**:
```
Producer → Hash(msg_id) → Target Node → Queue → Consumer
                                    ↓
                              Persistent Storage
```

### 4. Distributed Cache

**Protocol**: MESI Cache Coherence

**Cache States**:
- **M**odified: Dirty, exclusive to this cache
- **E**xclusive: Clean, exclusive to this cache
- **S**hared: Clean, may exist in other caches
- **I**nvalid: Not valid

**State Transitions**:
```
         Read Hit      Write
I ──────────────→ S ──────→ M
     ↑                       │
     └───────────────────────┘
          Invalidate
```

**Invalidation Protocol**:
1. Write operation → Set local to MODIFIED
2. Broadcast invalidation to all nodes
3. Other nodes → Set to INVALID
4. Write-back on eviction

## Communication Protocol

### Message Types

1. **Heartbeat** - Failure detection
2. **RequestVote** - Raft leader election
3. **AppendEntries** - Raft log replication
4. **LockRequest** - Lock acquisition
5. **LockRelease** - Lock release
6. **Invalidate** - Cache invalidation
7. **QueueMessage** - Message routing

### RPC Format

```json
{
  "type": "message_type",
  "sender": "node_id",
  "term": 123,
  "data": {
    // Message-specific data
  }
}
```

## Consensus Algorithm (Raft)

### States
- **Follower**: Passive, responds to RPCs
- **Candidate**: Requests votes during election
- **Leader**: Handles all client requests

### Leader Election
1. Follower timeout → Become Candidate
2. Increment term, vote for self
3. Request votes from all nodes
4. Majority votes → Become Leader
5. Send heartbeats to maintain leadership

### Log Replication
1. Client request → Leader appends to log
2. Leader sends AppendEntries to followers
3. Followers append entries
4. Majority acknowledged → Commit
5. Apply to state machine

## Failure Handling

### Node Failures

**Detection**: Heartbeat timeout (5 seconds)

**Recovery**:
1. Failure detector marks node as failed
2. Raft triggers new election if leader failed
3. Queue messages redistributed via consistent hashing
4. Cache entries marked INVALID

### Network Partitions

**Split-Brain Prevention**: Raft majority voting

**Scenario**: 3-node cluster splits into 2+1
- Partition with 2 nodes: Can elect leader (majority)
- Partition with 1 node: Cannot make progress

**Recovery**: When partition heals:
1. Lower-term leader steps down
2. Log entries replayed from current leader
3. State synchronized

### Data Consistency

**Lock Manager**: Linearizability via Raft
**Queue**: At-least-once delivery (may duplicate)
**Cache**: Sequential consistency via MESI

## Performance Considerations

### Throughput Optimization
- Batched message processing
- Pipelining in Raft log replication
- Connection pooling for RPC

### Latency Optimization
- Local caching with coherence
- Fast path for uncontended locks
- Priority queues for urgent messages

### Scalability
- Horizontal scaling via consistent hashing
- Independent scaling of each component
- Sharding support

## Deployment Architecture

### Docker Compose Setup

```yaml
services:
  node1, node2, node3:
    - Each node runs full stack
    - Connected via Docker network
    - Persistent storage via volumes
  
  redis:
    - Shared storage backend
    - Used for persistence
```

### Production Considerations
- Use Kubernetes for orchestration
- Persistent volumes for state
- Load balancer for API gateway
- Monitoring with Prometheus
- Logging with ELK stack

## Security

### Authentication
- TLS for inter-node communication
- API key authentication for clients

### Authorization
- Resource-based access control
- Node identity verification

### Data Protection
- Encryption at rest
- Encryption in transit
- Secure key management

## Monitoring & Observability

### Metrics (Prometheus)
- Request throughput
- Latency percentiles (P50, P95, P99)
- Lock acquisition time
- Queue depth
- Cache hit rate
- Node health status

### Logging
- Structured logging (JSON)
- Log levels: DEBUG, INFO, WARN, ERROR
- Distributed tracing support

### Alerts
- Node failure
- High latency
- Queue backlog
- Cache eviction rate

## Future Enhancements

1. **Multi-datacenter support** - Geographic replication
2. **Dynamic membership** - Auto-scaling
3. **Priority scheduling** - QoS guarantees
4. **Read replicas** - Improved read performance
5. **Snapshot support** - Faster recovery