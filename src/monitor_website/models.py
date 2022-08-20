import django.utils.timezone as tz
from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User


class Monitor(models.Model):
    group = models.CharField(max_length=20, blank=True, verbose_name="Код группы")
    human_name = models.CharField(max_length=50, blank=True)
    is_old = models.BooleanField(default=False)
    is_hidden = models.BooleanField(default=True)
    index = models.IntegerField(null=True)

    class Meta:
        ordering = ['index']

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

    def save(self, *args, **kwargs):
        super(Monitor, self).save(*args, **kwargs)
        if self.index is None:
            self.index = self.pk
            super(Monitor, self).save(*args, **kwargs)


    def has_errors(self):
        return self.contest_set.filter(error_text__isnull=False).exists()


class Personality(models.Model):
    monitor = models.ForeignKey(Monitor, on_delete=models.CASCADE)
    nickname = models.CharField(max_length=50)
    real_name = models.CharField(max_length=50, blank=True)
    is_blacklisted = models.BooleanField(default=False)

    class Meta:
        unique_together = ['monitor', 'nickname']

    def get_name(self):
        name = f"{self.real_name} ({self.nickname})" if self.real_name else f"{self.nickname}"
        if self.is_blacklisted:
            return f"🚫 {name}"
        return name


class Problem(models.Model):
    index = models.CharField("Номер в контесте", max_length=10, blank=True)
    name = models.TextField("Название задачи", blank=True)
    desc = models.TextField("Короткое описание", blank=True)  # no functional
    contest = models.ForeignKey("Contest", on_delete=models.CASCADE, verbose_name="Контест")
    is_analysed = models.BooleanField('Разобрано?', default=False)  # no functional
    difficulty = models.IntegerField("Сложность", null=True)

    class Meta:
        ordering = ['index']

    def get_cf_url(self):
        return f"https://codeforces.com/group/{self.contest.monitor.group}/contest/{self.contest.cf_contest}/problem/{self.index}"


class Submit(models.Model):
    index = models.CharField("Индекс", max_length=20)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    personality = models.ForeignKey(Personality, on_delete=models.CASCADE)
    submission_time = models.DateTimeField("Дата отправления")
    is_contest = models.BooleanField("Сдано на контесте?")
    verdict = models.CharField(max_length=20)
    test_no = models.IntegerField(null=True)
    language = models.CharField(max_length=50, blank=True)
    max_time = models.IntegerField(null=True)

    OK = "OK"

    def get_cf_url(self):
        return f"https://codeforces.com/group/{self.problem.contest.monitor.group}/contest/{self.problem.contest.cf_contest}/submission/{self.index}"


class Contest(models.Model):
    index = models.IntegerField(null=True)
    cf_contest = models.CharField(max_length=20, verbose_name="Номер контеста")
    human_name = models.TextField(blank=True)
    monitor = models.ForeignKey(Monitor, on_delete=models.CASCADE)
    error_text = models.TextField(null=True)
    # todo
    # owner = models.ForeignKey(User, to_field='username', default='Catmoonlight', on_delete=models.CASCADE)
    # editors = models.ManyToManyField(User)

    last_status_update = models.DateTimeField(null=True)
    last_ping = models.DateTimeField(null=True)

    class Meta:
        ordering = ['index']

    def get_name(self):
        if self.human_name:
            return f"{self.human_name}"
        return f"# {self.cf_contest}"

    def get_cf_url(self):
        return f"https://codeforces.com/group/{self.monitor.group}/contest/{self.cf_contest}"

    def set_error(self, comment):
        self.error_text = comment
        self.save()

    def save(self, *args, **kwargs):
        if self.index is None:
            self.index = self.pk
        super(Contest, self).save(*args, **kwargs)

    def refresh(self):
        self.problem_set.all().delete()
        self.last_status_update = None
        self.error_text = None
        self.save()
