import itertools
import math
import requests
import time
import os
from curatory.models import *

class Client:
    def __init__(self, url):
        self.url = url

    def submit_job(self, job):
        path = \
            "%s/submit_job" % self.url
        requests.post(
            path,
            json=job.to_json_obj(),
        ).raise_for_status()
