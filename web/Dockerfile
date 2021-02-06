FROM python:3.9-slim

ARG COMMIT_HASH
ENV COMMIT_HASH=$COMMIT_HASH

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app
RUN apt-get update && apt-get install gcc -y
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
