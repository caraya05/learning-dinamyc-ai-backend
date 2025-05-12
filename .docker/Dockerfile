FROM python:3.12-alpine AS builder
ENV PYTHONUNBUFFERED 1
ENV C_FORCE_ROOT=1
WORKDIR /code
RUN apk add --no-cache git cmake libffi-dev linux-headers g++ ffmpeg
COPY ./src/requirements.txt /code/requirements.txt
RUN pip install "Cython<3.0" pyyaml --no-build-isolation \
    && pip install --no-cache-dir --upgrade -r /code/requirements.txt
COPY ./src/. /code
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]