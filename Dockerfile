FROM python:3.13.14-slim
WORKDIR /app
COPY *.py .
COPY requirements.txt .

RUN pip install -r requirements.txt
