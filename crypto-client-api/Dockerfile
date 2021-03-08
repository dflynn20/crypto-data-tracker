FROM amd64/python:3.7

WORKDIR /crypto-client-api

COPY ./requirements.txt /crypto-client-api/requirements.txt

RUN pip install -r requirements.txt

RUN pip install gunicorn flask

COPY . /crypto-client-api

EXPOSE 5000

CMD ["gunicorn", "-b", "0.0.0.0:5000", "wsgi:app", "--graceful-timeout", "5", "-t", "5", "--keep-alive", "5"]
