from collections import defaultdict

from .models import Monitor, Personality, Problem, Submit
from django.utils import timezone


class TableCell:
    def __init__(self):
        self._submits: list[Submit] = []
        self.first_success = 0

    def _clean_up(self):
        self._submits.sort()
        self.first_success = 0
        while self.first_success < len(self._submits) and self._submits[self.first_success].verdict != Submit.OK:
            self.first_success += 1

    def add_submit(self, submit: Submit):
        self._submits.append(submit)
        if len(self._submits) > 1 and self._submits[-2].submission_time > submit.submission_time:
            self._clean_up()
        elif self.first_success == len(self._submits) - 1 and submit.verdict != Submit.OK:
            self.first_success += 1

    def remove_until(self, datetime: timezone.datetime):
        while self._submits and self._submits[-1].submission_time > datetime:
            self._submits.pop()
        self.first_success = min(self.first_success, len(self._submits))

    def get_result(self) -> (int or None, Submit or None):
        if len(self._submits) == 0:
            return None, None
        elif self.first_success >= len(self._submits):
            return self.first_success, self._submits[-1]
        else:
            return self.first_success, self._submits[self.first_success]


class MonitorGenerator:

    _raw_tables: dict[Monitor, dict[(Personality, Problem), TableCell]] = defaultdict(lambda: defaultdict(TableCell))
    _last_updates: dict[Monitor, timezone.datetime] = defaultdict(lambda: timezone.make_aware(timezone.datetime.min))
    _last_big_updates: dict[Monitor, timezone.datetime] = defaultdict(lambda: timezone.make_aware(timezone.datetime.min))
    BIG_UPDATE_PENALTY = timezone.timedelta(minutes=15)

    @classmethod
    def __update_table(cls,
                       table: dict[(Personality, Problem), TableCell],
                       personalities: list[Personality],
                       problem_list: list[Problem],
                       from_time: timezone.datetime
                       ):

        for person in personalities:
            for problem in problem_list:
                table[(person, problem)].remove_until(from_time)

            query = person.submit_set.filter(submission_time__gt=from_time).order_by('submission_time')

            for submit in query.all():
                table[(person, submit.problem)].add_submit(submit)

    @classmethod
    def gen(cls, monitor: Monitor):
        problem_list = []
        for contest in monitor.contest_set.all():
            problem_list += list(contest.problem_set.all())
        personalities = monitor.personality_set.filter(is_blacklisted=False).all()
        table = cls._raw_tables[monitor]

        if cls._last_big_updates[monitor] + cls.BIG_UPDATE_PENALTY < timezone.now():
            cls.__update_table(table, personalities, problem_list, timezone.make_aware(timezone.datetime.min))
            cls._last_big_updates[monitor] = cls._last_updates[monitor] = timezone.now()
        else:
            cls.__update_table(table, personalities, problem_list, cls._last_updates[monitor])
            cls._last_updates[monitor] = timezone.now()

        result = []

        for person in personalities:
            # todo: rewrite this shit
            table_row = [0, 0, person, [], 0, 0]

            for problem in problem_list:
                count, submit = table[(person, problem)].get_result()
                if submit is None:
                    table_row[3].append(('', '#', None))
                else:
                    table_row[3].append((count, submit.get_cf_url(), submit))
                    if submit.verdict == submit.OK:
                        if not submit.is_contest:
                            table_row[5] += 1
                        table_row[4] += 1

            result.append(table_row)

        for r in result:
            r[0] = len([p for p in result if p[4] > r[4]]) + 1
            r[1] = r[0] - len([p for p in result if p[4] - p[5] > r[4] - r[5]]) + 1

        return problem_list, sorted(result, key=lambda x: x[:2])
