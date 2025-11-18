from prometheus_client import Counter, Histogram

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
    buckets=(64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768),
)

# Error counter
ERROR_COUNT = Counter(
    "error_total",
    "Total number of errors",
    ["protocol", "service", "error_type"],
)
