from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth.views import LoginView
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django.views.generic import CreateView
from prepods.forms import LoginForm, CreationForm
import django.http as http


class LoginPrepod(LoginView):
    form_class = LoginForm
    template_name = 'auth.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Войти'
        return context

    def get_success_url(self):
        return reverse_lazy('main:home')


class RegisterPrepod(CreateView):
    form_class = CreationForm
    template_name = 'create.html'
    success_url = reverse_lazy('prepods:admin')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['heading'] = 'Добавить преподавателя'
        context['title'] = 'Добавить преподавателя'
        context['return'] = reverse_lazy('prepods:admin')
        context['return_text'] = 'Вернуться в админку'
        return context

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            raise http.Http404()
        return super().dispatch(request, *args, **kwargs)


def logout_prepod(request: http.HttpRequest):
    logout(request)
    return redirect('main:home')


def prepods_post_process(d):
    if 'query_type' not in d:
        return 'В запросе отсутствует тип запроса', 'danger'
    if 'teacher' not in d:
        return 'В запросе отсутствует пользователь', 'danger'
    if not User.objects.filter(username=d['teacher']).exists():
        return f'Пользователь {d["teacher"]} не найден', 'danger'
    if d['teacher'] == 'Catmoonlight':
        return 'Ты че, охуел?', 'danger'

    user = User.objects.get(username=d['teacher'])

    if d['query_type'] == 'admin':
        if 'is_set' in d and d['is_set'] == 'on':
            user.is_superuser = True
            user.save()
            return f'{user.username} теперь админ', 'success'
        else:
            user.is_superuser = False
            user.save()
            return f'{user.username} больше не админ', 'success'
    elif d['query_type'] == 'delete':
        user.delete()
        return f'{user.username} удален', 'success'
    else:
        return 'Тип запроса неизвестен', 'danger'


def prepods(request: http.HttpRequest):
    if not request.user.is_superuser:
        raise http.Http404()
    users = User.objects.order_by('username').all()
    context = {'users': users, 'title': 'Админка'}

    if request.method == 'POST':
        comment, style = prepods_post_process(request.POST)
        if comment:
            context['comment'] = comment
            context['comment_style'] = style

    return render(request, 'prepods.html', context)
