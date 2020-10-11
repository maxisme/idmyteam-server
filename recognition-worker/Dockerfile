FROM tensorflow/tensorflow:devel-gpu
ENV PYTHONUNBUFFERED 1
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD [ "python", "worker.py" ]