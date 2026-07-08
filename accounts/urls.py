from django.urls import path
from . import views

urlpatterns = [
    path('inquiry/submit/', views.user_send_inquiry, name='user_send_inquiry'),
    path('animal/<int:animal_id>/toggle-save/', views.user_toggle_save, name='user_toggle_save'),
    path('message/send/', views.user_send_message, name='user_send_message'),
    path('notifications/mark-read/', views.user_mark_notifications_read, name='user_mark_notifications_read'),
]
