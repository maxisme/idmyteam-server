FROM python:3.8-slim
COPY . .
RUN pip install -r requirements.txt
HEALTHCHECK CMD curl --fail http://localhost:8000/ || exit 1
CMD [ "python", "./manage.py", "runserver", "0.0.0.0:8000"]