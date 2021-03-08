from flask import Flask
from flask import request
from flask_cors import CORS
from setup import init
from middleware import validate_authorization
from healthcheck import HealthCheck, EnvironmentDump
import numpy as np
from pymysqlpool.pool import Pool
import requests
import pymysql
import json
import time
from threading import Thread
from werkzeug.exceptions import HTTPException
import os


app = Flask(__name__)
CORS(app)
health = HealthCheck()
env_dump = EnvironmentDump()
init(health, env_dump)


# This section is for running the service locally.
if os.environ.get("SQL_IP") == None:
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv())


# This loads the configuration needed to beginning the pool for the mySQL database
SQL_IP=os.environ.get('SQL_IP')
SQL_USER=os.environ.get('SQL_USER')
SQL_PASSWORD=os.environ.get('SQL_PASSWORD')
SQL_SCHEMA=os.environ.get('SQL_SCHEMA')
MAX_POOL_SIZE=os.environ.get('MAX_POOL_SIZE')
MIN_POOL_SIZE=os.environ.get('MIN_POOL_SIZE')
pool = Pool(host=SQL_IP, user=SQL_USER, password=SQL_PASSWORD, db=SQL_SCHEMA, autocommit=True, min_size=MIN_POOL_SIZE, max_size=MAX_POOL_SIZE)
pool.init()
print("Pool initialized")


def connectToMySQL():
    connection = pool.get_conn()
    cursor = connection.cursor()
    return connection, cursor, pool

# To be used for Debugging during coding, not sure what it will eventually look like....
@app.errorhandler(Exception)
def handleException(e):
    print(e)
    return json.dumps({'success': 0, 'objects': [], 'errorHandler': 1})

@app.route('/')
def validate_token():
    if validateAuthorization(request):
        return 'Welcome to CryptoDataWatch Backend Microservice'
    else:
        return json.dumps({"code":400, "msg": "Validation Not Correct"}), 400

def returnErrorReleaseSQL(pool, db, errorMessage):
    pool.release(db)
    return json.dumps({"code":400, "msg": errorMessage}), 400

# This code assumes
def addToDataBaseForTracking(userId, market, pair, metric):
    if userId < 1:
        return json.dumps({"code":400, "msg": "Invalid UserId"}), 400
    else:
        db, cursor, pool = connectToMySQL()
        userValidatingQuery = f"SELECT * FROM crypto.User WHERE id = {userId};"
        cursor.execute(userValidatingQuery)
        if len(cursor.fetchall()) < 1:
            return returnErrorReleaseSQL(pool, db, "Invalid UserId")
        metricValidatingQuery = f"SELECT deletedAt, id FROM crypto.MetricType WHERE name = {metric};"
        cursor.execute(metricValidatingQuery)
        metricData = cursor.fetchall()
        if len(metricData) < 1:
            return returnErrorReleaseSQL(pool, db, "Invalid Metric")
        deletedAt, metricTypeId = metricData[0]['deletedAt'], metricData[0]['id']
        print(deletedAt, metricTypeId)
        if deletedAt != None:
            return returnErrorReleaseSQL(pool, db, f"Metric was deleted at {deletedAt}")
        # TO DO
        # Add market and pair validation as well. I am assuming good behavior with these.

        # Counter is for Debugging
        try:
            counter = 0
            # Step 0
            firstCheck = f"""
            SELECT cpm.id, CASE WHEN ucpm.userId = {userId} then 1 else 0 end as alreadyTracking
            FROM crypto.UserCurrencyPairMetric ucpm JOIN crypto.CurrencyPairMetric cpm
            ON ucpm.currencyPairMetricId = cpm.id
            WHERE ucpm.deletedAt is null
            AND cpm.market = {market}
            AND cpm.pair = {pair}
            AND cpm.metricTypeId = {metricTypeId}
            ORDER BY 2 DESC
            LIMIT 1
            """
            cursor.execute(firstCheck)
            pairMetricData = cursor.fetchall()
            counter += 1
            if len(pairMetricData) < 1:
                # Step 1
                insertionPairMetric = f"INSERT INTO crypto.CurrencyPairMetric (market, pair, metricTypeId) VALUES  ({market}, {pair}, {metricTypeId}) "
                cursor.execute(insertionPairMetric)
                currencyPairMetricId = cursor.lastrowid
                counter += 1
                # Step 2 declares currencyPairMetricId using the cursor Function
            else:
                currencyPairMetricId = pairMetricData[0]['id']
                alreadyTracking = pairMetricData[0]['alreadyTracking']
                if alreadyTracking == 1:
                    pool.release(db)
                    return json.dumps({"code":200, "msg": "User already tracking that metric"}), 200
                counter += 2
                # Step 3 declares currencyPairMetricId via first row
            userMetricRelationship = f"INSERT INTO crypto.UserCurrencyPairMetric (userId, currencyPairMetricId, createdAt) VALUES ({userId},{currencyPairMetricId}, now())"
            cursor.execute(userMetricRelationship)
        except:
            print(f"Error occurred during step: {counter}")
            pass
        finally:
            pool.release(db)
            return json.dumps({"code":201, "msg": f"Successfully Added {metric} for {pair} on {market} for this user."}), 201


@app.route('/begin-tracking-metric', methods = ['POST'])
def addTrackingMetric():
    if validateAuthorization(request):
        data = request.json
        errorMessage, userId, market, pair, metric = check_params(data)
        if len(errorString) > 0:
            return json.dumps({"code":400, "msg": errorMessage}), 400
        else:
            return addToDataBaseForTracking(userId, market, pair, metric)
    else:
        return json.dumps({"code":400, "msg": "Validation Not Correct"}), 400

@app.route('/graphs-of-tracked-metrics/<userId>', methods = ['GET'])
def getGraphsOfMetrics(userId):
    if validateAuthorization(request):
        userInDatabase, userHasMetrics, metrics = getMetricsUserIsTracking(userId)
        results = formatResults(userInDatabase, userHasMetrics, metrics)
        return results
    else:
        return json.dumps({"code":400, "msg": "Validation Not Correct"}), 400

@app.route('/remove/<userId>/<market>/<pair>/<metric>', methods = ['DELETE'])
def removeUserMetric(userId, market, pair, metric):
    if validateAuthorization(request):
        return safeRemoveFromDatabase(userId, market, pair, metric)
    else:
        return json.dumps({"code":400, "msg": "Validation Not Correct"}), 400

@app.route('/hc')
def healthcheck():
    return health.run()

@app.route('/info')
def data_info():
    return env_dump.run()

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0')
