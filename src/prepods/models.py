from django.db import models


class RegisterKeyWord(models.Model):
    key = models.CharField(max_length=50, primary_key=True)
