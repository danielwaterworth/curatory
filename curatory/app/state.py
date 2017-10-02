from curatory.models import *
import itertools
import sortedcollections
import sqlite3
import time
import contextlib

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

class MemJobCollection:
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

class SQLJobCollection:
    def __init__(self, filename):
        self.filename = filename
        self.initialize_db()

    def initialize_db(self):
        with self.cursor() as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id INTEGER PRIMARY KEY,
                    job_json STRING
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS results (
                    job_id INTEGER PRIMARY KEY,
                    result_json STRING,
                    FOREIGN KEY(job_id) REFERENCES jobs(job_id)
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS questions (
                    question_id INTEGER PRIMARY KEY,
                    job_id INTEGER,
                    question_json STRING,
                    FOREIGN KEY(job_id) REFERENCES jobs(job_id)
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pending_questions (
                    question_id INTEGER PRIMARY KEY,
                    job_id INTEGER,
                    last_sent_time INTEGER,
                    FOREIGN KEY(job_id) REFERENCES jobs(job_id),
                    FOREIGN KEY(question_id) REFERENCES questions(question_id)
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS answers (
                    answer_id INTEGER PRIMARY KEY,
                    job_id INTEGER,
                    question_id INTEGER,
                    answer_json STRING,
                    FOREIGN KEY(question_id) REFERENCES questions(question_id)
                )
            ''')


    @contextlib.contextmanager
    def cursor(self):
        with sqlite3.connect(self.filename) as conn:
            with contextlib.closing(conn.cursor()) as cur:
                yield cur

    def submit_job(self, job):
        with self.cursor() as cursor:
            cursor.execute(
                'INSERT INTO jobs VALUES (?, ?)',
                (None, job.to_json_string())
            )
            job_id = cursor.lastrowid
            for question in job.questions():
                cursor.execute(
                    'INSERT INTO questions VALUES (?, ?, ?)',
                    (None, job_id, question.to_json_string())
                )
                question_id = cursor.lastrowid
                cursor.execute(
                    'INSERT INTO pending_questions VALUES (?, ?, ?)',
                    (question_id, job_id, 0)
                )

    def get_result(self, job_id):
        with self.cursor() as cursor:
            cursor.execute('SELECT result_json FROM jobs WHERE (job_id=?)', job_id)
            return Result.from_json_string(cursor.fetchone())

    def get_unanswered_question(self):
        with self.cursor() as cursor:
            t = int(time.time())
            cursor.execute(
                'SELECT question_id from pending_questions ORDER BY last_sent_time ASC, question_id ASC'
            )
            question_id = cursor.fetchone()[0]
            cursor.execute(
                'UPDATE pending_questions SET last_sent_time=? where question_id=?',
                (t, question_id),
            )
            cursor.execute(
                'SELECT job_id, question_json FROM questions WHERE question_id=?',
                (question_id,),
            )
            job_id, question_json = cursor.fetchone()
            question = Question.from_json_string(question_json)
            return job_id, question_id, question

    def submit_answer(self, job_id, question_id, answer):
        with self.cursor() as cursor:
            cursor.execute(
                'SELECT job_id FROM questions WHERE question_id=?',
                (question_id,),
            )
            job_job_id = cursor.fetchone()[0]
            assert job_job_id == job_id
            cursor.execute(
                'INSERT INTO answers VALUES (?, ?, ?, ?)',
                (None, job_id, question_id, answer.to_json_string()),
            )
            cursor.execute(
                'DELETE FROM pending_questions WHERE question_id=?',
                (question_id,)
            )
            cursor.execute(
                'SELECT count(*) from pending_questions where job_id=?',
                (job_id,)
            )
            n = cursor.fetchone()[0]
            print('done')
