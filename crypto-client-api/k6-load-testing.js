import http from 'k6/http';
import { check, group, sleep, fail } from 'k6';
import { Trend, Rate, Counter, Gauge } from 'k6/metrics';

export let RateOK = new Rate('Content OK');

export let options = {
  stages: [
    { duration: '30s', target: 5 },
    { duration: '45s', target: 10 },
    { duration: '1m', target: 20 }
  ],
  thresholds: {
    'http_req_duration': ['p(95)<3000', 'p(50)<950'],
    'Content OK': ['rate>0.80'],
  }
};



const BASE_URL = `${__ENV.BASE_URL}`;
const TOKEN = `${__ENV.AUTHORIZATION_TOKEN}`;

export default () => {
  let headers = {'Authorization': 'S3CUR3K3Y','Content-Type':	'application/json'};
  var query = queryReff[Math.floor((queryReff.length * Math.random()))];
  const indexLoc  = Math.floor((arrayLocation.length * Math.random()));
  const body = {
    "key": "value"
  };

  const response = http.post(`${BASE_URL}`, JSON.stringify(body), {headers: headers});
  const jsonResult = JSON.parse(response.body);

  RateOK.add(contentOK);
  sleep(1);
};
