import pymysql
import re
import numpy as np
import pandas as pd
import unicodedata
import time
import requests
import json
import os
import sendgrid
import os
from sendgrid.helpers.mail import *

## TO DO: Write Script to query and save to backend.
## Maintain when a metric gets deleted, to adjust deletedAt for all of these metrics

start_time = time.time()

# This section is for running the service locally.
if os.environ.get("SQL_IP") == None:
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv())

# This loads the configuration needed to beginning the pool for the mySQL database
SQL_IP=os.environ.get('SQL_IP')
SQL_USER=os.environ.get('SQL_USER')
SQL_PASSWORD=os.environ.get('SQL_PASSWORD')
SQL_SCHEMA=os.environ.get('SQL_SCHEMA')

db = pymysql.connect(SQL_IP,SQL_USER,SQL_PASSWORD,SQL_SCHEMA, autocommit = True)
cursor = db.cursor()
print("Database Initialized")


getActiveMetricsQuery = """
    SELECT cpm.id, cpm.pair, cpm.market, mt.accessKey
    FROM crypto.CurrencyPairMetric cpm
    JOIN crypto.MetricType mt on cpm.metricTypeId = mt.id
    WHERE cpm.id IN
    (
    SELECT DISTINCT ucpm.currencyPairMetricId
    FROM UserCurrencyPairMetric ucpm
    WHERE ucpm.deletedAt is null
    )
    """

cursor.execute(getActiveMetricsQuery)
currentMetrics = cursor.fetchall()
print(currentMetrics)

for row in currentMetrics:
    cpmId, pair, market, accessKey = row[0], row[1], row[2], row[3]
    result = requests.get(f"https://api.cryptowat.ch/markets/{market}/{pair}/summary")
    data = result.json()
    print(data)
    volume = data["result"]["volume"]
    print(volume)
db.close()
print("ClosedDB")
