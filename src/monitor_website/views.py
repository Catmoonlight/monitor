import django.http as http
from django.db import transaction
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin

import monitor_website.models as models
import monitor_website.forms as forms

from monitor_website.cf_worker import CodeforcesWorker, ping
from .monitor_gen import MonitorGenerator


def auth_or_404(function):
    def new_func(request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise http.Http404()
        return function(request, *args, **kwargs)
    return new_func


class NewMonitorView(LoginRequiredMixin, CreateView):
    model = models.Monitor
    form_class = forms.NewMonitorForm
    template_name = 'create.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['heading'] = 'Создание монитора'
        context['title'] = 'Создание монитора'
        context['return'] = reverse_lazy('main:home')
        return context


def monitor_inside(request: http.HttpRequest, monitor_id):
    monitor = get_object_or_404(models.Monitor, pk=monitor_id)
    problem_list, personalities = MonitorGenerator.gen(monitor, request.user.is_authenticated)
    return render(request, '_monitor.html', {
        'monitor': monitor,
        'total_problems': len(problem_list),
        'personalities': personalities,
    })


def monitor_page(request: http.HttpRequest, monitor_id):
    monitor = get_object_or_404(models.Monitor, pk=monitor_id)
    ping(monitor)

    return render(request, "monitor.html", {
        'title': monitor.human_name,
        'monitor': monitor,
    })


def monitor_edit(request: http.HttpRequest, monitor_id):
    if not request.user.is_authenticated:
        raise http.Http404()

    monitor = get_object_or_404(models.Monitor, pk=monitor_id)
    ping(monitor)
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
                person.is_blacklisted = not (f'{person.nickname}_is_whitelisted' in post and post[f'{person.nickname}_is_whitelisted'] == 'on')
                person.save()

    return render(request, "monitor_edit.html", {
        'title': f"Редактирование {monitor.human_name}",
        'monitor': monitor,
        'contests': contests,
        'creation_form': create_contest_form,
        'personals': sorted(list(monitor.personality_set.all()), key=lambda x: x.nickname.lower()),
        'w_status': CodeforcesWorker.current_status
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


@auth_or_404
def edit_rename_monitor(request, monitor_id):
    monitor = get_object_or_404(models.Monitor, pk=monitor_id)
    new_name = request.GET.get('name', monitor.human_name)
    monitor.human_name = new_name
    monitor.save()
    return redirect('main:monitor_edit', monitor_id=monitor_id)


def edit_rename_contest(request, monitor_id, contest_id):
    contest = _edit_get_contest(request, monitor_id, contest_id)
    new_name = request.GET.get('name', contest.human_name)
    contest.human_name = new_name
    contest.save()
    return redirect('main:monitor_edit', monitor_id=monitor_id)


def __swap(lst, i):
    with transaction.atomic():
        lst[i].index, lst[i + 1].index = lst[i + 1].index, lst[i].index
        lst[i].save()
        lst[i + 1].save()


@auth_or_404
def _edit_move_contest(request, monitor_id, contest_id, addit_index):
    monitor = get_object_or_404(models.Monitor, pk=monitor_id)
    all_contests = list(monitor.contest_set.all())
    for i in range(len(all_contests) - 1):
        if all_contests[i + addit_index].cf_contest == str(contest_id):
            __swap(all_contests, i)
            break
    return redirect('main:monitor_edit', monitor_id=monitor_id)


@auth_or_404
def _edit_move_monitor(request, monitor_id, addit_index):
    all_monitors = list(models.Monitor.objects.all())
    for i in range(len(all_monitors) - 1):
        if all_monitors[i + addit_index].pk == monitor_id:
            __swap(all_monitors, i)
            break
    return redirect('main:home')


def edit_move_left_contest(request, monitor_id, contest_id):
    return _edit_move_contest(request, monitor_id, contest_id, 1)


def edit_move_right_contest(request, monitor_id, contest_id):
    return _edit_move_contest(request, monitor_id, contest_id, 0)


def move_up_monitor(request, monitor_id):
    return _edit_move_monitor(request, monitor_id, 1)


def move_down_monitor(request, monitor_id):
    return _edit_move_monitor(request, monitor_id, 0)


def monitors_list_page(request: http.HttpRequest, render_admin=False):
    if render_admin and not request.user.is_superuser:
        render_admin = None
    CodeforcesWorker()
    return render(request, "home.html", {
        'render_admin': render_admin,
        'title': "Мониторы",
        'monitors': models.Monitor.objects.all(),
    })


def monitors_index_page(request: http.HttpRequest):
    if request.user.is_superuser:
        return monitors_list_page(request, True)
    return redirect('main:monitor_list')


def worker_logs(request: http.HttpRequest):
    if not request.user.is_authenticated:
        raise http.Http404()
    CodeforcesWorker()
    return render(request, 'worker_logs.html', {
        'title': 'Логи воркера',
        'logs': sorted(CodeforcesWorker.worker_logs.copy(), key=lambda x: x.time, reverse=True)
    })


def card_inside(request, monitor_id):
    contest_id = request.GET.get('contest', 'ERROR_NO')
    contest = _edit_get_contest(request, monitor_id, contest_id)
    return render(request, '__card_inside.html', {
        "contest": contest,
        "w_status": CodeforcesWorker.current_status
    })
