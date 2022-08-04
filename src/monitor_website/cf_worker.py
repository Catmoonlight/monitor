import os
import random
import threading
import time
import requests
from hashlib import sha512
import monitor_website.models as models
import datetime
import pytz
from django.utils import timezone
from django.db.utils import OperationalError


class CodeforcesWorker:
    _instance = None

    class Log:
        def __init__(self, comment, style=""):
            self.time = timezone.now()
            self.comment = comment
            self.style = style
            CodeforcesWorker.logs.append(self)
            if len(CodeforcesWorker.logs) > CodeforcesWorker.MAX_LOGS:
                CodeforcesWorker.logs.pop(0)

    class Status:
        def __init__(self, contest=None, comment="", style="", percent=100):
            self.time = timezone.now()
            self.comment = comment
            self.contest = contest
            self.style = style
            self.percent = percent

    MAX_LOGS = 1000
    logs = []
    current_status = Status()

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            cls._instance = object.__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        self._iters = 10
        self.apiKey = os.environ.get('WORKER_KEY')
        self.secret = os.environ.get('WORKER_SECRET')
        if not hasattr(self, "_worker") or not self._worker.is_alive():
            self._worker = threading.Thread(target=self.start)
            self._worker.start()
            self.Log('Воркер поднят из мертвых.')

    def _get_apisig(self, func_name, params: dict):
        a = sorted([(i, j) for i, j in params.items()])
        b = [f"{i}={j}" for i, j in a]
        rnd = random.randint(100000, 999999)
        s = f"{rnd}/{func_name}?{'&'.join(b)}#{self.secret}"
        hsh = sha512(s.encode('ascii')).hexdigest()
        return f"{rnd}{hsh}"

    def _get_cf_query(self, cid, query_name) -> dict:
        params = {
            "apiKey": f"{self.apiKey}",
            "contestId": f"{cid}",
            "time": f"{round(time.time())}",
            "lang": "ru"
        }
        params["apiSig"] = self._get_apisig(query_name, params)

        try:
            result = requests.get(f"https://codeforces.com/api/{query_name}", params)
        except requests.exceptions.RequestException:
            return {'status': 'C', 'comment': 'Проблема с соединением с codeforces'}
        try:
            js = result.json()
            return js
        except requests.exceptions.RequestsJSONDecodeError:
            self.Log(f"Не хочет превращаться в json: {result.content}", 'danger')
            return {'status': 'C', 'comment': 'Непонятная проблема с json'}

    def _try_return_result(self, contest: models.Contest, query):
        status = self._get_cf_query(contest.cf_contest, query)

        if 'status' not in status or status['status'] != 'OK':
            if 'comment' not in status:
                status['comment'] = "Неизвестная проблема"

            contest.set_error(status['comment'])
            self.Log(f'Метод {query} для контеста {contest.human_name} не сработал: {status["comment"]}')
            return None

        # contest.last_comment = ''
        # contest.last_status_update = timezone.now()
        # contest.has_errors = False
        # contest.save()

        return status['result']

    def _try_find_problem(self, contest, problemset, sumbission_desc):
        problem_q = problemset.filter(
            index=f"{sumbission_desc['problem']['index']}",
            name=f"{sumbission_desc['problem']['name']}",
            contest=contest
        )
        if problem_q.count() != 1:
            contest.set_error(f"Задача {sumbission_desc['problem']['name']} создана с ошибками.")
            self.Log(f'Ошибка в поиске проблемы {sumbission_desc["problem"]["name"]}', 'danger')
            return None

        return problem_q.first()

    def _update_contest(self, contest: models.Contest):
        result = self._try_return_result(contest, 'contest.status')
        if result is None:
            return
        problems = contest.problem_set.all()

        self.Log(f'Найдено {len(result)} посылок для обновления')
        new = 0
        for index, submission in enumerate(result):
            problem = self._try_find_problem(contest, problems, submission)
            if problem is None:
                return

            for participant in submission['author']['members']:
                personality, _ = models.Personality.objects.get_or_create(
                    monitor=contest.monitor,
                    nickname=participant['handle'],
                    defaults={
                        'is_blacklisted': True
                    }
                )

                _, is_new = models.Submit.objects.update_or_create(
                    index=f"{submission['id']}",
                    problem=problem,
                    defaults={
                        'personality': personality,
                        'submission_time': datetime.datetime.fromtimestamp(
                            submission['creationTimeSeconds'],
                            pytz.timezone('utc')
                        ),
                        'verdict': 'TESTING' if 'verdict' not in submission else (
                            submission['verdict'] if submission['verdict'] in ['OK', 'TESTING'] else 'NOT_OK'),
                        'is_contest': submission['author']['participantType'] == 'CONTESTANT'
                    }
                )
                if is_new:
                    new += 1
            if (index + 1) % 250 == 0:
                self.Log(f'Обновлено {index + 1}/{len(result)} посылок')

        contest.last_status_update = timezone.now()
        contest.save()

        self.Log(f'Обновление "{contest.human_name}" ({contest.monitor.human_name}) завершено! Новых посылок: {new}')

    def _init_contest(self, contest: models.Contest):
        result = self._try_return_result(contest, 'contest.standings')
        if result is None:
            return

        contest.problem_set.all().delete()
        problems_d = result['problems']
        for problem_d in problems_d:
            models.Problem.objects.create(
                index=problem_d['index'],
                name=problem_d['name'],
                contest=contest
            )

        if not contest.human_name:
            contest.human_name = result['contest']['name']

        contest.status = contest.NORMAL
        contest.last_status_update = None
        contest.last_comment = ''
        contest.save()

        self.Log(f'Контест {contest.get_name()} инициализирован, найдено {len(contest.problem_set.all())} задач')

    def start(self):
        while self._iters > 0:
            try:
                contests_q = models.Contest.objects.filter(monitor__is_old=False)
                if contests_q.filter(status=models.Contest.FRESH).exists():
                    contest = contests_q.filter(status=models.Contest.FRESH).first()
                    self.Log(f'Найден контест "{contest.get_name()}" для инициализации')
                    self._init_contest(contest)
                elif contests_q.filter(status=models.Contest.NORMAL).exists():
                    normals = contests_q.filter(status=models.Contest.NORMAL)
                    contest = normals.filter(last_status_update__isnull=True).first() \
                        if normals.filter(last_status_update__isnull=True).exists() \
                        else normals.order_by('last_status_update').first()
                    self.Log(f'Решено обновить контест "{contest.get_name()}" ({contest.monitor.human_name})')
                    self._update_contest(contest)
                else:
                    print('relax')
            except OperationalError:
                self.Log('База данных умерла', 'danger')
            time.sleep(3)
            self._iters -= 1
