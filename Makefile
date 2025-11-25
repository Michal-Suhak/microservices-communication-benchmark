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
	@echo "  Prometheus:  http://localhost:9090"
	@echo "  cAdvisor:    http://localhost:8080"

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

benchmark:
	@echo "Running benchmarks..."

report:
	@echo "Generating benchmark report..."