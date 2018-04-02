FROM python:3.6

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app
RUN pip install --no-cache-dir -r requirements.txt

COPY katello_exporter.py /usr/src/app

EXPOSE 9118
ENV DEBUG=0

ENTRYPOINT [ "python", "-u", "./katello_exporter.py" ]
