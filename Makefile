build:
	docker-compose  build --no-cache

up:
	docker-compose  up

up-pro:
	docker-compose  up -d

#up-db-pro:
#	docker-compose  up -d postgres

down:
	docker-compose  down

stop:
	docker-compose  stop

#init-migrations:
#	docker-compose  run --rm fastapi alembic init alembic

#apply-migrations:
#	docker-compose  run --rm fastapi alembic upgrade head

#migrate:
#	docker-compose  run --rm fastapi alembic revision --autogenerate -m "migration"

black:
	docker-compose  run --rm fastapi black --config=pyproject.toml --skip-string-normalization .

bash:
	docker-compose  run --rm fastapi sh

clean:
	docker-compose down --rmi all --volumes --remove-orphans | true
	docker-compose rm -f | true

flake8:
	docker-compose run --rm fastapi flake8 code

pylint:
	docker-compose run --rm fastapi pylint code

dev-build:
	docker-compose -f docker-compose-develop.yml build --no-cache

dev-up:
	docker-compose -f docker-compose-develop.yml up

dev-up-pro:
	docker-compose -f docker-compose-develop.yml up -d

dev-down:
	docker-compose -f docker-compose-develop.yml down -v

dev-stop:
	docker-compose -f docker-compose-develop.yml stop

dev-black:
	docker-compose -f docker-compose-develop.yml run --rm fastapi black --config=pyproject.toml --skip-string-normalization .

dev-bash:
	docker-compose -f docker-compose-develop.yml run --rm fastapi sh

dev-clean:
	docker-compose -f docker-compose-develop.yml down --rmi all --volumes --remove-orphans | true
	docker-compose -f docker-compose-develop.yml rm -f | true

dev-flake8:
	docker-compose -f docker-compose-develop.yml run --rm fastapi flake8 code

dev-pylint:
	docker-compose -f docker-compose-develop.yml run --rm fastapi pylint code

stage-build:
	docker-compose -f docker-compose-stage.yml build --no-cache

stage-up:
	docker-compose -f docker-compose-stage.yml up

stage-up-pro:
	docker-compose -f docker-compose-stage.yml up -d

stage-down:
	docker-compose -f docker-compose-stage.yml down -v

stage-stop:
	docker-compose -f docker-compose-stage.yml stop

stage-black:
	docker-compose -f docker-compose-stage.yml run --rm fastapi black --config=pyproject.toml --skip-string-normalization .

stage-bash:
	docker-compose -f docker-compose-stage.yml run --rm fastapi sh

stage-clean:
	docker-compose -f docker-compose-stage.yml down --rmi all --volumes --remove-orphans | true
	docker-compose -f docker-compose-stage.yml rm -f | true

stage-flake8:
	docker-compose -f docker-compose-stage.yml run --rm fastapi flake8 code

stage-pylint:
	docker-compose -f docker-compose-stage.yml run --rm fastapi pylint code

arm-build:
	docker-compose -f docker-compose-arm.yml build --no-cache

arm-up:
	docker-compose -f docker-compose-arm.yml up

arm-down:
	docker-compose -f docker-compose-arm.yml down -v

arm-stop:
	docker-compose -f docker-compose-arm.yml stop

#arm-apply-migrations:
#	docker-compose -f docker-compose-arm.yml run --rm fastapi alembic upgrade head

#arm-migrate:
#	docker-compose -f docker-compose-arm.yml run --rm fastapi alembic revision --autogenerate -m "create table"

#arm-bash:
#	docker-compose -f docker-compose-arm.yml run --rm fastapi sh

arm-clean:
	docker-compose -f docker-compose-arm.yml down --rmi all --volumes --remove-orphans | true
	docker-compose -f docker-compose-arm.yml rm -f | true

arm-flake8:
	docker-compose -f docker-compose-arm.yml run --rm fastapi flake8 .

arm-pylint:
	docker-compose -f docker-compose-arm.yml run --rm fastapi sh -c "find . -name '*.py' -type f | xargs pylint"

arm-black:
	docker-compose -f docker-compose-arm.yml run --rm fastapi black --config=pyproject.toml --skip-string-normalization .

arm-build-bg:
	docker-compose -f docker-compose-arm.yml build --no-cache celery_worker flower

arm-bash:
	docker-compose -f docker-compose-arm.yml run --rm fastapi sh

arm-test:
	docker-compose -f docker-compose-arm.yml run --rm fastapi pytest tests/

arm-update-docker:
	make arm-down && docker system prune -a && make arm-build && make arm-up

# ============================================================================
# TESTING - Analytics Module
# ============================================================================

test:
	cd src && python -m pytest analytics/tests_analytics.py -v

test-coverage:
	cd src && python -m pytest analytics/tests_analytics.py --cov=analytics --cov-report=html
	@echo "✅ Coverage report generated: htmlcov/index.html"

test-integration:
	cd src && python -m pytest analytics/tests_integration.py -v

test-all:
	cd src && python -m pytest analytics/ -v

test-watch:
	cd src && python -m pytest analytics/tests_analytics.py -v --tb=short

test-quick:
	cd src && python -m pytest analytics/tests_analytics.py -q

test-schemas:
	cd src && python -m pytest analytics/tests_analytics.py::TestAnalyticCreateSchema -v

test-exceptions:
	cd src && python -m pytest analytics/tests_analytics.py::TestExceptions -v

test-services:
	cd src && python -m pytest analytics/tests_analytics.py -k "Service" -v

test-analytics-docker:
	docker-compose -f docker-compose-develop.yml run --rm fastapi sh -c "python -m pytest analytics/tests_analytics.py -v"

test-coverage-docker:
	docker-compose -f docker-compose-develop.yml run --rm fastapi sh -c "python -m pytest analytics/tests_analytics.py --cov=analytics --cov-report=html"

# ============================================================================
# TESTING - User Dashboard Module
# ============================================================================

test-dashboard:
	cd src && python -m pytest user/tests_dashboard.py -v

test-dashboard-coverage:
	cd src && python -m pytest user/tests_dashboard.py --cov=user --cov-report=html
	@echo "✅ Coverage report generated: htmlcov/index.html"

test-dashboard-integration:
	cd src && python -m pytest user/tests_integration_dashboard.py -v

test-dashboard-docker:
	docker-compose -f docker-compose-develop.yml run --rm fastapi sh -c "python -m pytest user/tests_dashboard.py -v"

test-dashboard-coverage-docker:
	docker-compose -f docker-compose-develop.yml run --rm fastapi sh -c "python -m pytest user/tests_dashboard.py --cov=user --cov-report=html"

# ============================================================================

git:
	git config  --global user.name "caraya05"
	git config  --global user.email "carlos.amy375d@gmail.com"