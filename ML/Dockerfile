FROM tensorflow/tensorflow:devel-gpu
RUN apt-get update
RUN apt-get install -y libmysqlclient-dev
ENV PYTHONUNBUFFERED 1
RUN mkdir /code
WORKDIR /code
COPY requirements.txt /code/
RUN pip install -r requirements.txt
COPY . /code/
CMD [ "python", "worker.py" ]