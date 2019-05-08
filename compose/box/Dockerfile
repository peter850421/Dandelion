#FROM python:3.6
FROM balenalib/raspberrypi3-python:3.6-stretch-run

ENV PYTHONUNBUFFERED 1
RUN pip3 install --upgrade pip
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . /app
WORKDIR /app
RUN python /app/setup.py install
