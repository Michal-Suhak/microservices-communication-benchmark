#!/bin/bash

set -e

USERS=${USERS:-100}
SPAWN_RATE=${SPAWN_RATE:-10}
RUN_TIME=${RUN_TIME:-5m}
RESULTS_DIR="results/stress_tests"

mkdir -p "$RESULTS_DIR"

echo "Starting stress tests with configuration:"
echo "  Users: $USERS"
echo "  Spawn Rate: $SPAWN_RATE"
echo "  Run Time: $RUN_TIME"
echo ""

run_test() {
    local protocol=$1
    local locustfile=$2
    local host=$3
    local output_prefix=$4

    echo "=========================================="
    echo "Running $protocol stress test"
    echo "=========================================="

    locust -f "$locustfile" \
        --host "$host" \
        --headless \
        --users "$USERS" \
        --spawn-rate "$SPAWN_RATE" \
        --run-time "$RUN_TIME" \
        --html "$RESULTS_DIR/${output_prefix}_report.html" \
        --csv "$RESULTS_DIR/${output_prefix}" \
        --loglevel INFO

    echo ""
    echo "$protocol stress test completed"
    echo "Results saved to: $RESULTS_DIR/${output_prefix}_*"
    echo ""
}

echo "Checking if services are running..."
if ! curl -sf http://localhost:8001/health > /dev/null; then
    echo "ERROR: REST service not running on port 8001"
    exit 1
fi

if ! curl -sf http://localhost:8011/health > /dev/null; then
    echo "ERROR: JSON-RPC service not running on port 8011"
    exit 1
fi

echo "All services are healthy"
echo ""

run_test "REST" "benchmark/locust_rest.py" "http://localhost:8001" "rest"
run_test "JSON-RPC" "benchmark/locust_jsonrpc.py" "http://localhost:8011" "jsonrpc"
run_test "gRPC" "benchmark/locust_grpc.py" "localhost:8021" "grpc"

echo "=========================================="
echo "All stress tests completed!"
echo "=========================================="
echo ""
echo "Results location: $RESULTS_DIR/"
echo ""
echo "Summary files:"
ls -lh "$RESULTS_DIR/"