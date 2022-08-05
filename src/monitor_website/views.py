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

    problem_list = []
    for contest in monitor.contest_set.all():
        problem_list += list(contest.problem_set.all())

    results = {}
    for person in monitor.personality_set.filter(is_blacklisted=False).all():
        results[person] = []
        d_c = {}

        for submit in person.submit_set.order_by('submission_time').all():
            if submit.problem not in d_c:
                d_c[submit.problem] = ('', '#', True, 0)
            if d_c[submit.problem][0].startswith('+'):
                continue

            c = d_c[submit.problem][-1]
            if submit.verdict == submit.OK:
                d_c[submit.problem] = ('+' if c == 0 else f'+{c}', submit.get_cf_url(), submit.is_contest, c)
            else:
                d_c[submit.problem] = (f'-{c + 1}', submit.get_cf_url(), submit.is_contest, c + 1)

        for problem in problem_list:
            if problem in d_c:
                results[person] += [d_c[problem]]
            else:
                results[person] += [('', '#', True, 0)]

    personalities = list(results.items())
    personalities.sort(key=lambda x: (-x[0].solved(), -x[0].practiced()))
    for i in range(len(personalities)):
        personalities[i] = (i + 1, personalities[i][0], personalities[i][1])

    return render(request, "monitor.html", {
        'title': monitor.human_name,
        'monitor': monitor,
        'total_problems': len(problem_list),
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
        elif q_type == 'show':
            monitor.is_hidden = not ('is_set' in post and post['is_set'] == 'on')
            monitor.save()
        elif q_type == 'worker':
            monitor.is_old = not ('is_set' in post and post['is_set'] == 'on')
            monitor.save()
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


def _edit_get_contest(request, monitor_id, contest_id):
    if not request.user.is_authenticated:
        raise http.Http404()
    monitor = get_object_or_404(models.Monitor, pk=monitor_id)
    return get_object_or_404(models.Contest, cf_contest=contest_id, monitor=monitor)


def edit_delete_contest(request, monitor_id, contest_id):
    contest = _edit_get_contest(request, monitor_id, contest_id)
    contest.delete()
    return redirect('main:monitor_edit', monitor_id=monitor_id)


def edit_refresh_contest(request, monitor_id, contest_id):
    contest = _edit_get_contest(request, monitor_id, contest_id)
    contest.refresh()
    return redirect('main:monitor_edit', monitor_id=monitor_id)


def edit_rename_contest(request, monitor_id, contest_id):
    contest = _edit_get_contest(request, monitor_id, contest_id)
    new_name = request.GET['name']
    contest.human_name = new_name
    contest.save()
    return redirect('main:monitor_edit', monitor_id=monitor_id)


def edit_move_left_contest(request, monitor_id, contest_id):
    if not request.user.is_authenticated:
        raise http.Http404()
    monitor = get_object_or_404(models.Monitor, pk=monitor_id)
    all_contests = list(monitor.contest_set.all())
    for i in range(1, len(all_contests)):
        if all_contests[i].cf_contest == str(contest_id):
            all_contests[i].index, all_contests[i-1].index = all_contests[i-1].index, all_contests[i].index
            all_contests[i].save()
            all_contests[i-1].save()
            break
    return redirect('main:monitor_edit', monitor_id=monitor_id)


def edit_move_right_contest(request, monitor_id, contest_id):
    if not request.user.is_authenticated:
        raise http.Http404()
    monitor = get_object_or_404(models.Monitor, pk=monitor_id)
    all_contests = list(monitor.contest_set.all())
    for i in range(len(all_contests) - 1):
        if all_contests[i].cf_contest == str(contest_id):
            all_contests[i].index, all_contests[i+1].index = all_contests[i+1].index, all_contests[i].index
            all_contests[i].save()
            all_contests[i+1].save()
            break
    return redirect('main:monitor_edit', monitor_id=monitor_id)


def monitors_list_page(request: http.HttpRequest):
    CodeforcesWorker()

    return render(request, "home.html", {
        'title': "Мониторы",
        'monitors': models.Monitor.objects.all(),
    })


def worker_logs(request: http.HttpRequest):
    if not request.user.is_authenticated:
        raise http.Http404()

    CodeforcesWorker()
    return render(request, 'worker_logs.html', {
        'title': 'Логи воркера',
        'logs': sorted(CodeforcesWorker.logs.copy(), key=lambda x: x.time, reverse=True)
    })
