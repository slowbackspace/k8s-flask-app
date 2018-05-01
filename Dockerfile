FROM python:3
RUN apt-get install libmysqlclient-dev
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY run_gunicorn.sh ./
COPY source source
EXPOSE 5000
CMD [ "./run_gunicorn.sh" ]
