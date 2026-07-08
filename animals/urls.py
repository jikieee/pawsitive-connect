from django.urls import path
from . import views

urlpatterns = [
    path('animal/add/', views.org_add_animal, name='org_add_animal'),
    path('animal/<int:animal_id>/edit/', views.org_edit_animal, name='org_edit_animal'),
    path('animal/<int:animal_id>/toggle-adoption/', views.org_toggle_adoption, name='org_toggle_adoption'),
]
