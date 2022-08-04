import django.utils.timezone as tz
from django.db import models
from django.urls import reverse


class Monitor(models.Model):
    group = models.CharField(max_length=20, blank=True, verbose_name="Код группы")
    human_name = models.CharField(max_length=50, blank=True)
    is_old = models.BooleanField(default=False)
    is_hidden = models.BooleanField(default=True)
    default_ghosts = models.BooleanField(default=True)

    def get_absolute_url(self):
        return reverse('main:monitor', kwargs={"monitor_id": self.pk})

    def last_update(self):
        mn = None
        for contest in self.contest_set.all():
            if contest.last_status_update is None:
                return None
            if mn is None:
                mn = contest.last_status_update
            mn = min(mn, contest.last_status_update)
        return mn


class Personality(models.Model):
    monitor = models.ForeignKey(Monitor, on_delete=models.CASCADE)
    nickname = models.CharField(max_length=50)
    real_name = models.CharField(max_length=50, blank=True)
    is_blacklisted = models.BooleanField(default=False)

    def get_name(self):
        name = f"{self.real_name} ({self.nickname})" if self.real_name else f"{self.nickname}"
        if self.is_blacklisted:
            return f"🚫 {name}"
        return name

    def solved(self):
        contests = self.monitor.contest_set.all()
        submits = self.submit_set.filter(verdict=Submit.OK, problem__contest__in=contests)
        return len(set(submit.problem for submit in submits))

    def practiced(self):
        contests = self.monitor.contest_set.all()
        submits = self.submit_set.filter(verdict=Submit.OK, is_contest=False, problem__contest__in=contests)
        return len(set(submit.problem for submit in submits))


class Problem(models.Model):
    index = models.CharField("Номер в контесте", max_length=10, blank=True)
    name = models.TextField("Название задачи", blank=True)
    desc = models.TextField("Короткое описание", blank=True)  # no functional
    contest = models.ForeignKey("Contest", on_delete=models.CASCADE, verbose_name="Контест")
    is_analysed = models.BooleanField('Разобрано?', default=False)  # no functional

    def get_cf_url(self):
        return f"https://codeforces.com/group/{self.contest.monitor.group}/contest/{self.contest.cf_contest}/problem/{self.index}"


class Submit(models.Model):
    # rewrite to unique ??
    index = models.CharField("Индекс", max_length=20)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    personality = models.ForeignKey(Personality, on_delete=models.CASCADE)
    submission_time = models.DateTimeField("Дата отправления")
    is_contest = models.BooleanField("Сдано на контесте?")

    OK = "OK"
    NOT_OK = "NOT_OK"

    verdict = models.CharField(
        max_length=10,
        choices=(
            (OK, "OK"),
            (NOT_OK, "Не зачтено"),
        )
    )

    def get_cf_url(self):
        return f"https://codeforces.com/group/{self.problem.contest.monitor.group}/contest/{self.problem.contest.cf_contest}/submission/{self.index}"


class Contest(models.Model):
    cf_contest = models.CharField(max_length=20, verbose_name="Номер контеста")
    human_name = models.TextField(blank=True)
    monitor = models.ForeignKey(Monitor, on_delete=models.CASCADE)
    last_status_update = models.DateTimeField(null=True)
    last_comment = models.TextField(blank=True)

    FRESH = 'FRESH'
    NORMAL = 'OK'
    ERROR = 'ERROR'

    status = models.CharField(
        max_length=10,
        choices=(
            (FRESH, "Только что создан"),
            (NORMAL, "OK"),
            (ERROR, "Ошибка!")
        ),
        default=FRESH
    )

    def get_name(self):
        if self.human_name:
            return f"{self.human_name}"
        return f"No. {self.cf_contest}"

    def get_cf_url(self):
        return f"https://codeforces.com/group/{self.monitor.group}/contest/{self.cf_contest}"

    def set_error(self, comment):
        self.status = self.ERROR
        self.last_comment = comment
        self.save()

