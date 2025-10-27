# Deployment Guide

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- Python 3.8+ (for local development)
- 4GB RAM minimum
- 10GB disk space

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/aq1el/tugas2-sister.git
cd tugas2-sister
```

### 2. Environment Setup

```bash
cp .env.example .env
# Edit .env if needed
```

### 3. Start with Docker Compose

```bash
docker-compose up -d
```

This starts:
- 3 distributed nodes (ports 8001, 8002, 8003)
- Redis for persistence (port 6379)

### 4. Verify Deployment

```bash
# Check node health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health

# Check system status
curl http://localhost:8001/status
```

## Local Development

### Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Run Single Node

```bash
export NODE_ID=node1
export NODE_PORT=8001
python -m src.main
```

### Run Tests

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Performance tests
python tests/performance/load_test.py
```

## Production Deployment

### Docker Build

```bash
# Build image
docker build -f docker/Dockerfile -t tugas2-sister:latest .

# Tag for registry
docker tag tugas2-sister:latest your-registry/tugas2-sister:latest

# Push to registry
docker push your-registry/tugas2-sister:latest
```

### Kubernetes Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: distributed-sync
spec:
  serviceName: "distributed-sync"
  replicas: 3
  selector:
    matchLabels:
      app: distributed-sync
  template:
    metadata:
      labels:
        app: distributed-sync
    spec:
      containers:
      - name: node
        image: tugas2-sister:latest
        ports:
        - containerPort: 8001
        env:
        - name: NODE_ID
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: REDIS_HOST
          value: "redis-service"
```

Apply:
```bash
kubectl apply -f deployment.yaml
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| NODE_ID | Unique node identifier | node1 |
| NODE_PORT | HTTP API port | 8001 |
| CLUSTER_NODES | Comma-separated node list | node1:8001,node2:8002,node3:8003 |
| REDIS_HOST | Redis hostname | localhost |
| REDIS_PORT | Redis port | 6379 |
| ELECTION_TIMEOUT_MIN | Min election timeout (ms) | 150 |
| ELECTION_TIMEOUT_MAX | Max election timeout (ms) | 300 |
| HEARTBEAT_INTERVAL | Heartbeat interval (ms) | 50 |
| CACHE_SIZE | Cache capacity | 1000 |
| CACHE_POLICY | Cache eviction policy | LRU |

### Scaling

**Horizontal Scaling:**
```bash
# Scale to 5 nodes
docker-compose up -d --scale node=5
```

**Update cluster configuration:**
```bash
export CLUSTER_NODES=node1:8001,node2:8002,node3:8003,node4:8004,node5:8005
```

## Monitoring

### Prometheus Integration

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'distributed-sync'
    static_configs:
      - targets:
        - 'localhost:8001'
        - 'localhost:8002'
        - 'localhost:8003'
```

### Grafana Dashboard

Import dashboard from `monitoring/grafana-dashboard.json`

Key metrics:
- Request throughput
- Latency percentiles
- Lock acquisition time
- Queue depth
- Cache hit rate

## Troubleshooting

### Node Won't Start

```bash
# Check logs
docker-compose logs node1

# Common issues:
# 1. Port already in use
# 2. Redis not accessible
# 3. Invalid configuration
```

### High Latency

```bash
# Check node status
curl http://localhost:8001/status

# Check metrics
curl http://localhost:8001/metrics

# Possible causes:
# 1. Network issues between nodes
# 2. Redis bottleneck
# 3. Lock contention
```

### Split Brain

```bash
# Verify Raft state
curl http://localhost:8001/status | jq '.raft_state'

# Should have only ONE leader
# If multiple leaders, check network partitions
```

## Backup & Recovery

### Backup

```bash
# Backup Redis data
docker-compose exec redis redis-cli SAVE
docker cp container_id:/data/dump.rdb ./backup/

# Backup logs
docker-compose logs > backup/logs.txt
```

### Recovery

```bash
# Restore Redis data
docker cp ./backup/dump.rdb container_id:/data/
docker-compose restart redis
```

## Security

### Enable TLS

```bash
# Generate certificates
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout key.pem -out cert.pem

# Update docker-compose.yml
environment:
  - TLS_CERT=/certs/cert.pem
  - TLS_KEY=/certs/key.pem
volumes:
  - ./certs:/certs
```

### API Authentication

```bash
# Set API key
export API_KEY=your-secret-key

# Use in requests
curl -H "Authorization: Bearer $API_KEY" http://localhost:8001/status
```

## Performance Tuning

### Optimize for Throughput

```bash
export BATCH_SIZE=100
export MAX_CONNECTIONS=1000
```

### Optimize for Latency

```bash
export CACHE_SIZE=10000
export ELECTION_TIMEOUT_MIN=100
export HEARTBEAT_INTERVAL=25
```

## Maintenance

### Rolling Update

```bash
# Update one node at a time
docker-compose up -d --no-deps --build node1
sleep 30
docker-compose up -d --no-deps --build node2
sleep 30
docker-compose up -d --no-deps --build node3
```

### Health Checks

```bash
#!/bin/bash
for port in 8001 8002 8003; do
  status=$(curl -s http://localhost:$port/health | jq -r '.status')
  echo "Node $port: $status"
done
```