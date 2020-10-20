FROM python:3
ENV PYTHONUNBUFFERED 1
RUN mkdir /code
RUN mkdir /code/logs
WORKDIR /code
COPY . .
RUN pip install -r requirements.txt
RUN pip install gunicorn==20.0.4
#COPY . /code/