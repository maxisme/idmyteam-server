FROM tensorflow/tensorflow:devel-gpu
RUN apt-get update && apt-get install python-numpy -y
ENV PYTHONUNBUFFERED 1
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD [ "python", "worker.py" ]