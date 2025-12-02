up:
	docker compose up -d
	@echo ""
	@echo "Services started successfully!"
	@echo ""
	@echo "Service URLs:"
	@echo "  REST:     http://localhost:8001"
	@echo "  JSON-RPC: http://localhost:8011"
	@echo ""
	@echo "Monitoring:"
	@echo "  Grafana:     http://localhost:3000 (admin/admin)"
	@echo "  Prometheus:  http://localhost:9095"

down:
	docker compose down

logs:
	docker compose logs -f

restart:
	docker compose restart

clean:
	docker compose down -v
	rm -rf results/*.json
	@echo "All services stopped and data cleaned"

format:
	@echo "Formatting Python code..."
	black .
	isort .
	@echo "Code formatted successfully!"

lint:
	@echo "Running linters..."
	ruff check .
	@echo "Linting complete!"

test:
	@echo "Running tests..."
	pytest -v
	@echo "Tests complete!"

benchmark-rest:
	@echo "Running REST benchmark..."
	@mkdir -p results
	locust -f benchmark/locust_rest.py --host http://localhost:8001 --headless \
		--users 100 --spawn-rate 10 --run-time 5m \
		--html results/rest_report.html --csv results/rest
	@echo "REST benchmark complete! Report: results/rest_report.html"

benchmark-jsonrpc:
	@echo "Running JSON-RPC benchmark..."
	@mkdir -p results
	locust -f benchmark/locust_jsonrpc.py --host http://localhost:8011 --headless \
		--users 100 --spawn-rate 10 --run-time 5m \
		--html results/jsonrpc_report.html --csv results/jsonrpc
	@echo "JSON-RPC benchmark complete! Report: results/jsonrpc_report.html"

benchmark-grpc:
	@echo "Running gRPC benchmark..."
	@mkdir -p results
	locust -f benchmark/locust_grpc.py --headless \
		--users 100 --spawn-rate 10 --run-time 5m \
		--html results/grpc_report.html --csv results/grpc
	@echo "gRPC benchmark complete! Report: results/grpc_report.html"

benchmark-all:
	@echo "Running all benchmarks in parallel..."
	@mkdir -p results
	@locust -f benchmark/locust_rest.py --host http://localhost:8001 --headless \
		--users 100 --spawn-rate 10 --run-time 5m \
		--html results/rest_report.html --csv results/rest & \
	locust -f benchmark/locust_jsonrpc.py --host http://localhost:8011 --headless \
		--users 100 --spawn-rate 10 --run-time 5m \
		--html results/jsonrpc_report.html --csv results/jsonrpc & \
	locust -f benchmark/locust_grpc.py --headless \
		--users 100 --spawn-rate 10 --run-time 5m \
		--html results/grpc_report.html --csv results/grpc & \
	wait
	@echo ""
	@echo "=========================================="
	@echo "All benchmarks completed!"
	@echo "=========================================="
	@echo "Results:"
	@ls -lh results/*.html

benchmark: benchmark-all
