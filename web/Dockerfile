FROM python:3.8-slim
COPY . .
RUN pip install -r requirements.txt
RUN apt update && apt install -y curl
HEALTHCHECK CMD curl --fail http://localhost:8000/ || exit 1
CMD [ "python", "./manage.py", "runserver", "0.0.0.0:8000"]