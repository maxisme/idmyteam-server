FROM python:3.8-slim
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app
ADD requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENTRYPOINT ["/usr/src/app/entrypoint.sh"]