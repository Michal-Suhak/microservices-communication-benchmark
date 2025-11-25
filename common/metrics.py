from prometheus_client import Counter, Gauge, Histogram, Info

# Request counter
REQUEST_COUNT = Counter(
    "request_total",
    "Total number of requests",
    ["protocol", "service", "method"],
)

# Request latency histogram
REQUEST_LATENCY = Histogram(
    "request_latency_seconds",
    "Request latency in seconds",
    ["protocol", "service", "method"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# Payload size histogram
PAYLOAD_SIZE = Histogram(
    "payload_size_bytes",
    "Payload size in bytes",
    ["protocol", "service", "direction"],
    buckets=(100, 500, 1000, 5000, 10000, 50000, 100000, 500000),
)

# Error counter
ERROR_COUNT = Counter(
    "error_total",
    "Total number of errors",
    ["protocol", "service", "error_type"],
)

# Active connections gauge
ACTIVE_CONNECTIONS = Gauge(
    "active_connections",
    "Number of active connections",
    ["protocol", "service"],
)

# Service info
SERVICE_INFO = Info("service_info", "Service information")
