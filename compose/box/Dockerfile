
FROM balenalib/raspberrypi3-python:3.6-edge

ENV PYTHONUNBUFFERED 1
RUN pip install --upgrade pip
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . /app
WORKDIR /app
RUN python /app/setup.py install
