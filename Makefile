.PHONY: help start stop restart logs clean test example

help:
	@echo "PR Telemetry - Makefile commands"
	@echo ""
	@echo "  make start     - Start all services"
	@echo "  make stop      - Stop all services"
	@echo "  make restart   - Restart all services"
	@echo "  make logs      - Show logs (all services)"
	@echo "  make clean     - Stop and remove all volumes"
	@echo "  make example   - Run E2E example"
	@echo "  make test      - Run tests"
	@echo ""

start:
	@echo "Starting PR Telemetry services..."
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 10
	@echo "Checking health..."
	@curl -s http://localhost:8000/healthz || echo "API not ready yet, wait a few more seconds"
	@echo ""
	@echo "✅ Services started!"
	@echo "API: http://localhost:8000"
	@echo "MinIO Console: http://localhost:9001"

stop:
	@echo "Stopping services..."
	docker-compose stop

restart:
	@echo "Restarting services..."
	docker-compose restart

logs:
	docker-compose logs -f

clean:
	@echo "Stopping and removing all containers and volumes..."
	docker-compose down -v
	@echo "✅ Cleaned!"

example:
	@echo "Running E2E example..."
	python3 examples/submit_example.py

test:
	@echo "Running tests..."
	pytest tests/ -v

