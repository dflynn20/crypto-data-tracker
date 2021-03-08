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
