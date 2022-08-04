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
            print("Worker, wake up!")

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
        return result.json()

    def _try_return_result(self, contest: models.Contest, query):
        status = self._get_cf_query(contest.cf_contest, query)
        contest.last_status_update = timezone.now()

        if 'status' not in status or status['status'] != 'OK':
            print(f'result of {query} query failed because {status["comment"]}')

            if 'status' in status and status['status'] == 'C':
                contest.last_comment = status['comment']
                contest.save()
                return None

            if 'comment' in status:
                contest.set_error(status['comment'])
            else:
                contest.set_error('Неизвестная проблема')
            return None

        contest.last_comment = ''
        contest.has_errors = False
        print(f'result of {query} query completed')
        contest.save()

        return status['result']

    def _try_find_problem(self, contest, problemset, sumbission_desc):
        problem_q = problemset.filter(
            index=f"{sumbission_desc['problem']['index']}",
            name=f"{sumbission_desc['problem']['name']}",
            contest=contest
        )
        if problem_q.count() != 1:
            contest.last_comment = f"Задача {sumbission_desc['problem']['name']} создана с ошибками."
            contest.has_errors = True
            print(f'problems with task {sumbission_desc["problem"]["name"]} query completed')
            contest.save()
            return None

        return problem_q.first()

    def _update_contest(self, contest: models.Contest):
        result = self._try_return_result(contest, 'contest.status')
        if result is None:
            return
        problems = contest.problem_set.all()

        for submission in result:
            problem = self._try_find_problem(contest, problems, submission)
            if problem is None:
                return

            for participant in submission['author']['members']:
                personality, _ = models.Personality.objects.get_or_create(
                    monitor=contest.monitor,
                    nickname=participant['handle'],
                    defaults={
                        'is_blacklisted': contest.monitor.default_ghosts
                    }
                )

                models.Submit.objects.update_or_create(
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
        print('Done!\n')

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
        print('Done!\n')

    def start(self):
        while self._iters > 0:
            try:
                contests_q = models.Contest.objects.filter(monitor__is_old=False)
                if contests_q.filter(status=models.Contest.FRESH).exists():
                    contest = contests_q.filter(status=models.Contest.FRESH).first()
                    print(f"Init... {contest.human_name}")
                    self._init_contest(contest)
                elif contests_q.filter(status=models.Contest.NORMAL).exists():
                    normals = contests_q.filter(status=models.Contest.NORMAL)
                    contest = normals.filter(last_status_update__isnull=True).first() \
                        if normals.filter(last_status_update__isnull=True).exists() \
                        else normals.order_by('last_status_update').first()
                    print(f"Update... {contest.human_name}")
                    self._update_contest(contest)
                else:
                    print('relax')
            except OperationalError:
                print('Fuck! DB died :(')
            time.sleep(3)
            self._iters -= 1
