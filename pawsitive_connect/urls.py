from django.contrib import admin
from django.urls import path, include, reverse_lazy
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home_redirect, name='home'),
    path('role-select/', views.role_select_view, name='role_select'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='password_reset.html',
        email_template_name='registration/password_reset_email.html',
        subject_template_name='registration/password_reset_subject.txt',
        success_url=reverse_lazy('password_reset_done'),
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='password_reset_confirm.html',
        success_url=reverse_lazy('password_reset_complete'),
    ), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='password_reset_complete.html'
    ), name='password_reset_complete'),
    path('account/settings/', views.profile_settings_view, name='profile_settings'),
    path('account/password/', views.change_password_view, name='change_password'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/admin/users/<int:user_id>/toggle-active/', views.admin_toggle_user_active, name='admin_toggle_user_active'),
    path('dashboard/admin/organizations/<int:org_id>/toggle-active/', views.admin_toggle_org_active, name='admin_toggle_org_active'),
    path('dashboard/admin/reports/<int:report_id>/status/', views.admin_update_report_status, name='admin_update_report_status'),
    path('dashboard/admin/reports/export.csv', views.admin_export_reports_csv, name='admin_export_reports_csv'),
    path('dashboard/admin/activity/export.csv', views.admin_export_activity_csv, name='admin_export_activity_csv'),
    
    # API Endpoints
    path('api/dashboard-stats/', views.dashboard_stats_api, name='dashboard_stats_api'),
    path('api/recent-reports/', views.recent_reports_api, name='recent_reports_api'),
    path('api/org-stats/', views.org_stats_api, name='org_stats_api'),
    path('api/user-notifications/', views.user_notifications_api, name='user_notifications_api'),
    path('api/browse-animals/', views.browse_animals_api, name='browse_animals_api'),
    path('api/animal/<int:animal_id>/detail/', views.animal_detail_api, name='animal_detail_api'),
    path('api/message-thread/<int:other_user_id>/', views.message_thread_api, name='message_thread_api'),
    path('api/conversations/', views.conversations_api, name='conversations_api'),
    path('api/rescue-organizations/', views.RescueOrganizationListAPIView.as_view(), name='rescue_organizations_api'),
    path('api/rescued-animals/', views.RescuedAnimalListAPIView.as_view(), name='rescued_animals_api'),
    path('api/adoption-inquiries/', views.AdoptionInquiryListAPIView.as_view(), name='adoption_inquiries_api'),
    
    # Service URLs
    path('api/', include('reports.urls')),
    path('api/', include('animals.urls')),
    path('api/', include('organizations.urls')),
    path('api/', include('accounts.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
