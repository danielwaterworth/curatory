from curatory.app import app
import flask
from flask import Response
from flask import abort
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
import collections
import itertools
import sys
import os
import re

image_dir = os.path.expanduser(sys.argv[1])

def get_image(image_id):
    with open(os.path.join(image_dir, image_id + '.png'), 'rb') as fd:
        return fd.read()

def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]

class PendingJob:
    def __init__(self, job_id, job):
        self.job_id = job_id
        self.job = job
        self.original_questions = list(job.questions())
        self.questions = list(enumerate(self.original_questions))
        self.answers = {}

    def has_unanswered_questions(self):
        return len(self.questions) != 0

    def get_unanswered_question(self):
        question_id, question = self.questions.pop()
        return self.job_id, question_id, question

    def submit_answer(self, question_id, answer):
        self.answers[question_id] = answer
        if len(self.answers) == len(self.original_questions):
            answers = map(lambda x: x[1], sorted(self.answers.items()))
            return self.job.collate_answers(self.original_questions, answers)

class JobCollection:
    def __init__(self):
        self.results = {}
        self.job_ids = itertools.count()
        self.pending_jobs = []

    def submit_job(self, job):
        job_id = next(self.job_ids)
        self.pending_jobs.append(PendingJob(job_id, job))
        return job_id

    def get_result(self, job_id):
        return self.results[job_id]

    def get_unanswered_question(self):
        for pending_job in self.pending_jobs:
            if pending_job.has_unanswered_questions():
                return pending_job.get_unanswered_question()
        raise Exception("No unanswered questions")

    def submit_answer(self, job_id, question_id, answer):
        for pending_job in self.pending_jobs:
            if pending_job.job_id == job_id:
                result = pending_job.submit_answer(question_id, answer)
                if result:
                    self.pending_jobs.remove(pending_job)
                    self.results[job_id] = result
                return None
        raise Exception("No such job")

class Job:
    @classmethod
    def from_json_obj(cls, obj):
        if obj['type'] == 'MutuallyExclusiveLabelJob':
            return \
                MutuallyExclusiveLabelJob(
                    obj['label_type'],
                    obj['images'],
                    obj['labels'],
                )
        elif obj['type'] == 'AuditLabelsJob':
            return \
                AuditLabelsJob(
                    obj['label_type'],
                    obj['images'],
                    obj['labels'],
                )
        else:
            raise TypeError()

class MutuallyExclusiveLabelJob(Job):
    def __init__(self, label_type, images, labels):
        self.label_type = label_type
        self.images = images
        self.labels = labels

    def questions(self):
        for image in self.images:
            yield LabelImageQuestion(self.label_type, image, self.labels)

    def collate_answers(self, questions, answers):
        results = {}
        for question, answer in zip(questions, answers):
            results[question.image] = answer.label
        return MutuallyExclusiveLabelResult(results)

class AuditLabelsJob(Job):
    def __init__(self, label_type, images, labels):
        self.label_type = label_type
        self.images = images
        self.labels = labels

    def questions(self):
        groups = {}
        for image, label in zip(self.images, self.labels):
            groups[label] = groups.get(label, [])
            groups[label].append(image)
        for label, group in groups.items():
            for chunk in chunks(25, group):
                yield AuditLabelQuestion(self.label_type, label, chunk)

    def collate_answers(self, questions, answers):
        incorrect_images = set()
        for question, answer in zip(questions, answers):
            incorrect_images |= set(answer.incorrect_images)
        return AuditLabelsResult(list(incorrect_images))

class Question:
    pass

class LabelImageQuestion(Question):
    def __init__(self, label_type, image, labels):
        self.label_type = label_type
        self.image = image
        self.labels = labels

    def to_json_obj(self):
        return {
            'type': 'LabelImageQuestion',
            'label_type': self.label_type,
            'image': self.image,
            'labels': self.labels,
        }

class AuditLabelQuestion(Question):
    def __init__(self, label_type, label, images):
        self.label_type = label_type
        self.label = label
        self.images = images

    def to_json_obj(self):
        return {
            'type': 'AuditLabelQuestion',
            'label_type': self.label_type,
            'label': self.label,
            'images': self.images,
        }

class Answer:
    @classmethod
    def from_json_obj(cls, obj):
        if obj['type'] == 'LabelAnswer':
            return LabelAnswer(obj['label'])
        elif obj['type'] == 'AuditAnswer':
            return AuditAnswer(obj['incorrect_images'])
        else:
            raise TypeError()

class LabelAnswer(Answer):
    def __init__(self, label):
        self.label = label

class AuditAnswer(Answer):
    def __init__(self, incorrect_images):
        self.incorrect_images = incorrect_images

class Result:
    pass

class MutuallyExclusiveLabelResult(Result):
    def __init__(self, labels):
        self.labels = labels

    def to_json_obj(self):
        return {
            'type': 'MutuallyExclusiveLabelResult',
            'labels': self.labels,
        }

class AuditLabelsResult(Result):
    def __init__(self, incorrect_images):
        self.incorrect_images = incorrect_images

    def to_json_obj(self):
        return {
            'type': 'AuditLabelsResult',
            'incorrect_images': self.incorrect_images,
        }

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
