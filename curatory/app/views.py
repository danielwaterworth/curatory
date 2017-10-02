from curatory.app import app
from curatory.app.state import *
from flask import Response
from flask import abort
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
import collections
import flask
import itertools
import os
import re
import sortedcollections
import sys
import time

image_dir = os.path.expanduser(sys.argv[1])

def get_image(image_id):
    with open(os.path.join(image_dir, image_id + '.png'), 'rb') as fd:
        return fd.read()

jobs = JobCollection()

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/worker', methods=['GET'])
def worker():
    return render_template('worker.html')

@app.route('/get_question.json', methods=['POST'])
def get_question():
    job_id, question_id, question = jobs.get_unanswered_question()
    response = {
        'job_id': job_id,
        'question_id': question_id,
        'question': question.to_json_obj(),
    }
    return jsonify(**response)

@app.route('/image/<string:image_id>')
def image(image_id, methods=['GET']):
    img = get_image(image_id)
    return Response(img, mimetype='image/png')

@app.route('/job/<int:job_id>/question/<int:question_id>/submit_answer', methods=['POST'])
def answer(job_id, question_id):
    answer = Answer.from_json_obj(request.json)
    jobs.submit_answer(job_id, question_id, answer)
    return ''

@app.route('/submit_job', methods=['POST'])
def submit_job():
    job = Job.from_json_obj(request.json)
    job_id = jobs.submit_job(job)
    return jsonify(job_id=job_id)

@app.route('/job/<int:job_id>/result.json', methods=['GET'])
def job_result(job_id):
    return jsonify(jobs.get_result(job_id).to_json_obj())
