from django.shortcuts import redirect
from django.urls import path
import monitor_website.views as views

app_name = "main"
urlpatterns = [
    path('', lambda request: redirect('monitors/', permanent=False)),
    path('monitors/', views.monitors_list_page, name="home"),
    path('monitors/new', views.NewMonitorView.as_view(), name='new_monitor'),
    path('monitor/<int:monitor_id>/', views.monitor_page, name="monitor"),
    path('monitor/<int:monitor_id>/edit/', views.monitor_edit, name="monitor_edit"),
    path('logs/', views.worker_logs, name='logs')
]