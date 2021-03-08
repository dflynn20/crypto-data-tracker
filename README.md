# Crypto Data Tracker
This Repo is the backend for an application for watching cryptocurrency metrics based on https://docs.cryptowat.ch/rest-api/.

Here is the entity relationship diagram for the MySQL Backend as a reference for the database architecture this application uses: https://drive.google.com/file/d/1_ltuClV3AReFugKyGAiPhEupvrrHWlke/view?usp=sharing

A couple of assumptions I will be making:
- That the User module is created prior to being able to login to system to add cryptocurrency pairs to the metric.
- Privacy for what users are using this Data Tracker for is not the highest concern, as the rank for different types of metrics will be compared and returned.

It consists of two different critical components to this application.

# 1. REST API built in Python using the Flask Framework
This is the crypto-client-api folder that is to be considered as a separate github repo.

From the front-end, this is how the client will interact with the backend.

In order to run it locally, you need to be within a Python 3.7 virtual environment with Flask installed and type in the command line:

flask run

Functions:

1. POST {{url}}/begin-tracking-metric

Request

Headers:
"Authorization": "S3CUR3K3Y"
"Content-Type": "application/json"

Body:
{
  "userId": 1,
  "market": "kraken",
  "pair": "btceur",
  "metric": "Volume"
}

If the authorization is correct and that user has yet to add that metric to his/her watchlist, the system will begin tracking the metric for that user.

2. GET {{url}}/graphs-of-tracked-metrics/:userId

Headers:
"Authorization": "S3CUR3K3Y"

If the authorization is correct and that user has tracked metrics, this will return all of the necessary information to plot the graphs of all of the metrics for that specific user.  This assumes a cacheing system on the frontend for ease of toggling between different metrics.  Also, the rank will be returned within the different metrics, compared to all similar metric types.

3. DELETE {{url}}/:userId/:market/:pair/:metric

Headers:
"Authorization": "S3CUR3K3Y"

If the authorization is correct and that user has that metric tracked, then it will remove it from that user's follow list.

# To Do for Production:
Configure the Gunicorn Flask Python 3.7 application as GKE Service and Ingress.
An example Dockerfile has been provided for this REST API.
After testing with K6 based on estimated load (or another load tester like WebLOAD / LoadNinja),
determine the Autoscale parameters for the GKE Services and Ingress.
Configure the Environment variables using the Config Map funcionality within the GKE container
for this specific service.

# Improvements
Implementing a rotating security key system for the api "Authorization" header (Ex: Okta).

Providing a list of the possible markets and pairs of currencies such that the frontend would not have to consult the cryptowatch API by itself for the checkboxes.

# 2. Python Script to upkeep the Data Backend
This is the cryptowatch-querying folder that is to be considered as a separate github repo.

The script (DONNY TO ADD) will run on a 1-minute cadence to query the cryptowatch rest-api, specifically the https://docs.cryptowat.ch/rest-api/markets/summary, which returns all of the metrics we could possibly want to track for the specified market pair. It then saves those values to the MySQL Backend so that it can be queried from the REST API.

Here are three added features:
- An example SendGrid API has been integrated to show how it is possible to send an alert when a metric exceeds 3X the value of its average in the past hour, to notify the user.
- Catching a KeyError which would use the SendGrid API to ping the responsible engineer notifying that the return value from the cryptowatch API had changed.
- If the entire script takes more than half of the time window it is supposed to be running at, it will also utilize the SendGrid API to ping the responsible engineer notifying that a throughput improvement is needed.


# To Do for Production:
Configure the Gunicorn Flask Python 3.7 application as GKE Workload.
An example Dockerfile has been provided for this Python Workload.
Configure the Environment variables using the Config Map funcionality within the GKE container
for this specific workload.
Continue to monitor the CPU / Memory usage to make sure that more resources are not needed.

# Improvements
It is always necessary to finish all of the necessary metrics prior to the minute finishing; thus,
threading would be needed at scale.
