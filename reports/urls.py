from django.urls import path
from core import views as core_views
from . import views

urlpatterns = [
    path('report/submit/', core_views.user_submit_report, name='user_submit_report'),
    path('report/<int:report_id>/update/', views.update_animal_report, name='org_update_report'),
]
