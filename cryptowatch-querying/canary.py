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

BACKEND_EMAIL=os.environ.get('BACKEND_EMAIL')
CADENCE_PER_MINUTE=int(os.environ.get('CADENCE_PER_MINUTE'))
THRESHOLD=int(os.environ.get('FACTOR_DATA_FRESHNESS_THRESHOLD'))

# Thanks to https://github.com/sendgrid/sendgrid-python , this is a very easy way to send
# an email via Python.
def sendEmail(subject, body, recipient):
    sg = sendgrid.SendGridAPIClient(api_key=os.environ.get('SENDGRID_API_KEY'))
    from_email = Email("bot@crypto-data-tracker.com")
    to_email = To(recipient)
    content = Content("text/plain", body)
    mail = Mail(from_email, to_email, subject, content)
    response = sg.client.mail.send.post(request_body=mail.get())
    print(response.status_code)



# Sends the notice to the Backend engineer responsible for timeouts and performance improvements
def sendBackendDataPipelineAlert(secondsElapsed, gap):
    subject = "ERROR: Data Failing Freshness Probe"
    message =   f"""Hello,

                    Our query shows that the latest metric was added to the database {secondsElapsed} seconds ago, and this is above the
                    threshold by {round((secondsElapsed - gap)/gap, 2)}%. Please review and fix.

                    Best,
                    CryptoDataBot"""
    sendEmail(subject, message, BACKEND_EMAIL)


# Initializes the Database
def main():
    db = pymysql.connect(SQL_IP,SQL_USER,SQL_PASSWORD,SQL_SCHEMA, autocommit = True)
    cursor = db.cursor()
    print("Database Initialized")
    gap = THRESHOLD * 60 / CADENCE_PER_MINUTE
    checkMetricsBeingTracked = f"""
        SELECT count(*)
        FROM UserCurrencyPairMetric WHERE deletedAt is null
        AND createdAt < DATE_SUB(CURRENT_TIMESTAMP, INTERVAL {gap} SECOND)
    """
    cursor.execute(checkMetricsBeingTracked)
    row = cursor.fetchone()
    countMetrics = row[0]
    if countMetrics > 0:
        getFreshnessQuery = """
            SELECT timestampdiff(SECOND, MAX(timestamp(queriedAt)), CURRENT_TIMESTAMP)
            FROM crypto.MetricValue;
            """
        cursor.execute(getFreshnessQuery)
        row = cursor.fetchone()
        difference = row[0]

        # 60 Seconds in a minute times the threshold which is how many periods we NEED to have always.
        if difference > gap:
            sendBackendDataPipelineAlert(difference, gap)

    db.close()
    print(f"--- Closed DB, Done --- {round(time.time() - start_time, 4)} seconds ---")


main()
