import django.forms as forms
import monitor_website.models as models


class NewMonitorForm(forms.ModelForm):
    group = forms.CharField(label='Код группы', widget=forms.TextInput(
        attrs={'class': 'form-control font-monospace'})
    )
    human_name = forms.CharField(label='Название монитора', widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = models.Monitor
        fields = ('group', 'human_name', 'name')


class CreateContestForm(forms.Form):
    cf_contest = forms.IntegerField(label='ID контеста', widget=forms.TextInput(
        attrs={'class': 'form-control font-monospace'})
    )
    human_name = forms.CharField(label='Название контеста', widget=forms.TextInput(attrs={'class': 'form-control'}))
