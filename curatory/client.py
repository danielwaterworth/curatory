import itertools
import math
import requests
import time
import os

class Client:
    def __init__(self, url):
        self.url = url

    def submit_job(self, job):
        path = \
            "%s/submit_job" % self.url
        requests.post(
            path,
            json=job.to_json(),
        ).raise_for_status()

class MutuallyExclusiveLabelJob:
    def __init__(self, images, label_type, labels):
        self.images = images
        self.label_type = label_type
        self.labels = labels

    def to_json(self):
        return {
            'type': 'MutuallyExclusiveLabelJob',
            'images': self.images,
            'label_type': self.label_type,
            'labels': self.labels,
        }

class PickLocationJob:
    def __init__(self, images, label_type):
        self.images = images
        self.label_type = label_type

    def to_json(self):
        return {
            'type': 'PickLocationJob',
            'images': self.images,
            'label_type': self.label_type,
        }
