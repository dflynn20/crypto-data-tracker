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

CADENCE_PER_MINUTE=int(os.environ.get('CADENCE_PER_MINUTE'))
HOURS_LOOKBACK=int(os.environ.get('HOURS_LOOKBACK'))
HOURS_FOR_ALERT=int(os.environ.get('HOURS_FOR_ALERT'))

ACCEPTABLE_THRESH_MISSING_ALERT=float(os.environ.get('ACCEPTABLE_THRESH_MISSING_ALERT'))
FACTOR_METRIC_THRESH_ALERT=int(os.environ.get('FACTOR_METRIC_THRESH_ALERT'))

BACKEND_THRESHOLD=float(os.environ.get('BACKEND_THRESHOLD'))
BACKEND_EMAIL=os.environ.get('BACKEND_EMAIL')



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


# This checks whether or not a value is above certain threshold (with enough data to validate the alert).
# These environment variables are to be configured by the engineers reponsible for upkeep of meeting product
# use cases for these alerts.
# Inputs: mySQLCursor, currencyPairMetricId, its current value
# Outputs: boolean if the alert is to be sent, metric's previous average to also include in the alert message
def checkAlert(cursor, cpmId, value):
    averageAlertingPeriod = f"""
        SELECT avg(value), count(*) FROM crypto.MetricValue
        WHERE queriedAt > DATE_SUB(CURRENT_TIMESTAMP, INTERVAL {HOURS_FOR_ALERT} HOUR)
    """
    try:
        cursor.execute(averageAlertingPeriod)
        scoutAlertData = cursor.fetchone()
        previousAverage, numRows = scoutAlertData[0], scoutAlertData[1]

        # 60 Minutes in an Hour, based on the environment variables setup in basis of
        # CADENCE_PER_MINUTE and HOURS_FOR_ALERT.
        expected = 60 * CADENCE_PER_MINUTE * HOURS_FOR_ALERT

        # Protecting against divide by zero errors in case the environment variables are configured poorly
        if expected > 0 and ((expected - numRows) / expected) < ACCEPTABLE_THRESH_MISSING_ALERT:
            if float(value) > FACTOR_METRIC_THRESH_ALERT * previousAverage:
                return True, previousAverage
        return False, 0
    except:
        print(f"Error within try segment of checkAlert function")
        return False, 0


# Sends the notice to the Backend engineer responsible for timeouts and performance improvements
def sendBackendTimeAlert(secondsElapsed, threshold):
    subject = "Notice: script query-cryptowatch nearing threshold"
    message =   f"""Hello,
                    query-cryptowatch.py took {secondsElapsed} seconds to run, which is above the configured threshold:
                    {round(threshold * 100,2)}% of the cadence time. If you are comfortable with this, feel free to ignore it or disable
                    the check.

                    Best,
                    CryptoDataBot"""
    sendEmail(subject, message, BACKEND_EMAIL)


# Inputs are the mySQLCursor, and the array of dictionary objects for the currencyPairMetrics with
# their current value as well as the previous value during the HOURS_FOR_ALERT lookback.
# Iterates through the needed email alerts, formats the messages, and calls the sendGrid wrapper
# for each necessary metric/user pair.
def sendNecessaryClientAlerts(cursor, alertingData):
    for metricDict in alertingData:
        cpmId, previousValue, value = alertingData['currencyPairMetricId'], alertingData['previousValue'], alertingData['currentValue']
        userMetricAlertingQuery = f"""
            SELECT DISTINCT u.email, u.firstName, u.lastName, mt.name,
            cpm.pair, cpm.market
            FROM crypto.UserCurrencyPairMetric ucpm
            JOIN crypto.User u on ucpm.userId = u.id
            JOIN crypto.CurrencyPairMetric cpm on cpm.id = ucpm.currencyPairMetricId
            JOIN crypto.MetricType mt on cpm.metricTypeId = mt.id
            WHERE ucpm.deletedAt is not null
            AND ucpm.currencyPairMetricId = {cpmId}
            AND u.email is not null
        """
        cursor.execute(userMetricAlertingQuery)
        userData = cursor.fetchall()
        for row in userData:
            userEmail, firstName, lastName, metric, pair, market = row[0], row[1], row[2], row[3], row[4], row[5]
            subject = f"Alert: {metric} for {pair} on {market}"
            message =   f"""Hello {firstName} {lastName},

                            I have been configured to tell you when any of your tracked metrics are above {FACTOR_METRIC_THRESH_ALERT}
                            times what they have been averaging in the past {HOURS_FOR_ALERT} hours.

                            This is the case for {metric} for {pair} on {market}, which just registered a value of {value} compared to
                            its previous average of {previousValue}, marking a growth of {round(100 * (value - previousValue) /previousValue, 2)}%.

                            I hope you find this information useful!

                            Best,
                            CryptoDataBot"""
            sendEmail(subject, message, userEmail)


# Initializes the Database
def main():
    db = pymysql.connect(SQL_IP,SQL_USER,SQL_PASSWORD,SQL_SCHEMA, autocommit = True)
    cursor = db.cursor()
    print("Database Initialized")

    # Gets all of the active metrics from the database that need to be tracked.
    getActiveMetricsQuery = """
        SELECT cpm.id, cpm.pair, cpm.market,
        mt.firstLevel, mt.secondLevel, mt.thirdLevel
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

    alertingData = []

    for row in currentMetrics:
        start_time_run_i = time.time()
        cpmId, pair, market, firstLevel, secondLevel, thirdLevel = row[0], row[1], row[2], row[3], row[4], row[5]

        # This is the query that takes the longest within this process. An improvement would be to thread
        # the different requests. It also might just be solved if the cryptowatch API is pinged from a
        # paid account as well...
        result = requests.get(f"https://api.cryptowat.ch/markets/{market}/{pair}/summary")

        # IMPROVEMENT HERE: seeing if the market pair is still valid. If it is not and returns a 400 more than a threshold
        # to be defined, this script should softdelete the UserCurrencyPairMetric for all (market, pairs) <=> users.

        data = result.json()

        if secondLevel == None:
            value = data["result"][firstLevel]
        elif thirdLevel == None:
            value = data["result"][firstLevel][secondLevel]
        else:
            value = data["result"][firstLevel][secondLevel][thirdLevel]


        # IMPROVEMENT HERE: Wrapping the read of the specific metric to catch possible KeyError's,
        # Send the backend an urgent email, and softdelete the UserCurrencyPairMetric.

        toSendAlert, previousValue = checkAlert(cursor, cpmId, value)
        if toSendAlert: alertingData.append({'currencyPairMetricId': cpmId, 'previousValue': previousValue, 'currentValue': value})
        insertionQuery = f"""
            INSERT INTO crypto.MetricValue (currencyPairMetricId, value, queriedAt)
            VALUES ({cpmId}, {value},
            '{pd.to_datetime(pd.Timestamp.today().replace(microsecond=0).replace(second=0))}');
        """
        cursor.execute(insertionQuery)
        print(f"--- Fetched One Value and Checked Alert --- {round(time.time() - start_time_run_i,4)} seconds ---")

    # Deletes every metric at once that is beyond the lookback that the app promises.
    cursor.execute(f"DELETE FROM crypto.MetricValue WHERE queriedAt < DATE_SUB(CURRENT_TIMESTAMP, INTERVAL {HOURS_LOOKBACK} HOUR)")

    secondsElapsed = round(time.time() - start_time, 4)
    print(f"--- Writing Script Over --- {secondsElapsed} seconds ---")

    if CADENCE_PER_MINUTE > 0 and secondsElapsed > BACKEND_THRESHOLD * (60 / CADENCE_PER_MINUTE):
        sendBackendTimeAlert(secondsElapsed, BACKEND_THRESHOLD)

    if len(alertingData) > 0:
        sendNecessaryClientAlerts(cursor, alertingData)

    db.close()
    print(f"--- Closed DB, Done --- {round(time.time() - start_time, 4)} seconds ---")


main()
