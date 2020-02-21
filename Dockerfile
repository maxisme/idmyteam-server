FROM python:3

WORKDIR /usr/src/idmyteam

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

ADD . .
ENV PYTHONPATH /usr/src/idmyteam/:/usr/src/idmyteam/web/:/usr/src/idmyteam/settings/

CMD ["python3", "/usr/src/idmyteam/server.py"]