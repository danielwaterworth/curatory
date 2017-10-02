from curatory.models import *
import itertools
import sortedcollections
import time

class PendingJob:
    def __init__(self, job_id, job):
        self.job_id = job_id
        self.job = job
        self.original_questions = list(job.questions())
        self.questions_by_id = dict(enumerate(self.original_questions))
        self.unanswered_question_times_by_id = sortedcollections.ValueSortedDict()
        for question_id in self.questions_by_id.keys():
            self.unanswered_question_times_by_id[question_id] = 0
        self.answers = {}

    def has_unanswered_questions(self):
        return len(self.unanswered_question_times_by_id) != 0

    def get_unanswered_question(self):
        question_id = self.unanswered_question_times_by_id.keys()[0]
        self.unanswered_question_times_by_id[question_id] = time.time()
        return self.job_id, question_id, self.questions_by_id[question_id]

    def submit_answer(self, question_id, answer):
        self.answers[question_id] = answer
        del self.unanswered_question_times_by_id[question_id]
        if not self.has_unanswered_questions():
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
