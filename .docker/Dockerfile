FROM python:3.10-alpine
ENV PYTHONUNBUFFERED 1
ENV C_FORCE_ROOT=1
RUN apk add --no-cache gdal libpq-dev git cmake gettext libffi-dev gcc g++ musl-dev linux-headers figlet ffmpeg
WORKDIR /code
COPY ./src/requirements.txt /code/requirements.txt
RUN pip install "Cython<3.0" pyyaml --no-build-isolation
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
COPY ./src/. /code
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]