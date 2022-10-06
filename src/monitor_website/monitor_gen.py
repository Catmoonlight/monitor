from .models import Monitor


class MonitorGenerator:

    @classmethod
    def gen(cls, monitor: Monitor, is_authenticated):
        problem_list = []
        for contest in monitor.contest_set.all():
            problem_list += list(contest.problem_set.all())

        results = {}
        contest_solved = {}
        practiced = {}

        for person in monitor.personality_set.filter(is_blacklisted=False).all():
            results[person] = []
            contest_solved[person] = 0
            practiced[person] = 0

            d_c = {}

            for submit in person.submit_set.order_by('submission_time').all():
                if submit.problem not in d_c:
                    d_c[submit.problem] = ('', '#', None, 0)
                if d_c[submit.problem][0].startswith('+'):
                    continue

                c = d_c[submit.problem][-1]
                if submit.verdict == submit.OK:
                    d_c[submit.problem] = ('+' if c == 0 else f'+{c}',
                                           submit.get_cf_url() if is_authenticated else '#',
                                           submit, c)
                    if submit.is_contest:
                        contest_solved[person] += 1
                    else:
                        practiced[person] += 1
                else:
                    d_c[submit.problem] = (f'-{c + 1}', submit.get_cf_url() if is_authenticated else '#',
                                           submit, c + 1)

            for problem in problem_list:
                if problem in d_c:
                    results[person] += [d_c[problem]]
                else:
                    results[person] += [('', '#', None, 0)]

        personalities = list(results.items())

        places = sorted([(contest_solved[person] + practiced[person], contest_solved[person])
                         for person, _ in personalities])[::-1]
        contest_places = sorted([contest_solved[person] for person, _ in personalities])[::-1]

        personalities.sort(key=lambda x: (-contest_solved[x[0]] - practiced[x[0]], -contest_solved[x[0]]))
        for i in range(len(personalities)):
            person = personalities[i][0]
            index = places.index((contest_solved[person] + practiced[person], contest_solved[person])) + 1
            c_index = contest_places.index(contest_solved[person]) + 1
            personalities[i] = (index, c_index - index, person, personalities[i][1],
                                contest_solved[person] + practiced[person], practiced[person])

        return problem_list, personalities
