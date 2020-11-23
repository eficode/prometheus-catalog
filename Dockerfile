FROM python:3.8
RUN apt-get clean \
    && apt-get -y update
RUN apt-get -y install nginx python3-dev build-essential
COPY requirements.txt /srv/flask_app/
WORKDIR /srv/flask_app
ENV CURL_CA_BUNDLE=""
RUN pip install -r requirements.txt --src /usr/local/src
COPY . /srv/flask_app
COPY nginx.conf /etc/nginx
RUN chmod +x ./start.sh
CMD ["./start.sh"]
