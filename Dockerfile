FROM python:3.8-slim-buster

WORKDIR /usr/src/app

RUN python3 -m pip install flask requests apscheduler

COPY server.py .
COPY kv_log.py .

EXPOSE 5000

CMD ["python",  "server.py"]
