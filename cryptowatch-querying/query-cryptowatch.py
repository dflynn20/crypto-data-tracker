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
