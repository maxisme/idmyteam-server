FROM python:3.8-slim
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["/usr/src/app/entrypoint.sh"]