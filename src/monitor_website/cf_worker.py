import os
import random
import threading
import time
import requests
from hashlib import sha512
import monitor_website.models as models
import datetime
import pytz
# from selenium import webdriver
# import chromedriver_binary
from django.utils import timezone
from django.db.utils import OperationalError
from django.db.models import F


class WorkerError(IOError):
    """Base class for all worker errors"""

    def __init__(self, *args, **kwargs):
        self.comment = kwargs.pop('comment', '')
        super().__init__(*args, **kwargs)


class CodeforcesAPIError(WorkerError):
    """Problem with codeforces"""


class CodeforcesAccessError(WorkerError):
    """Problem with group access"""


class WorkerContestError(WorkerError):
    """Problem with contest initialization"""


class CodeforcesAPIManager:
    API_KEY = os.environ.get('WORKER_KEY')
    SECRET = os.environ.get('WORKER_SECRET')

    @classmethod
    def _get_apisig(cls, func_name, params: dict):
        a = sorted([(i, j) for i, j in params.items()])
        b = [f"{i}={j}" for i, j in a]
        rnd = random.randint(100000, 999999)
        s = f"{rnd}/{func_name}?{'&'.join(b)}#{cls.SECRET}"
        hsh = sha512(s.encode('ascii')).hexdigest()
        return f"{rnd}{hsh}"

    @classmethod
    def get_cf_query(cls, cid, query_name) -> dict:
        """Can raise RequestException or CodeforcesAPI"""
        params = {
            "apiKey": f"{cls.API_KEY}",
            "contestId": f"{cid}",
            "time": f"{round(time.time())}",
            "lang": "ru"
        }
        params["apiSig"] = cls._get_apisig(query_name, params)

        try:
            time.sleep(3)
            result = requests.get(f"https://codeforces.com/api/{query_name}", params)
            return result.json()
        except requests.exceptions.JSONDecodeError:
            raise CodeforcesAPIError(comment="Codeforces services unavailable")


class CodeforcesGroupManager:
    CF_USER = 'cmw'
    CF_PASS = os.environ.get('CF_PASS')

    @classmethod
    def check_group(cls, group_no):
        pass


class CodeforcesWorker:
    _instance = None

    class Log:
        def __init__(self, comment, style=""):
            self.time = timezone.now()
            self.comment = comment
            self.style = style

    @classmethod
    def log(cls, comment, style=""):
        CodeforcesWorker.worker_logs.append(cls.Log(comment, style))
        if len(CodeforcesWorker.worker_logs) > CodeforcesWorker.MAX_LOGS:
            CodeforcesWorker.worker_logs.pop(0)

    class Status:
        def __init__(self, contest=None, comment=""):
            self.time = timezone.now()
            self.comment = comment
            self.contest = contest

    @classmethod
    def set_status(cls, contest=None, comment=""):
        cls.current_status = cls.Status(contest, comment)

    current_status = Status()
    worker_logs = []

    MAX_LOGS = 500
    SUBMITS_QUERY = 'contest.status'
    PROBLEMS_QUERY = 'contest.standings'
    SEARCH_NEW_STEP = 27
    PING_DELTA = timezone.timedelta(minutes=20)
    BIG_UPDATE_DELTA = timezone.timedelta(hours=24)
    UPDATE_DELTA = timezone.timedelta(seconds=10)
    NAP_SECONDS = 10

    VERDICTS = {
        'FAILED': 'FAIL',
        'OK': 'OK',
        "COMPILATION_ERROR": 'CE',
        'RUNTIME_ERROR': 'RE',
        'WRONG_ANSWER': 'WA',
        'PRESENTATION_ERROR': 'PE',
        'TIME_LIMIT_EXCEEDED': 'TL',
        'MEMORY_LIMIT_EXCEEDED': 'ML',
        'IDLENESS_LIMIT_EXCEEDED': "IdL",
        'SECURITY_VIOLATED': 'SV',
        'CRASH': "crash",
        "SKIPPED": "skip",
        'TESTING': 'testing',
        'REJECTED': 'reject'
    }

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            cls._instance = object.__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        self._iters = 20

        if not hasattr(self, "_worker") or not self._worker.is_alive():
            self._worker = threading.Thread(target=self.start)
            self._worker.start()

            if self.current_status.contest is None:
                self.log('Воркер подняли из спячки.')
            else:
                self.log('Воркер подняли из метрвых.', 'danger')

    @staticmethod
    def _get_query_result(contest: models.Contest, query):
        status = CodeforcesAPIManager.get_cf_query(contest.cf_contest, query)
        if 'status' not in status or status['status'] != 'OK' or 'result' not in status:
            raise CodeforcesAPIError(comment=status.get('comment', 'Unknown problem'))
        return status['result']

    @staticmethod
    def _find_problem(contest, sumbission_desc):
        problem_q = contest.problem_set.filter(
            index=f"{sumbission_desc['problem']['index']}",
            name=f"{sumbission_desc['problem']['name']}",
            contest=contest
        )
        if problem_q.count() != 1:
            raise WorkerContestError()
        return problem_q.first()

    def _update_submission(self, contest: models.Contest, submission: dict):
        res = False
        for participant in submission['author']['members']:
            personality, _ = models.Personality.objects.get_or_create(
                monitor=contest.monitor,
                nickname=participant['handle'],
                defaults={
                    'is_blacklisted': True
                }
            )

            problem = self._find_problem(contest, submission)

            _, is_new = models.Submit.objects.update_or_create(
                index=f"{submission['id']}",
                problem=problem,
                personality=personality,
                defaults={
                    'submission_time': datetime.datetime.fromtimestamp(
                        submission['creationTimeSeconds'],
                        pytz.timezone('utc')
                    ),
                    'verdict':
                        'NA' if 'verdict' not in submission or submission['verdict'] not in self.VERDICTS
                        else self.VERDICTS[submission['verdict']],
                    'test_no': None if 'passedTestCount' not in submission else submission['passedTestCount'] + 1,
                    'is_contest': submission['author']['participantType'] == 'CONTESTANT',
                    'language': submission['programmingLanguage'],
                    'max_time': 0 if 'timeConsumedMillis' not in submission else submission['timeConsumedMillis']
                }
            )
            res |= is_new
        return res

    @staticmethod
    def _init_contest(contest: models.Contest, result: dict):
        contest.problem_set.all().delete()
        problems_d = result['problems']

        for problem_d in problems_d:
            models.Problem.objects.create(
                index=problem_d['index'],
                name=problem_d['name'],
                contest=contest,
                difficulty=None if 'rating' not in problem_d else problem_d['rating']
            )

        if not contest.human_name:
            contest.human_name = result['contest']['name']
        contest.save()

    def _process_contest(self, contest: models.Contest, full_update=False):
        try:
            self.set_status(contest, 'Подготовка выгрузки...')

            if contest.problem_set.count() == 0 or full_update:
                self.set_status(contest, 'Выгружаем задачи...')
                result = self._get_query_result(contest, self.PROBLEMS_QUERY)
                self.set_status(contest, 'Записываем задачи...')
                self._init_contest(contest, result)

            self.set_status(contest, 'Выгружаем посылки...')
            result = self._get_query_result(contest, self.SUBMITS_QUERY)

            start = max(0, len(result) - self.SEARCH_NEW_STEP)

            for s_ndx in range(0, len(result), self.SEARCH_NEW_STEP):
                self.set_status(contest, f'Проверяем {s_ndx + 1}/{len(result)}')
                if self._update_submission(contest, result[s_ndx]):
                    start = min(start, max(0, s_ndx - self.SEARCH_NEW_STEP))
                    break

            for i in range(start, len(result)):
                self.set_status(contest, f'Обновляем {i + 1}/{len(result)}')
                self._update_submission(contest, result[i])

        except CodeforcesAPIError as e:
            # TODO : call group cf api
            contest.set_error(e.comment)
            self.log(f'Проблема с контестом {contest.get_name()} ({contest.monitor.human_name}): {e.comment}', 'danger')
        except WorkerContestError:
            self._process_contest(contest, True)

    def start(self):
        while self._iters > 0:
            try:
                contests_q = models.Contest.objects.filter(
                    monitor__is_old=False,
                    error_text__isnull=True,
                    last_ping__gte=timezone.now() - self.PING_DELTA
                ).exclude(last_status_update__gte=timezone.now() - self.UPDATE_DELTA)

                if contests_q.exists():
                    contest = contests_q.earliest(F('last_status_update').desc(nulls_first=True))

                    self.log(f'Выбран контест "{contest.get_name()}" ({contest.monitor.human_name}) для обновления')
                    self._process_contest(contest)

                    contest.last_status_update = timezone.now()
                    self.set_status()
                    contest.save()
                else:
                    self.log(f'Воркер не нашел работы и пошел спать')
                    time.sleep(self.NAP_SECONDS)

            except OperationalError:
                self.log('База данных умерла', 'danger')
                if self.current_status.contest:
                    self.set_status(
                        self.current_status.contest,
                        'База данных не отвечает :(',
                    )

                time.sleep(self.NAP_SECONDS)
            except requests.exceptions.RequestException:
                self.log('Codeforces не доступен (как и интернет?)', 'danger')
                if self.current_status.contest:
                    self.set_status(
                        self.current_status.contest,
                        'Codeforces не отвечает :(',
                    )

                time.sleep(self.NAP_SECONDS)

            self._iters -= 1


def ping(monitor: models.Monitor):
    for contest in monitor.contest_set.all():
        contest.last_ping = timezone.now()
        contest.save()
    CodeforcesWorker()
