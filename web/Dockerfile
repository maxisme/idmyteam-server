FROM python:3.8-slim
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

RUN apt update && apt install -y curl
HEALTHCHECK CMD curl --fail http://localhost:8000 || exit 1

ENTRYPOINT ["/usr/src/app/entrypoint.sh"]