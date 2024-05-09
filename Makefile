build:
	docker-compose  build

up:
	docker-compose  up

up-pro:
	docker-compose  up -d

up-db-pro:
	docker-compose  up -d postgres

down:
	docker-compose  down

stop:
	docker-compose  stop

init-migrations:
	docker-compose  run --rm fastapi alembic init alembic

apply-migrations:
	docker-compose  run --rm fastapi alembic upgrade head

migrate:
	docker-compose  run --rm fastapi alembic revision --autogenerate -m "migration"

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

arm-build:
	docker-compose -f docker-compose-arm.yml build

arm-up:
	docker-compose -f docker-compose-arm.yml up

arm-down:
	docker-compose -f docker-compose-arm.yml down

arm-stop:
	docker-compose -f docker-compose-arm.yml stop

arm-apply-migrations:
	docker-compose -f docker-compose-arm.yml run --rm fastapi alembic upgrade head

arm-migrate:
	docker-compose -f docker-compose-arm.yml run --rm fastapi alembic revision --autogenerate -m "create table"

arm-bash:
	docker-compose -f docker-compose-arm.yml run --rm fastapi sh

arm-clean:
	docker-compose -f docker-compose-arm.yml down --rmi all --volumes --remove-orphans | true
	docker-compose -f docker-compose-arm.yml rm -f | true

arm-flake8:
	docker-compose -f docker-compose-arm.yml run --rm fastapi flake8 .

arm-pylint:
	docker-compose -f docker-compose-arm.yml run --rm fastapi sh -c "find . -name '*.py' -type f | xargs pylint"

arm-black:
	docker-compose -f docker-compose-arm.yml run --rm fastapi black --config=pyproject.toml --skip-string-normalization .