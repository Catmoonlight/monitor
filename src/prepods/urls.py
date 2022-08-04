from django.shortcuts import redirect
from django.urls import path
import prepods.views as views

app_name = "prepods"
urlpatterns = [
    path('login/', views.LoginPrepod.as_view(), name='login'),
    path('logout/', views.logout_prepod, name='logout'),
    path('admin/', views.prepods, name='admin'),
    path('admin/create', views.RegisterPrepod.as_view(), name='create')
]