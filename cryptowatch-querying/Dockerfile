FROM python:3.7

WORKDIR /cryptowatch-querying
ADD . /cryptowatch-querying

ADD query-cryptowatch.py /
RUN pip install -r requirements.txt

CMD python query-cryptowatch.py
