#FROM python:3.6
FROM resin/raspberry-pi-alpine:3.6 AS build

ENV PYTHONUNBUFFERED 1

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . /app
WORKDIR /app
RUN python /app/setup.py install
