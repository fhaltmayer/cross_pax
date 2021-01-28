FROM redis:alpine

RUN apk add --update --no-cache python3 && ln -sf python3 /usr/bin/python
run apk add --update --no-cache bash
RUN python3 -m ensurepip
RUN pip3 install --no-cache --upgrade pip setuptools


WORKDIR /usr/src/app

RUN python3 -m pip install flask requests apscheduler redis

COPY server.py .
COPY kv_log.py .
COPY redis_commands.py .
COPY redis_and_server_start.sh .

RUN chmod 777 redis_and_server_start.sh

EXPOSE 5000

CMD ./redis_and_server_start.sh
