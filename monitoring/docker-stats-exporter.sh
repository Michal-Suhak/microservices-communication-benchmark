#!/bin/sh
# Docker Stats Exporter for Prometheus
# Exports container CPU and memory metrics with human-readable names

OUTPUT_FILE="/tmp/docker_stats.prom"

# Get stats for all containers
docker stats --no-stream --format "{{.Name}},{{.CPUPerc}},{{.MemUsage}}" | while IFS=',' read -r name cpu mem; do
    # Skip header
    if [ "$name" = "NAME" ]; then
        continue
    fi

    # Extract numeric values
    cpu_value=$(echo "$cpu" | sed 's/%//')
    mem_value=$(echo "$mem" | awk '{print $1}' | sed 's/MiB//')

    # Extract protocol and service from container name
    case "$name" in
        rest-*|jsonrpc-*|grpc-*|kafka-*|rabbitmq-*)
            protocol=$(echo "$name" | cut -d'-' -f1)
            service=$(echo "$name" | cut -d'-' -f2)

            # Only export if it's a valid service
            case "$service" in
                order|payment|notification)
                    echo "docker_container_cpu_percent{container=\"$name\",protocol=\"$protocol\",service=\"$service\"} $cpu_value"
                    echo "docker_container_memory_mb{container=\"$name\",protocol=\"$protocol\",service=\"$service\"} $mem_value"
                    ;;
            esac
            ;;
    esac
done > "$OUTPUT_FILE.tmp"

mv "$OUTPUT_FILE.tmp" "$OUTPUT_FILE"
