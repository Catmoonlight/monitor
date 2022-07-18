import django.http as http
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView

import monitor_website.models as models
import monitor_website.forms as forms

from monitor_website.cf_worker import CodeforcesWorker


class NewMonitorView(CreateView):
    model = models.Monitor
    form_class = forms.NewMonitorForm
    template_name = 'create.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['heading'] = 'Создание монитора'
        context['title'] = 'Создание монитора'
        context['return'] = reverse_lazy('main:home')
        return context


def monitor_page(request: http.HttpRequest, monitor_id):
    CodeforcesWorker()
    monitor = get_object_or_404(models.Monitor, pk=monitor_id)

    results = {}
    for person in monitor.personality_set.filter(is_blacklisted=False).all():
        results[person] = []
        for contest in monitor.contest_set.all():
            for problem in contest.problem_set.all():
                c = 0
                lst = ('', '#', True)
                for submit in person.submit_set.filter(problem=problem).order_by('submission_time').all():
                    if submit.verdict == submit.OK:
                        lst = ('+' if c == 0 else f'+{c}', submit.get_cf_url(), submit.is_contest)
                        break
                    else:
                        c += 1
                        lst = ('' if c == 0 else f'-{c}', submit.get_cf_url(), submit.is_contest)
                results[person] += [lst]

    personalities = list(results.items())
    personalities.sort(key=lambda x: -x[0].solved())

    return render(request, "monitor.html", {
        'title': monitor.human_name,
        'monitor': monitor,
        'personalities': personalities,
    })


def monitor_edit(request: http.HttpRequest, monitor_id):
    if not request.user.is_authenticated:
        raise http.Http404()

    CodeforcesWorker()
    monitor = get_object_or_404(models.Monitor, pk=monitor_id)
    contests = monitor.contest_set.all()

    create_contest_form = forms.CreateContestForm()

    if request.method == 'POST' and 'query_type' in request.POST:
        q_type = request.POST['query_type']
        post = request.POST.copy()
        post.pop('query_type')

        if q_type == 'delete_monitor':
            monitor.delete()
            return redirect('main:home')
        # monitor settings
        elif q_type == 'show':
            monitor.is_hidden = not ('is_set' in post and post['is_set'] == 'on')
            monitor.save()
        elif q_type == 'worker':
            monitor.is_old = not ('is_set' in post and post['is_set'] == 'on')
            monitor.save()
        elif q_type == "ghosts":
            monitor.default_ghosts = 'is_set' in post and post['is_set'] == 'on'
            monitor.save()
        # contests
        elif q_type == 'create':
            create_contest_form = forms.CreateContestForm(post)
            if create_contest_form.is_valid():
                data = create_contest_form.cleaned_data
                if contests.filter(cf_contest=data['cf_contest'], monitor=monitor).exists():
                    create_contest_form.add_error('cf_contest', "Такой контест уже существует в мониторе!")
                else:
                    models.Contest.objects.create(
                        cf_contest=data['cf_contest'],
                        monitor=monitor,
                        human_name=data['human_name']
                    )
                    create_contest_form = forms.CreateContestForm()
        elif q_type == 'delete':
            cf_contest = post['cf_contest']
            contest = get_object_or_404(models.Contest, cf_contest=cf_contest, monitor=monitor)
            contest.delete()
        elif q_type == 'refresh':
            cf_contest = post['cf_contest']
            contest = get_object_or_404(models.Contest, cf_contest=cf_contest, monitor=monitor)
            contest.status = contest.FRESH
            contest.problem_set.all().delete()
            contest.last_status_update = None
            contest.save()
        # pers
        elif q_type == 'update_pers':
            for person in models.Personality.objects.filter(monitor=monitor).all():
                if f'{person.nickname}_real_name' not in post:
                    continue
                person.real_name = post[f'{person.nickname}_real_name']
                person.is_blacklisted = f'{person.nickname}_is_blacklisted' in post and post[f'{person.nickname}_is_blacklisted'] == 'on'
                person.save()

    return render(request, "monitor_edit.html", {
        'title': f"Редактирование {monitor.human_name}",
        'monitor': monitor,
        'contests': contests,
        'creation_form': create_contest_form,
        'personals': sorted(list(monitor.personality_set.all()), key=lambda x: x.nickname.lower())
    })


def monitors_list_page(request: http.HttpRequest):
    CodeforcesWorker()

    return render(request, "home.html", {
        'title': "Мониторы",
        'monitors': models.Monitor.objects.all(),
    })