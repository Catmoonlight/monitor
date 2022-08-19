from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django import forms
from django.contrib.auth.models import User
from prepods.models import RegisterKeyWord


class LoginForm(AuthenticationForm):
    username = forms.CharField(label='Логин', widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        "autocomplete": "current-password"
    }))


class CreationForm(UserCreationForm):
    username = forms.CharField(label='Логин', widget=forms.TextInput(attrs={'class': 'form-control'}))
    code_word = forms.CharField(label='Кодовое слово', widget=forms.TextInput(attrs={'class': 'form-control font-monospace'}))
    password1 = forms.CharField(label='Пароль', widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        "autocomplete": "new-password",
    }))
    password2 = forms.CharField(label='Еще раз пароль', widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        "autocomplete": "new-password",
    }))

    class Meta:
        model = User
        fields = ('username', 'password1', 'password2', 'code_word')

    def _post_clean(self):
        super()._post_clean()
        keyword = self.cleaned_data.get("code_word")
        if keyword and not RegisterKeyWord.objects.filter(pk=keyword).exists():
            self.add_error('code_word', "Такого кодового слова не существует")

    def save(self, commit=True):
        if commit:
            code_word = self.cleaned_data.get('code_word')
            if code_word and RegisterKeyWord.objects.filter(pk=code_word).exists():
                RegisterKeyWord.objects.get(pk=code_word).delete()

        return super().save(commit)


class KeyWordForm(forms.ModelForm):
    key = forms.CharField(label='Ключ', widget=forms.TextInput(attrs={'class': 'form-control font-monospace'}))

    class Meta:
        model = RegisterKeyWord
        fields = ('key',)

