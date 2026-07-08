from django.urls import path
from . import views
from core import views as core_views

urlpatterns = [
    path('reports/export.csv', views.org_export_reports_csv, name='org_export_reports_csv'),
    path('activity/export.csv', views.org_export_activity_csv, name='org_export_activity_csv'),
    path('announcement/post/', views.org_post_announcement, name='org_post_announcement'),
    path('announcement/<int:announcement_id>/edit/', views.org_edit_announcement, name='org_edit_announcement'),
    path('announcement/<int:announcement_id>/archive/', views.org_archive_announcement, name='org_archive_announcement'),
    path('announcement/<int:announcement_id>/restore/', views.org_restore_announcement, name='org_restore_announcement'),
    path('message/reply/', core_views.org_send_message, name='org_send_message'),
    path('inquiry/<int:inquiry_id>/status/', core_views.org_update_inquiry_status, name='org_update_inquiry_status'),
]
