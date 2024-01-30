build:
	docker-compose  build

up:
	docker-compose  up

up-pro:
	docker-compose  up -d

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

arm-black:
	docker-compose -f docker-compose-arm.yml run --rm fastapi black --config=pyproject.toml --skip-string-normalization .

arm-bash:
	docker-compose -f docker-compose-arm.yml run --rm fastapi sh