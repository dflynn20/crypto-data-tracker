# Crypto Data Tracker
This Repo is the backend for an application for watching cryptocurrency metrics based on https://docs.cryptowat.ch/rest-api/.

Here is the entity relationship diagram for the MySQL Backend as a reference for the database architecture this application uses: https://drive.google.com/file/d/1_ltuClV3AReFugKyGAiPhEupvrrHWlke/view?usp=sharing

To ease the setup of the MySQL Backend, I included ```databaseSetup.sql``` which can be run within MySQL to set up the tables as well as insert the metrics from cryptowatch that are current as of 3/8/2021.

A couple of assumptions I made:
- That the User module is created prior to being able to login to system to add cryptocurrency pairs to the metric.
- Well-behaved inputs for both markets and pairs, as there is no validation on the system right now.
- Deployment will happen on the Google Cloud Platform (GKE specifically), although it should be cloud agnostic.

Choices I made:
- The database setup such that it is able to scale and handle many users and metrics, while avoiding redundancy. (IE: User A and User B are tracking the same metric, the system will only query that metric once and share the data).
- REST API has the singular responsibility of responding to the client's requests as fast as possible via querying the database through a pymysql connection pool, which makes scaling to multiple users easier.
- The script has the singular responsibility for querying the API to maintain data freshness, clearing (after the time period is up), and to carry out the alerting system.
- Sampling the data more rapidly would necessitate threading or performance boosts. The environment variable and the CRON scheduler would have to change to reflect the speedup. Currently, the bottleneck is the API request, so hopefully paying for the service would alleviate that in the future.
- I chose to return all of a user's tracked metrics in one request. This could cause a headache on the frontend of this application as there could be too much data if a user has 400+ metrics, each with 1440 date/float pairs to be graphed.
- User-Based/Personalized Dashboard System that assumes that the User is already created at the time of the creation of the first metric.
- Using Sendgrid for the Email alerting system, and I left a couple of TODOs regarding this in the script.

The application consists of two different critical components.

# 1. REST API built in Python using the Flask Framework
This is the crypto-client-api folder that is to be considered as a separate github repo.

From the front-end, this is how the client will interact with the backend.

In order to run it locally, you need to be within a Python 3.7 virtual environment with Flask installed and type in the command line:

```bash
pip install -r requirements.txt
flask run
```

Functions:

1. ```POST {{url}}/begin-tracking-metric```

Request

Headers:
```
{
  "Authorization": "S3CUR3K3Y"
  "Content-Type": "application/json"
}
```
Body:
```
{
  "userId": 1,
  "market": "kraken",
  "pair": "btceur",
  "metric": "Volume"
}
```

If the authorization is correct and that user has yet to add that metric to his/her watchlist, the system will begin tracking the metric for that user.

2. ```GET {{url}}/graphs-of-tracked-metrics/:userId```

Headers:
"Authorization": "S3CUR3K3Y"

If the authorization is correct and that user has tracked metrics, this will return all of the necessary information to plot the graphs of all of the metrics for that specific user.  This assumes a cacheing system on the frontend for ease of toggling between different metrics.  Also, the rank will be returned within the different metrics, compared to all similar metric types.

3. ```DELETE {{url}}/:userId/:market/:pair/:metric```

Headers:
"Authorization": "S3CUR3K3Y"

If the authorization is correct and that user has that metric tracked, then it will remove it from that user's follow list. Otherwise, it will throw an error that the user or metric are not registered.

# To Do for Production:
Configure the Gunicorn Flask Python 3.7 application as GKE Service and Ingress.
An example Dockerfile has been provided for this REST API.
After load testing with K6 based on estimated load (or another load tester like WebLOAD / LoadNinja), determine the Autoscale parameters for the GKE Services and Ingress and the min/max mySQL Pool Size.
Configure the Environment variables using the Config Map functionality within the GKE container for this specific service.

```
SQL_IP=localhost
SQL_USER=root
SQL_PASSWORD=PA$$W3RD
SQL_SCHEMA=crypto

MAX_POOL_SIZE= # TO BE DETERMINED AFTER LOAD TESTING
MIN_POOL_SIZE= # TO BE DETERMINED AFTER LOAD TESTING
AUTHORIZATION_TOKEN=S3CUR3K3Y
```

# Improvements
Implementing a rotating security key system for the api "Authorization" header (Ex: Okta).

Providing a list of the possible markets and pairs of currencies such that the frontend would not have to consult the cryptowatch API by itself for the checkboxes.

In addition to this, and related, a validation step of the pair with the market would be necessary for production deployment to handle errors.


# 2. Python Script to upkeep the Data Backend
This is the cryptowatch-querying folder that is to be considered as a separate github repo.

The script ```query-cryptowatch.py``` will run on a 1-minute cadence to query the cryptowatch rest-api, specifically the https://docs.cryptowat.ch/rest-api/markets/summary, which returns all of the metrics we could possibly want to track for the specified market pair. It then saves those values to the MySQL Backend so that it can be queried from the REST API.

To do a dry run to pull metrics that are already in the mySQL Database:
```bash
pip install -r requirements.txt
python query-cryptowatch.py
```

Here are two added features that are implemented (just need a SENDGRID_API_KEY):
- An example SendGrid API has been integrated to show how it is possible to send an alert when a metric exceeds 3X the value of its average in the past hour, to notify the user.
- If the entire script takes more than half of the time window it is supposed to be running at, it will also utilize the SendGrid API to ping the responsible engineer notifying that a throughput improvement is needed.

# To Do for Production:
Configure the Python 3.7 Script as GKE Workload with a crontab scheduler of ```* * * * *```, meaning every minute.
An example Dockerfile has been provided for this Python Workload.
Configure the Environment variables using the Config Map functionality within the GKE container for this specific workload.
```
SQL_IP=localhost
SQL_USER=root
SQL_PASSWORD=PA$$W3RD
SQL_SCHEMA=crypto

# The Script is robust to all three of these changes, although they must be integers.
# Cadence per minute has a dependency as well on the crontab scheduler for the job.
CADENCE_PER_MINUTE=1
HOURS_LOOKBACK=24
HOURS_FOR_ALERT=1

ACCEPTABLE_THRESH_MISSING_ALERT=0.1   # This is for the equivalent of 90% of the data being in the table
FACTOR_METRIC_THRESH_ALERT=3          # Initial Feature Request, is robust to changes here
BACKEND_THRESHOLD=0.5                 # Alerting when the code is beginning to be slower to monitor possible threading
BACKEND_EMAIL=gilfoyle@piedpiper.net  # Star Backend Engineer to be Notified in case of issues
SENDGRID_API_KEY=$3NDGR1DK3Y          # SENDGRID_API_KEY such that email alerts can be sent
```
Continue to monitor the CPU / Memory usage to make sure that more resources are not needed.

# Improvements
It is always necessary to finish all of the necessary metrics prior to the minute-cadence finishing; thus, threading would be needed as more metrics are added.

Two other features to be added:
- Catching a KeyError which would use the SendGrid API to ping the responsible engineer notifying that the return value from the cryptowatch API had changed.
- Alerting when the market/pair disappears or when the metric is no longer accessible in the same way that it has been. Within the ```main()```, there are clearly denoted sections for where those improvements belong.

# Clarification
Throughout the README, the code, and the architecture it says ```market``` when it really should be ```exchange``` based on the documentation from cryptowatch.
