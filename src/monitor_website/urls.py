from django.shortcuts import redirect
from django.urls import path
import monitor_website.views as views

app_name = "main"
urlpatterns = [
    path('', views.monitors_index_page, name='home'),
    path('monitors/', views.monitors_list_page, name="monitor_list"),
    path('monitors/new/', views.NewMonitorView.as_view(), name='new_monitor'),
    path('monitor/<int:monitor_id>/', views.monitor_page, name="monitor"),
    path('monitor/<int:monitor_id>/up/', views.move_up_monitor, name="monitor_up"),
    path('monitor/<int:monitor_id>/down/', views.move_down_monitor, name="monitor_down"),
    path('monitor/<int:monitor_id>/edit/', views.monitor_edit, name="monitor_edit"),
    path('monitor/<int:monitor_id>/edit/delete/<int:contest_id>/', views.edit_delete_contest, name="contest_delete"),
    path('monitor/<int:monitor_id>/edit/refresh/<int:contest_id>/', views.edit_refresh_contest, name="contest_refresh"),
    path('monitor/<int:monitor_id>/edit/left/<int:contest_id>/', views.edit_move_left_contest, name="contest_left"),
    path('monitor/<int:monitor_id>/edit/right/<int:contest_id>/', views.edit_move_right_contest, name="contest_right"),
    path('monitor/<int:monitor_id>/edit/rename/<int:contest_id>/', views.edit_rename_contest, name="contest_rename"),
    path('monitor/<int:monitor_id>/edit/monitor_rename/', views.edit_rename_monitor, name="monitor_rename"),

    path('logs/', views.worker_logs, name='logs'),
    path('hidden/<int:monitor_id>/card/', views.card_inside, name='card_inside'),
    path('hidden/<int:monitor_id>/', views.monitor_inside, name='monitor_inside')
]