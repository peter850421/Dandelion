FROM python:3.6

ENV PYTHONUNBUFFERED 1

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . /app
WORKDIR /app
RUN python /app/setup.py install


ENTRYPOINT ["python", "run_box.py"]
CMD ["bash"]