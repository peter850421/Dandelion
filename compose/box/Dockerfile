#FROM python:3.6
FROM balenalib/%%BALENA_MACHINE_NAME%%-python:3-stretch-run

ENV PYTHONUNBUFFERED 1

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . /app
WORKDIR /app
RUN python /app/setup.py install
