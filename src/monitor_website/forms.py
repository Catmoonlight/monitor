import django.forms as forms
import monitor_website.models as models


class NewMonitorForm(forms.ModelForm):
    group = forms.CharField(label='Код группы', widget=forms.TextInput(
        attrs={'class': 'form-control font-monospace',
               'placeholder': "codeforces.com/group/<нужны эти 10 символов>"})
    )
    human_name = forms.CharField(label='Название монитора', widget=forms.TextInput(
        attrs={'class': 'form-control',
               'placeholder': "Дюжонок, декабрь 2019, первая группа"}))
    is_hidden = forms.BooleanField(label='Скрыть по умолчанию?', required=False, widget=forms.CheckboxInput(
        attrs={'class': 'form-check-input',
               'checked': ""}))

    class Meta:
        model = models.Monitor
        fields = ('group', 'human_name', 'is_hidden')


class CreateContestForm(forms.Form):
    cf_contest = forms.IntegerField(label='ID контеста', widget=forms.TextInput(
        attrs={'class': 'form-control font-monospace',
               'placeholder': "codeforces.com/.../contest/<вот эти цифры>"})
    )
    human_name = forms.CharField(label='Название контеста', required=False,
                                 widget=forms.TextInput(attrs={
                                     'class': 'form-control',
                                     'placeholder': "По умолчанию загрузится название с codeforces"
                                 }))
