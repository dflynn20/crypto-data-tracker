from flask import Flask
from flask import request
from flask_cors import CORS
from setup import init
from middleware import validateAuthorization, checkParams
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
pool = Pool(host=SQL_IP, user=SQL_USER, password=SQL_PASSWORD, db=SQL_SCHEMA, autocommit=True, min_size=int(MIN_POOL_SIZE), max_size=int(MAX_POOL_SIZE))
pool.init()
print("Pool initialized")

# This returns the necessary objects to operate with the mySQL Pool.
def connectToMySQL():
    connection = pool.get_conn()
    cursor = connection.cursor()
    return connection, cursor, pool

# To be used for Debugging. Need to view the logs to see what happened.
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

# Error handler that will return the proper error message as well as release the db from the pool.
def returnErrorReleaseSQL(pool, db, errorMessage):
    pool.release(db)
    return json.dumps({"code":400, "msg": errorMessage}), 400

# This adds the specified metric, pair, and market to be tracked for the user.
def addToDataBaseForTracking(userId, market, pair, metric):
    if userId < 1:
        return json.dumps({"code":400, "msg": "Invalid UserId"}), 400
    else:
        db, cursor, pool = connectToMySQL()
        userValidatingQuery = f"SELECT id FROM crypto.User WHERE deletedAt is null AND id = {userId};"
        cursor.execute(userValidatingQuery)
        if len(cursor.fetchall()) < 1:
            return returnErrorReleaseSQL(pool, db, "Invalid UserId")

        metricValidatingQuery = f"SELECT mt.deletedAt, mt.id FROM crypto.MetricType mt WHERE mt.deletedAt is null AND mt.name = '{metric}';"
        cursor.execute(metricValidatingQuery)
        metricData = cursor.fetchall()
        if len(metricData) < 1:
            return returnErrorReleaseSQL(pool, db, "Invalid Metric")
        deletedAt, metricTypeId = metricData[0]['deletedAt'], metricData[0]['id']
        if deletedAt != None:
            return returnErrorReleaseSQL(pool, db, f"Metric was deleted at {deletedAt}")

        # TO DO
        # Add market and pair validation as well. I am assuming good behavior with these.

        # Counter is for Debugging
        try:
            failed = False
            shortCircuit = False
            counter = 0
            # Step 0
            check = f"""
            SELECT cpm.id, CASE WHEN ucpm.userId = {userId} THEN 1 ELSE 0 END as alreadyTracking
            FROM crypto.UserCurrencyPairMetric ucpm JOIN crypto.CurrencyPairMetric cpm
            ON ucpm.currencyPairMetricId = cpm.id
            WHERE ucpm.deletedAt is null
            AND cpm.market = '{market}'
            AND cpm.pair = '{pair}'
            AND cpm.metricTypeId = {metricTypeId}
            ORDER BY 2 DESC
            LIMIT 1
            """
            cursor.execute(check)
            pairMetricData = cursor.fetchall()

            counter += 1
            if len(pairMetricData) < 1:
                # Step 1
                insertionPairMetric = f"INSERT INTO crypto.CurrencyPairMetric (market, pair, metricTypeId) VALUES  ('{market}', '{pair}', {metricTypeId});"
                print(insertionPairMetric)
                cursor.execute(insertionPairMetric)
                currencyPairMetricId = cursor.lastrowid
                counter += 1
                # Step 2 declares currencyPairMetricId using the cursor Function
            else:
                currencyPairMetricId = pairMetricData[0]['id']
                alreadyTracking = pairMetricData[0]['alreadyTracking']
                if alreadyTracking == 1:
                    shortCircuit = True
                    return
                counter += 2
                # Step 3 declares currencyPairMetricId via first row
            userMetricRelationship = f"INSERT INTO crypto.UserCurrencyPairMetric (userId, currencyPairMetricId, createdAt) VALUES ({userId},{currencyPairMetricId}, now())"
            cursor.execute(userMetricRelationship)
        except:
            print(f"Error occurred during step: {counter}")
            failed = True
            pass
        finally:
            pool.release(db)
            if shortCircuit: return json.dumps({"code":200, "msg": "User already tracking that metric"}), 200
            if failed: return json.dumps({"code":400, "msg": f"Something went wrong {metric} for {pair} on {market} for this user."}), 400
            return json.dumps({"code":201, "msg": f"Successfully Added {metric} for {pair} on {market} for this user."}), 201


# This function returns the rank of the standard deviation using SQL
# to compare to other metrics of that type, on that market that are being tracked.
# It returns the numerator of the rank, and the denominator of the rank (being the total
# of such metrics).
def getRank(cursor, currencyPairMetricId, metricTypeId, market):
    rankNum, rankDenom = 0, 0
    rankQuery = f"""
    SELECT stddev(mv.value), cpm.id FROM
    crypto.MetricValue mv JOIN
    crypto.CurrencyPairMetric cpm
    ON mv.currencyPairMetricId = cpm.id
    WHERE cpm.metricTypeId = {metricTypeId}
    AND cpm.market = '{market}'
    GROUP BY 2
    ORDER BY 1 DESC
    """
    cursor.execute(rankQuery)
    rankData = cursor.fetchall()
    rowNum = 0
    for row in rankData:
        rowNum += 1
        if row['id'] == currencyPairMetricId: rankNum = rowNum
    rankDenom = rowNum
    return rankNum, rankDenom

# This function takes in a cursor object as well as the currencyPairMetricIds.
# It returns a Dictionary of Dictionaries.
# The key to the first level is the index for the allMetricData array corresponding to that
# specific CurrencyPairMetric. The Value is a Dictionary with the keys being:
# "times": X Array of the times that the metric was taken
# "values": Y Array of the value of that metric at the corresponding times
# such that the frontend can graph this data.
def getAllUserGraphData(cursor, allUserCurrencyPairMetrics, indexDict):
    # Special handling when there is only one metric vs multiple.
    whereString = f" in {tuple(allUserCurrencyPairMetrics)} " if len(allUserCurrencyPairMetrics) > 1 else f" = {allUserCurrencyPairMetrics[0]} "
    graphQuery = f"""
    SELECT queriedAt, value, currencyPairMetricId
    FROM crypto.MetricValue
    WHERE currencyPairMetricId {whereString}
    ORDER BY 3, 1 ASC
    """
    cursor.execute(graphQuery)
    graphData = cursor.fetchall()
    resultsDict = {}
    # Taking advantage of the SQL Ordering
    prevId, xAr, yAr = 0, [], []
    for row in graphData:
        currId = row['currencyPairMetricId']
        if prevId > 0 and currId != prevId:
            resultsDict[indexDict[prevId]] = {'times': xAr, 'values': yAr}
            xAr, yAr = [], []
        prevId = currId
        xAr.append(row['queriedAt'])
        yAr.append(row['value'])
    # Still have to add the last one as the trigger condition would not have been hit yet
    resultsDict[indexDict[prevId]] = {'times': xAr, 'values': yAr}
    return resultsDict

def getMetricsUserIsTracking(userId):
    db, cursor, pool = connectToMySQL()
    getMetrics = f"""
    SELECT cpm.*, mt.name as metricName
    FROM crypto.CurrencyPairMetric cpm
    JOIN crypto.MetricType mt on cpm.metricTypeId = mt.id
    WHERE cpm.id IN
    (
    SELECT DISTINCT ucpm.currencyPairMetricId
    FROM UserCurrencyPairMetric ucpm
    WHERE ucpm.deletedAt is null AND ucpm.userId = {userId}
    )
    """
    cursor.execute(getMetrics)
    metricData = cursor.fetchall()
    allMetricData = []
    try:
        allUserCurrencyPairMetrics, indexDict, index = [], {}, 0
        for row in metricData:
            currencyPairMetricId = row['id']
            allUserCurrencyPairMetrics.append(currencyPairMetricId)
            indexDict[currencyPairMetricId] = index
            rankNum, rankDenom = getRank(cursor, currencyPairMetricId, row['metricTypeId'], row['market'])
            rowDict = {'pair': row['pair'], 'market': row['market'], 'metric': row['metricName'],
                        'rankNum': rankNum, 'rankDenom': rankDenom, 'times': [], 'values': []}
            allMetricData.append(rowDict)
            index += 1
        graphDataDict = getAllUserGraphData(cursor, allUserCurrencyPairMetrics, indexDict)
        for k, v in graphDataDict.items():
            allMetricData[k]['times'] = v['times']
            allMetricData[k]['values'] = v['values']
        pool.release(db)
        return json.dumps({"code":200, "successfullyFinished": True, "data": allMetricData}, default = str), 200
    except:
        pool.release(db)
        print(f"Error occurred {len(allMetricData)} / {len(metricData)} of the way through the loop.")
        return json.dumps({"code":200, "successfullyFinished": False, "data": allMetricData}, default = str), 200

# Properly handles when the User is not in the database as well as when the metric is not valid.
def safeRemoveFromDatabase(userId, market, pair, metric):
    db, cursor, pool = connectToMySQL()
    userValidatingQuery = f"SELECT id FROM crypto.User WHERE deletedAt is null AND id = {userId};"
    cursor.execute(userValidatingQuery)
    if len(cursor.fetchall()) < 1:
        return returnErrorReleaseSQL(pool, db, "Invalid UserId")
    metricValidatingQuery = f"SELECT mt.id FROM crypto.MetricType mt WHERE mt.deletedAt is null AND mt.name = '{metric}';"
    cursor.execute(metricValidatingQuery)
    metricData = cursor.fetchall()
    if len(metricData) < 1:
        return returnErrorReleaseSQL(pool, db, "Invalid Metric")
    metricTypeId = metricData[0]['id']
    check = f"""
    SELECT ucpm.id
    FROM crypto.UserCurrencyPairMetric ucpm JOIN crypto.CurrencyPairMetric cpm
    ON ucpm.currencyPairMetricId = cpm.id
    WHERE ucpm.deletedAt is null
    AND cpm.market = '{market}'
    AND cpm.pair = '{pair}'
    AND cpm.metricTypeId = {metricTypeId}
    """
    cursor.execute(check)
    checkUserMetricData = cursor.fetchall()
    if len(checkUserMetricData) < 1:
        pool.release(db)
        return json.dumps({"code":200, "msg": f"User was not tracking {metric} for {pair} on {market} for this user."}), 200
    userCurrencyPairMetricId = checkUserMetricData[0]['id']
    cursor.execute(f"UPDATE crypto.UserCurrencyPairMetric SET deletedAt = now() where id = {userCurrencyPairMetricId}")
    return json.dumps({"code":200, "msg": f"Successfully ended tracking of {metric} for {pair} on {market} for this user."}), 200

# This function adds the
@app.route('/begin-tracking-metric', methods = ['POST'])
def addTrackingMetric():
    if validateAuthorization(request):
        data = request.json
        errorMessage, userId, market, pair, metric = checkParams(data)
        if len(errorMessage) > 0:
            return json.dumps({"code":400, "msg": errorMessage}), 400
        else:
            return addToDataBaseForTracking(userId, market, pair, metric)
    else:
        return json.dumps({"code":400, "msg": "Validation Not Correct"}), 400


# Takes in a userId and returns all of that users tracked metrics in a json object of
# the format:
#   {
#     successfullyFinished: true,
#     data: [{'pair': pairName, 'market': marketName, 'metric': metricName,
#             'rankNum': rankNumerator, 'rankDenom': rankDenominator,
#             'times': [], (AN ARRAY OF STRINGS, NEEDS TO BE CONVERTED ON FRONTEND TO GRAPH)
#              'values': []    (AN ARRAY OF floats) }, ...
#           ]
#   }
# IMPROVEMENT: Right now, if there is a user that is tracking many different metrics,
# this function will return all of 1440 pairs for each one of the users' metrics which might
# overload the cache for the frontend at scale.
@app.route('/graphs-of-tracked-metrics/<userId>', methods = ['GET'])
def getGraphsOfMetrics(userId):
    if validateAuthorization(request):
        return getMetricsUserIsTracking(userId)
    else:
        return json.dumps({"code":400, "msg": "Validation Not Correct"}), 400


# Takes in the path of a userId, market, pair, metric name and removes it from that
# users' tracked list.
@app.route('/remove/<userId>/<market>/<pair>/<metric>', methods = ['DELETE'])
def removeUserMetric(userId, market, pair, metric):
    if validateAuthorization(request):
        return safeRemoveFromDatabase(userId, market, pair, metric)
    else:
        return json.dumps({"code":400, "msg": "Validation Not Correct"}), 400


# Provides a HealthCheck route to make sure that the REST API is functioning correctly.
@app.route('/hc')
def healthcheck():
    return health.run()

@app.route('/info')
def data_info():
    return env_dump.run()

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0')
