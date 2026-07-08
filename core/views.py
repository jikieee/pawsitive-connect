from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Max, Count, Q
from django.conf import settings
from datetime import date, timedelta
from functools import wraps
import json
import csv
import urllib.parse
import urllib.request

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .forms import RegistrationForm, ProfileUpdateForm
from .models import AdminAuditLog

# Models from correct apps
from accounts.models import UserProfile, SavedAnimal, AdoptionInquiry, Message, Notification, Conversation
from animals.models import RescuedAnimal, RescuedAnimalPhoto
from reports.models import AnimalReport, AnimalReportPhoto
from organizations.models import RescueOrganization, Announcement

from .serializers import (
    AdoptionInquirySerializer,
    RescueOrganizationSerializer,
    RescuedAnimalSerializer,
)

# ══════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════

def _get_or_create_profile(user):
    """Return the UserProfile for a user, creating one if missing."""
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


def _unread_count(user):
    return Notification.objects.filter(recipient=user, is_read=False).count()



def _admin_log(request, action, target_label, details=''):
    """Create an admin audit entry without interrupting the main action."""
    try:
        AdminAuditLog.objects.create(
            actor=request.user if request.user.is_authenticated else None,
            action=action,
            target_label=str(target_label)[:255],
            details=details or '',
        )
    except Exception:
        pass


def _csv_response(filename):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write('\ufeff')
    return response

def _wants_json(request):
    return (
        request.headers.get('x-requested-with') == 'XMLHttpRequest' or
        'application/json' in request.headers.get('accept', '')
    )


def _trend_summary(current, previous, label):
    delta = current - previous
    if delta > 0:
        return {'direction': 'up', 'text': f'↑ {delta} vs {label}'}
    if delta < 0:
        return {'direction': 'down', 'text': f'↓ {abs(delta)} vs {label}'}
    return {'direction': 'same', 'text': f'↔ 0 vs {label}'}


def _build_pagination_context(request, page_obj):
    params = request.GET.copy()
    params.pop('page', None)
    params.pop('tab', None)
    querystring = params.urlencode()

    num_pages = page_obj.paginator.num_pages
    current = page_obj.number
    page_numbers = []
    if num_pages <= 7:
        page_numbers = list(range(1, num_pages + 1))
    else:
        page_numbers = [1, 2]
        if current > 4:
            page_numbers.append('...')
        for page_num in range(current - 1, current + 2):
            if 2 < page_num < num_pages - 1:
                page_numbers.append(page_num)
        if current < num_pages - 3:
            page_numbers.append('...')
        page_numbers += [num_pages - 1, num_pages]
        seen = set()
        page_numbers = [x for x in page_numbers if x not in seen and not seen.add(x)]

    return {
        'page_obj': page_obj,
        'querystring': querystring,
        'page_numbers': page_numbers,
    }


def _validate_recaptcha(request):
    token = request.POST.get('g-recaptcha-response', '').strip()
    if not token:
        return False

    secret_key = getattr(settings, 'RECAPTCHA_SECRET_KEY', '')
    if not secret_key:
        return False

    payload = urllib.parse.urlencode({
        'secret': secret_key,
        'response': token,
        'remoteip': request.META.get('REMOTE_ADDR', ''),
    }).encode('utf-8')

    try:
        with urllib.request.urlopen(
            getattr(settings, 'RECAPTCHA_VERIFY_URL', 'https://www.google.com/recaptcha/api/siteverify'),
            data=payload,
            timeout=5,
        ) as response:
            data = json.loads(response.read().decode('utf-8'))
    except Exception:
        return False

    return bool(data.get('success'))


def _is_admin_user(user, profile=None):
    profile = profile or _get_or_create_profile(user)
    return user.is_superuser or user.is_staff or profile.role == 'admin'


def _role_allowed(user, roles):
    if not user.is_authenticated:
        return False
    profile = _get_or_create_profile(user)
    if 'admin' in roles and _is_admin_user(user, profile):
        return True
    return profile.role in roles


def _validate_uploaded_files(files):
    max_files = 5
    max_size = 5 * 1024 * 1024
    if len(files) > max_files:
        return False, 'You may upload up to 5 photos.'
    for uploaded_file in files:
        if not uploaded_file.content_type.startswith('image/'):
            return False, 'Only image files are allowed for report photos.'
        if uploaded_file.size > max_size:
            return False, 'Each photo must be smaller than 5MB.'
    return True, ''


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not _role_allowed(request.user, roles):
                if request.path.startswith('/api/'):
                    return JsonResponse({'error': 'You do not have permission to perform this action.'}, status=403)
                messages.error(request, 'You do not have permission to access that page.')
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def api_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'ok': False, 'error': 'Authentication required.'}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper


# ══════════════════════════════════════════════════
#  AUTH
# ══════════════════════════════════════════════════

def home_redirect(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('role_select')


def role_select_view(request):
    """Display role selection page before login."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        selected_role = request.POST.get('role', '').strip()
        if selected_role in ['reporter', 'rescue_org', 'admin']:
            request.session['selected_role'] = selected_role
            return redirect('login')
        messages.error(request, 'Invalid role selection.')
    
    landing_stats = {
        'landing_total_reports': AnimalReport.objects.count(),
        'landing_rescued_count': AnimalReport.objects.filter(status__in=['rescued', 'under_observation', 'in_treatment', 'ready_for_adoption', 'adopted']).count(),
        'landing_adoptable_count': RescuedAnimal.objects.filter(status='adoption', adoption_open=True, rescue_org__isnull=False).count(),
    }
    return render(request, 'role_select.html', landing_stats)


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    selected_role = request.session.get('selected_role')
    if not selected_role:
        return redirect('role_select')

    if request.method == 'POST':
        if not _validate_recaptcha(request):
            messages.error(request, 'Please complete the reCAPTCHA verification.')
            return render(request, 'login.html', {
                'selected_role': selected_role,
                'role_display': dict(UserProfile.ROLE_CHOICES).get(selected_role, selected_role),
                'recaptcha_site_key': settings.RECAPTCHA_SITE_KEY,
            })

        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            profile = _get_or_create_profile(user)
            if selected_role == 'admin' and not _is_admin_user(user, profile):
                messages.error(request, 'This account does not have administrator access.')
                return render(request, 'login.html', {
                    'selected_role': selected_role,
                    'role_display': dict(UserProfile.ROLE_CHOICES).get(selected_role, selected_role)
                })
            if selected_role != 'admin' and profile.role != selected_role:
                messages.error(request, f'This account is registered as {profile.get_role_display()}.')
                return render(request, 'login.html', {
                    'selected_role': selected_role, 
                    'role_display': dict(UserProfile.ROLE_CHOICES).get(selected_role, selected_role)
                }) 
            
            login(request, user)
            request.session.pop('selected_role', None)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')

    context = {
        'selected_role': selected_role,
        'role_display': dict(UserProfile.ROLE_CHOICES).get(selected_role, selected_role),
        'recaptcha_site_key': settings.RECAPTCHA_SITE_KEY,
    }
    return render(request, 'login.html', context)


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    selected_role = request.session.get('selected_role', 'reporter')
    if selected_role == 'admin':
        messages.info(request, 'Administrator accounts must be created by an existing administrator.')
        return redirect('login')

    if request.method == 'POST':
        form = RegistrationForm(request.POST, selected_role=selected_role)
        if not _validate_recaptcha(request):
            messages.error(request, 'Please complete the reCAPTCHA verification.')
        elif form.is_valid():
            user = form.save()

            # Notify administrators whenever a new account is created.
            # This uses the existing Notification model so admins can see
            # new reporter/rescue organization registrations in their dashboard.
            role_label = dict(UserProfile.ROLE_CHOICES).get(selected_role, selected_role)
            admin_profiles = UserProfile.objects.filter(role='admin').select_related('user')
            admin_users = list(User.objects.filter(is_superuser=True)) + [p.user for p in admin_profiles]
            seen_admin_ids = set()
            admin_notifications = []
            for admin_user in admin_users:
                if not admin_user or admin_user.pk in seen_admin_ids:
                    continue
                seen_admin_ids.add(admin_user.pk)
                admin_notifications.append(Notification(
                    recipient=admin_user,
                    type='new_user_message',
                    title=f'New {role_label} account created',
                    body=f'{user.get_full_name() or user.username} registered as {role_label}.',
                ))
            if admin_notifications:
                Notification.objects.bulk_create(admin_notifications)

            login(request, user)
            request.session.pop('selected_role', None)
            messages.success(request, 'Account created successfully.')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = RegistrationForm(selected_role=selected_role)

    context = {
        'form': form,
        'selected_role': selected_role,
        'role_display': dict(UserProfile.ROLE_CHOICES).get(selected_role, selected_role),
        'recaptcha_site_key': settings.RECAPTCHA_SITE_KEY,
    }
    return render(request, 'register.html', context)

def logout_view(request):
    logout(request)
    return redirect('role_select')


@login_required
def profile_settings_view(request):
    profile = _get_or_create_profile(request.user)

    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile_settings')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = ProfileUpdateForm(instance=profile, user=request.user)

    return render(request, 'account_settings.html', {
        'form': form,
        'profile': profile,
        'page_title': 'Account Settings',
        'unread_count': _unread_count(request.user),
    })


@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully.')
            return redirect('profile_settings')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'change_password.html', {
        'form': form,
        'page_title': 'Change Password',
        'unread_count': _unread_count(request.user),
    })


# ══════════════════════════════════════════════════
#  ROLE-BASED DASHBOARD ROUTER
# ══════════════════════════════════════════════════

@login_required
def dashboard(request):
    profile = _get_or_create_profile(request.user)
    if _is_admin_user(request.user, profile):
        return _admin_dashboard(request)
    elif profile.role == 'rescue_org':
        from organizations.views import _org_dashboard
        return _org_dashboard(request, profile)
    else:
        from accounts.views import _user_dashboard
        return _user_dashboard(request, profile)


# ──────────────────────────────────────────────────
#  ADMIN DASHBOARD  
# ──────────────────────────────────────────────────

def _admin_dashboard(request):
    users = User.objects.select_related('profile', 'profile__organization').order_by('-date_joined')
    organizations = RescueOrganization.objects.annotate(
        member_count=Count('members', distinct=True),
        report_count=Count('assigned_reports', distinct=True),
        animal_count=Count('rescued_animals', distinct=True),
    ).order_by('-created_at')
    reports = AnimalReport.objects.select_related('reporter', 'rescue_org').order_by('-reported_at')
    animals = RescuedAnimal.objects.select_related('rescue_org', 'source_report').order_by('-rescued_at')
    announcements = Announcement.objects.select_related('rescue_org', 'posted_by').order_by('-created_at')[:20]
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')

    today = date.today()
    week_ago = today - timedelta(days=7)

    context = {
        'user': request.user,
        'page_title': 'Admin Dashboard',
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'total_orgs': RescueOrganization.objects.count(),
        'active_orgs': RescueOrganization.objects.filter(is_active=True).count(),
        'inactive_orgs': RescueOrganization.objects.filter(is_active=False).count(),
        'total_reports': AnimalReport.objects.count(),
        'pending_rescues': AnimalReport.objects.filter(status='pending').count(),
        'responding_reports': AnimalReport.objects.filter(status='responding').count(),
        'completed_rescues': AnimalReport.objects.filter(status__in=['rescued', 'closed', 'ready_for_adoption', 'adopted']).count(),
        'reports_this_week': AnimalReport.objects.filter(reported_at__date__gte=week_ago).count(),
        'rescued_animals': RescuedAnimal.objects.count(),
        'in_treatment': RescuedAnimal.objects.filter(status__in=['observation', 'recovering']).count(),
        'ready_for_adoption': RescuedAnimal.objects.filter(status='adoption', adoption_open=True).count(),
        'adopted_animals': RescuedAnimal.objects.filter(status='adopted').count(),
        'announcements_total': Announcement.objects.count(),
        'active_announcements': Announcement.objects.filter(is_active=True).count(),
        'users': users,
        'organizations': organizations,
        'reports': reports,
        'animals': animals,
        'announcements': announcements,
        'notifications': notifications,
        'audit_logs': AdminAuditLog.objects.select_related('actor').order_by('-created_at')[:100],
        'unread_count': notifications.filter(is_read=False).count(),
        'animal_type_counts': {
            'dogs': AnimalReport.objects.filter(animal_type='dog').count(),
            'cats': AnimalReport.objects.filter(animal_type='cat').count(),
            'other': AnimalReport.objects.filter(animal_type='other').count(),
        },
    }
    return render(request, 'dashboard.html', context)


@login_required
@role_required('admin')
@require_POST
def admin_toggle_user_active(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    if target == request.user:
        messages.error(request, 'You cannot deactivate your own admin account.')
        return redirect('dashboard')
    target.is_active = not target.is_active
    target.save(update_fields=['is_active'])
    _admin_log(request, 'user_toggle', target.username, f"User active status changed to {'active' if target.is_active else 'inactive'}.")
    messages.success(request, f"{target.username} is now {'active' if target.is_active else 'inactive'}.")
    return redirect('dashboard')


@login_required
@role_required('admin')
@require_POST
def admin_toggle_org_active(request, org_id):
    org = get_object_or_404(RescueOrganization, pk=org_id)
    org.is_active = not org.is_active
    org.save(update_fields=['is_active'])
    _admin_log(request, 'org_toggle', org.name, f"Organization active status changed to {'active' if org.is_active else 'inactive'}.")
    messages.success(request, f"{org.name} is now {'active' if org.is_active else 'inactive'}.")
    return redirect('dashboard')


@login_required
@role_required('admin')
@require_POST
def admin_update_report_status(request, report_id):
    report = get_object_or_404(AnimalReport, pk=report_id)
    new_status = request.POST.get('status', '').strip()
    if new_status not in dict(AnimalReport.STATUS_CHOICES):
        messages.error(request, 'Invalid report status.')
        return redirect('dashboard')
    old_status = report.get_status_display()
    report.status = new_status
    report.save(update_fields=['status', 'updated_at'])
    _admin_log(request, 'report_status', f'Report #{report.pk}', f"Status changed from {old_status} to {report.get_status_display()}.")
    messages.success(request, f'Report #{report.pk} status updated to {report.get_status_display()}.')
    return redirect('dashboard')



@login_required
@role_required('admin')
def admin_export_reports_csv(request):
    response = _csv_response('admin_reports_export.csv')
    writer = csv.writer(response)
    writer.writerow(['Report ID', 'Animal Type', 'Condition', 'Reporter', 'Organization', 'Location', 'Latitude', 'Longitude', 'Priority', 'Status', 'Reported At', 'Updated At', 'Description'])
    qs = AnimalReport.objects.select_related('reporter', 'rescue_org').order_by('-reported_at')
    for report in qs:
        writer.writerow([
            report.pk,
            report.get_animal_type_display(),
            report.get_condition_display(),
            report.reporter.get_full_name() or report.reporter.username if report.reporter else 'Anonymous',
            report.rescue_org.name if report.rescue_org else 'Unassigned',
            report.location,
            report.latitude or '',
            report.longitude or '',
            report.get_priority_display(),
            report.get_status_display(),
            report.reported_at.strftime('%Y-%m-%d %H:%M') if report.reported_at else '',
            report.updated_at.strftime('%Y-%m-%d %H:%M') if report.updated_at else '',
            report.description,
        ])
    _admin_log(request, 'export', 'Admin Reports CSV', 'Exported all rescue reports from the admin dashboard.')
    return response


@login_required
@role_required('admin')
def admin_export_activity_csv(request):
    response = _csv_response('admin_monthly_activity_export.csv')
    writer = csv.writer(response)
    writer.writerow(['Month', 'Reports', 'Rescued/Completed Reports'])
    today = date.today()
    for offset in range(11, -1, -1):
        target_month = today.month - offset
        target_year = today.year
        while target_month <= 0:
            target_month += 12
            target_year -= 1
        month_start = date(target_year, target_month, 1)
        if target_month == 12:
            month_end = date(target_year + 1, 1, 1)
        else:
            month_end = date(target_year, target_month + 1, 1)
        writer.writerow([
            month_start.strftime('%b %Y'),
            AnimalReport.objects.filter(reported_at__gte=month_start, reported_at__lt=month_end).count(),
            AnimalReport.objects.filter(reported_at__gte=month_start, reported_at__lt=month_end, status__in=['rescued', 'in_treatment', 'ready_for_adoption', 'adopted', 'closed']).count(),
        ])
    _admin_log(request, 'export', 'Admin Activity CSV', 'Exported monthly activity chart data from the admin dashboard.')
    return response


# ══════════════════════════════════════════════════
#  ORG-FACING ACTIONS  (POST endpoints)
# ══════════════════════════════════════════════════

def _ensure_rescued_animal_for_report(report):
    """Create or reuse a RescuedAnimal for a report marked as rescued."""
    animal, created = RescuedAnimal.objects.get_or_create(
        source_report=report,
        defaults={
            'rescue_org': report.rescue_org,
            'name': '',
            'species': report.animal_type,
            'breed': '',
            'sex': 'unknown',
            'approx_age': '',
            'color': '',
            'status': 'recovering',
            'vaccination': 'none',
            'shelter': report.location,
            'medical_notes': f'Rescued from report #{report.pk}: {report.get_condition_display()}. {report.description}',
            'temperament': '',
            'adoption_open': False,
        }
    )

    # Ensure rescued animal stays linked and in recovering status
    updated = False
    if animal.rescue_org != report.rescue_org:
        animal.rescue_org = report.rescue_org
        updated = True
    if animal.status != 'recovering':
        animal.status = 'recovering'
        updated = True
    if animal.adoption_open:
        animal.adoption_open = False
        updated = True
    if animal.source_report_id != report.pk:
        animal.source_report = report
        updated = True
    if updated:
        animal.save()

    return animal


@login_required
@role_required('rescue_org')
@require_POST
def org_update_report(request, report_id):
    """Org updates the status / response notes on a rescue report."""
    profile = _get_or_create_profile(request.user)
    report  = get_object_or_404(AnimalReport, pk=report_id, rescue_org=profile.organization)

    new_status = request.POST.get('status')
    notes      = request.POST.get('response_notes', '').strip()

    if new_status:
        if new_status not in dict(AnimalReport.STATUS_CHOICES):
            if _wants_json(request):
                return JsonResponse({'ok': False, 'error': 'Invalid report status.'}, status=400)
            messages.error(request, 'Invalid report status.')
            return redirect('dashboard')
        report.status = new_status
    if notes:
        report.response_notes = notes
    report.save()

    if new_status == 'rescued':
        _ensure_rescued_animal_for_report(report)

    # Handle additional photos
    for f in request.FILES.getlist('photos'):
        AnimalReportPhoto.objects.create(report=report, image=f)

    # Notify the original reporter
    if report.reporter:
        Notification.objects.create(
            recipient=report.reporter,
            type='rescue_update',
            title=f'Update on your report #{report.pk}',
            body=f'Status changed to: {report.get_status_display()}. {notes}',
            report=report,
        )

    messages.success(request, 'Report updated successfully.')
    if _wants_json(request):
        return JsonResponse({'ok': True, 'status': report.status, 'status_display': report.get_status_display()})
    return redirect('dashboard')


@login_required
@role_required('rescue_org')
@require_POST
def org_add_animal(request):
    """Org creates a new rescued animal profile."""
    profile = _get_or_create_profile(request.user)
    if not profile.organization:
        return JsonResponse({'error': 'No organization linked.'}, status=403)

    species = request.POST.get('species', 'dog')
    sex = request.POST.get('sex', 'unknown')
    status = request.POST.get('status', 'observation')
    vaccination = request.POST.get('vaccination', 'none')

    if species not in dict(RescuedAnimal.SPECIES_CHOICES):
        species = 'dog'
    if sex not in dict(RescuedAnimal.SEX_CHOICES):
        sex = 'unknown'
    if status not in dict(RescuedAnimal.STATUS_CHOICES):
        status = 'observation'
    if vaccination not in dict(RescuedAnimal.VACCINATION_CHOICES):
        vaccination = 'none'

    animal = RescuedAnimal.objects.create(
        rescue_org    = profile.organization,
        name          = request.POST.get('name', '').strip(),
        species       = species,
        sex           = sex,
        approx_age    = request.POST.get('approx_age', '').strip(),
        color         = request.POST.get('color', '').strip(),
        breed         = request.POST.get('breed', '').strip(),
        status        = status,
        vaccination   = vaccination,
        shelter       = request.POST.get('shelter', '').strip(),
        medical_notes = request.POST.get('medical_notes', '').strip(),
        temperament   = request.POST.get('temperament', '').strip(),
    )

    # Link to source report if provided
    source_id = request.POST.get('source_report_id')
    if source_id:
        try:
            animal.source_report = AnimalReport.objects.get(pk=source_id)
            animal.save()
        except AnimalReport.DoesNotExist:
            pass

    # Handle photo uploads
    for i, f in enumerate(request.FILES.getlist('photos')):
        RescuedAnimalPhoto.objects.create(
            animal=animal, image=f, is_primary=(i == 0)
        )

    messages.success(request, f'Animal profile for "{animal.display_name()}" created.')
    return redirect('dashboard')


@login_required
@role_required('rescue_org')
@require_POST
def org_edit_animal(request, animal_id):
    """Org edits an existing rescued animal profile."""
    profile = _get_or_create_profile(request.user)
    animal  = get_object_or_404(RescuedAnimal, pk=animal_id, rescue_org=profile.organization)

    animal.name          = request.POST.get('name', animal.name).strip()
    animal.species       = request.POST.get('species', animal.species)
    animal.sex           = request.POST.get('sex', animal.sex)
    animal.approx_age    = request.POST.get('approx_age', animal.approx_age).strip()
    animal.color         = request.POST.get('color', animal.color).strip()
    animal.breed         = request.POST.get('breed', animal.breed).strip()
    animal.status        = request.POST.get('status', animal.status)
    animal.vaccination   = request.POST.get('vaccination', animal.vaccination)
    animal.shelter       = request.POST.get('shelter', animal.shelter).strip()
    animal.medical_notes = request.POST.get('medical_notes', animal.medical_notes).strip()
    animal.temperament   = request.POST.get('temperament', animal.temperament).strip()
    animal.adoption_open = request.POST.get('adoption_open') == 'on'
    animal.save()

    for f in request.FILES.getlist('photos'):
        RescuedAnimalPhoto.objects.create(animal=animal, image=f)

    # If status changed to 'adoption', notify users who saved this animal
    if animal.status == 'adoption':
        saved_users = SavedAnimal.objects.filter(animal=animal).select_related('user')
        for sv in saved_users:
            Notification.objects.get_or_create(
                recipient=sv.user,
                type='adoption_ready',
                animal=animal,
                defaults={
                    'title': f'{animal.display_name()} is now ready for adoption!',
                    'body':  f'Good news! {animal.display_name()} at {profile.organization.name} has completed recovery and is available for adoption.',
                }
            )

    messages.success(request, 'Animal profile updated.')
    return redirect('dashboard')


@login_required
@role_required('rescue_org')
@require_POST
def org_toggle_adoption(request, animal_id):
    """AJAX: toggle adoption_open flag on a rescued animal."""
    profile = _get_or_create_profile(request.user)
    animal  = get_object_or_404(RescuedAnimal, pk=animal_id, rescue_org=profile.organization)

    animal.adoption_open = not animal.adoption_open
    if animal.adoption_open:
        animal.status = 'adoption'
    animal.save()

    return JsonResponse({'adoption_open': animal.adoption_open, 'status': animal.status})


@login_required
@role_required('rescue_org')
@require_POST
def org_post_announcement(request):
    """Org posts a new announcement."""
    profile = _get_or_create_profile(request.user)
    if not profile.organization:
        return JsonResponse({'error': 'No organization linked.'}, status=403)

    ann = Announcement.objects.create(
        rescue_org = profile.organization,
        posted_by  = request.user,
        type       = request.POST.get('type', 'update'),
        title      = request.POST.get('title', '').strip(),
        body       = request.POST.get('body', '').strip(),
    )
    if 'photo' in request.FILES:
        ann.photo = request.FILES['photo']
        ann.save()

    messages.success(request, 'Announcement published.')
    return redirect('dashboard')


@login_required
@role_required('rescue_org')
@require_POST
def org_send_message(request):
    """Org replies to a user's message."""
    profile      = _get_or_create_profile(request.user)
    recipient_id = request.POST.get('recipient_id')
    body         = request.POST.get('body', '').strip()

    if not body or not recipient_id:
        return JsonResponse({'error': 'Missing fields.'}, status=400)

    recipient = get_object_or_404(User, pk=recipient_id)
    inquiry_id = request.POST.get('inquiry_id')
    inquiry = None
    if inquiry_id:
        try:
            inquiry = AdoptionInquiry.objects.get(pk=inquiry_id)
        except AdoptionInquiry.DoesNotExist:
            inquiry = None

    conv = None
    conv_id = request.POST.get('conversation_id')
    if conv_id:
        try:
            conv = Conversation.objects.get(pk=conv_id)
        except Conversation.DoesNotExist:
            conv = None

    if conv is None:
        conv = Conversation.objects.filter(participants=request.user).filter(participants=recipient).order_by('-updated_at').first()

    if conv is None:
        conv = Conversation.objects.create(subject=request.POST.get('subject', '') or '', inquiry=inquiry)
        conv.participants.add(request.user, recipient)
    elif inquiry and conv.inquiry_id != inquiry.pk:
        conv.inquiry = inquiry
        conv.save(update_fields=['inquiry'])

    if inquiry and not conv.participants.filter(pk=recipient.pk).exists():
        conv.participants.add(recipient)
    if inquiry and not conv.participants.filter(pk=request.user.pk).exists():
        conv.participants.add(request.user)

    msg = Message.objects.create(
        sender    = request.user,
        recipient = recipient,
        conversation = conv,
        inquiry   = inquiry,
        body      = body,
        subject   = request.POST.get('subject', ''),
    )

    # Link optional context
    animal_id = request.POST.get('animal_id')
    if animal_id:
        try:
            msg.animal = RescuedAnimal.objects.get(pk=animal_id)
            msg.save()
        except RescuedAnimal.DoesNotExist:
            pass

    if inquiry:
        Notification.objects.create(
            recipient=inquiry.user,
            type='org_reply',
            title=f'{profile.organization.name if profile.organization else request.user.username} replied to you',
            body=body[:200],
            inquiry=inquiry,
            animal=inquiry.animal,
        )
    else:
        Notification.objects.create(
            recipient=recipient,
            type='org_reply',
            title=f'{profile.organization.name if profile.organization else request.user.username} replied to you',
            body=body[:200],
        )

    # Update conversation last message and timestamp
    conv.last_message = msg
    conv.updated_at = timezone.now()
    conv.save()

    return JsonResponse({'ok': True, 'message_id': msg.pk})


@login_required
@role_required('rescue_org')
@require_POST
def org_update_inquiry_status(request, inquiry_id):
    """Org updates the status of an adoption inquiry and notifies the user."""
    profile = _get_or_create_profile(request.user)
    inquiry = get_object_or_404(AdoptionInquiry, pk=inquiry_id, rescue_org=profile.organization)

    new_status = request.POST.get('status')
    if new_status not in dict(AdoptionInquiry.STATUS_CHOICES):
        return JsonResponse({'error': 'Invalid status.'}, status=400)

    inquiry.status = new_status
    inquiry.save(update_fields=['status', 'updated_at'])

    Notification.objects.create(
        recipient=inquiry.user,
        type='inquiry_status_updated',
        title=f'Adoption inquiry updated to {inquiry.get_status_display()}',
        body=f'Your inquiry for {inquiry.animal.display_name()} is now {inquiry.get_status_display()}.',
        inquiry=inquiry,
        animal=inquiry.animal,
    )

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'ok': True,
            'status': inquiry.status,
            'status_display': inquiry.get_status_display(),
        })

    messages.success(request, 'Inquiry status updated.')
    return redirect('dashboard')


# ══════════════════════════════════════════════════
#  USER-FACING ACTIONS  (POST endpoints)
# ══════════════════════════════════════════════════

@api_login_required
@role_required('reporter')
@require_POST
def user_submit_report(request):
    """User submits a new rescue report."""
    animal_type = request.POST.get('animal_type', 'dog')
    condition = request.POST.get('condition', 'stray')
    priority = request.POST.get('priority', 'normal')
    description = request.POST.get('description', '').strip()
    location = request.POST.get('location', '').strip()

    if animal_type not in dict(AnimalReport.ANIMAL_TYPE_CHOICES):
        return JsonResponse({'ok': False, 'error': 'Please choose a valid animal type.'}, status=400)
    if condition not in dict(AnimalReport.CONDITION_CHOICES):
        return JsonResponse({'ok': False, 'error': 'Please choose a valid condition.'}, status=400)
    if priority not in dict(AnimalReport.PRIORITY_CHOICES):
        return JsonResponse({'ok': False, 'error': 'Please choose a valid priority.'}, status=400)
    if not description or not location:
        return JsonResponse({'ok': False, 'error': 'Description and location are required.'}, status=400)

    uploaded_files = []
    if 'photo' in request.FILES:
        uploaded_files.append(request.FILES['photo'])
    uploaded_files.extend(request.FILES.getlist('photos'))

    valid, validation_error = _validate_uploaded_files(uploaded_files)
    if not valid:
        return JsonResponse({'ok': False, 'error': validation_error}, status=400)

    latitude_value = request.POST.get('latitude', '').strip() or None
    longitude_value = request.POST.get('longitude', '').strip() or None
    try:
        latitude_value = float(latitude_value) if latitude_value is not None else None
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'Latitude must be a valid number.'}, status=400)
    try:
        longitude_value = float(longitude_value) if longitude_value is not None else None
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'Longitude must be a valid number.'}, status=400)

    if latitude_value is not None and not (-90.0 <= latitude_value <= 90.0):
        return JsonResponse({'ok': False, 'error': 'Latitude must be between -90 and 90.'}, status=400)
    if longitude_value is not None and not (-180.0 <= longitude_value <= 180.0):
        return JsonResponse({'ok': False, 'error': 'Longitude must be between -180 and 180.'}, status=400)

    report = AnimalReport.objects.create(
        reporter    = request.user,
        animal_type = animal_type,
        condition   = condition,
        priority    = priority,
        description = description,
        location    = location,
        latitude    = latitude_value,
        longitude   = longitude_value,
        status      = 'pending',
    )

    # Primary photo
    if 'photo' in request.FILES:
        report.photo = request.FILES['photo']
        report.save()

    # Additional photos
    for f in request.FILES.getlist('photos'):
        AnimalReportPhoto.objects.create(report=report, image=f)

    # Auto-assign to an active org: prefer nearest org when coordinates provided
    org = None
    if latitude_value is not None and longitude_value is not None:
        active_orgs = RescueOrganization.objects.filter(is_active=True).exclude(latitude__isnull=True).exclude(longitude__isnull=True)
        nearest = None
        min_dist = None
        for o in active_orgs:
            try:
                dx = float(o.latitude) - float(latitude_value)
                dy = float(o.longitude) - float(longitude_value)
            except Exception:
                continue
            dist = dx * dx + dy * dy
            if min_dist is None or dist < min_dist:
                min_dist = dist
                nearest = o
        org = nearest or RescueOrganization.objects.filter(is_active=True).first()
    else:
        org = RescueOrganization.objects.filter(is_active=True).first()

    if org:
        report.rescue_org = org
        report.save()

        # Notify all org members
        org_members = UserProfile.objects.filter(organization=org, role='rescue_org').select_related('user')
        for member in org_members:
            Notification.objects.create(
                recipient=member.user,
                type='new_report',
                title=f'New rescue report #{report.pk} assigned',
                body=f'{report.get_animal_type_display()} ({report.get_condition_display()}) at {report.location}',
                report=report,
            )

    # Notify the reporter
    Notification.objects.create(
        recipient=request.user,
        type='rescue_update',
        title=f'Report #{report.pk} submitted successfully',
        body=f'Your report has been received. {"Assigned to " + org.name + "." if org else "Awaiting assignment."}',
        report=report,
    )

    return JsonResponse({'ok': True, 'report_id': report.pk, 'report_number': report.pk})


@login_required
@role_required('reporter')
@require_POST
def user_toggle_save(request, animal_id):
    """AJAX: toggle saved/unsaved state for an animal."""
    animal = get_object_or_404(RescuedAnimal, pk=animal_id)
    saved, created = SavedAnimal.objects.get_or_create(user=request.user, animal=animal)
    if not created:
        saved.delete()
        return JsonResponse({'saved': False})
    return JsonResponse({'saved': True})


@login_required
@role_required('reporter')
@require_POST
def user_send_inquiry(request):
    """User submits an adoption inquiry."""
    animal_id = request.POST.get('animal_id')
    animal    = get_object_or_404(RescuedAnimal, pk=animal_id, adoption_open=True)

    # One inquiry per user per animal (update if already exists)
    inquiry, created = AdoptionInquiry.objects.update_or_create(
        user=request.user,
        animal=animal,
        defaults={
            'rescue_org':       animal.rescue_org,
            'living_situation': request.POST.get('living_situation', 'house'),
            'other_pets':       request.POST.get('other_pets', 'none'),
            'message':          request.POST.get('message', '').strip(),
            'status':           'pending',
        }
    )

    conversation = None
    conversation_id = request.POST.get('conversation_id')
    if conversation_id:
        try:
            conversation = Conversation.objects.get(pk=conversation_id, inquiry=inquiry)
        except Conversation.DoesNotExist:
            conversation = None

    if conversation is None:
        conversation = Conversation.objects.filter(inquiry=inquiry).order_by('-updated_at').first()

    if conversation is None:
        conversation = Conversation.objects.create(subject=f'Inquiry for {animal.display_name()}', inquiry=inquiry)
        conversation.participants.add(request.user)

    if animal.rescue_org:
        org_members = UserProfile.objects.filter(
            organization=animal.rescue_org, role='rescue_org'
        ).select_related('user')
        for member in org_members:
            Notification.objects.create(
                recipient=member.user,
                type='new_inquiry',
                title=f'New adoption inquiry for {animal.display_name()}',
                body=f'{request.user.get_full_name() or request.user.username} is interested in adopting {animal.display_name()}.',
                animal=animal,
                inquiry=inquiry,
            )
            if not conversation.participants.filter(pk=member.user.pk).exists():
                conversation.participants.add(member.user)

    if not conversation.participants.filter(pk=request.user.pk).exists():
        conversation.participants.add(request.user)

    message_body = (request.POST.get('message', '') or '').strip()
    if message_body:
        message = Message.objects.create(
            sender=request.user,
            recipient=animal.rescue_org.members.first().user if animal.rescue_org and animal.rescue_org.members.exists() else request.user,
            conversation=conversation,
            inquiry=inquiry,
            body=message_body,
            subject='Inquiry message',
        )
        conversation.last_message = message
        conversation.updated_at = timezone.now()
        conversation.save()

    return JsonResponse({'ok': True, 'inquiry_id': inquiry.pk, 'conversation_id': conversation.pk})


@login_required
@role_required('reporter')
@require_POST
def user_send_message(request):
    """User sends a message to a rescue org member."""
    recipient_id = request.POST.get('recipient_id')
    body         = request.POST.get('body', '').strip()

    if not body or not recipient_id:
        return JsonResponse({'error': 'Missing fields.'}, status=400)

    recipient = get_object_or_404(User, pk=recipient_id)
    inquiry_id = request.POST.get('inquiry_id')
    inquiry = None
    if inquiry_id:
        try:
            inquiry = AdoptionInquiry.objects.get(pk=inquiry_id)
        except AdoptionInquiry.DoesNotExist:
            inquiry = None

    # Conversation handling: prefer explicit conversation_id, else find or create between participants
    conv = None
    conv_id = request.POST.get('conversation_id')
    if conv_id:
        try:
            conv = Conversation.objects.get(pk=conv_id)
        except Conversation.DoesNotExist:
            conv = None

    if conv is None:
        conv = Conversation.objects.filter(participants=request.user).filter(participants=recipient).order_by('-updated_at').first()

    if conv is None:
        conv = Conversation.objects.create(subject=request.POST.get('subject', '') or '', inquiry=inquiry)
        conv.participants.add(request.user, recipient)
    elif inquiry and conv.inquiry_id != inquiry.pk:
        conv.inquiry = inquiry
        conv.save(update_fields=['inquiry'])

    if inquiry and not conv.participants.filter(pk=recipient.pk).exists():
        conv.participants.add(recipient)
    if inquiry and not conv.participants.filter(pk=request.user.pk).exists():
        conv.participants.add(request.user)

    msg = Message.objects.create(
        sender    = request.user,
        recipient = recipient,
        conversation = conv,
        inquiry   = inquiry,
        body      = body,
        subject   = request.POST.get('subject', ''),
    )

    animal_id = request.POST.get('animal_id')
    if animal_id:
        try:
            msg.animal = RescuedAnimal.objects.get(pk=animal_id)
            msg.save()
        except RescuedAnimal.DoesNotExist:
            pass

    if inquiry:
        if request.user == inquiry.user:
            Notification.objects.create(
                recipient=recipient,
                type='new_user_message',
                title=f'New message from {request.user.get_full_name() or request.user.username}',
                body=body[:200],
                inquiry=inquiry,
                animal=inquiry.animal,
            )
        else:
            Notification.objects.create(
                recipient=inquiry.user,
                type='org_reply',
                title=f'Update on your adoption inquiry for {inquiry.animal.display_name()}',
                body=body[:200],
                inquiry=inquiry,
                animal=inquiry.animal,
            )
    else:
        Notification.objects.create(
            recipient=recipient,
            type='new_user_message',
            title=f'New message from {request.user.get_full_name() or request.user.username}',
            body=body[:200],
        )

    # Update conversation last message and timestamp
    conv.last_message = msg
    conv.updated_at = timezone.now()
    conv.save()

    return JsonResponse({'ok': True, 'message_id': msg.pk})


@login_required
@role_required('reporter', 'rescue_org', 'admin')
@require_POST
def user_mark_notifications_read(request):
    """Mark all (or specific) notifications as read."""
    notif_ids = request.POST.getlist('ids')
    qs = Notification.objects.filter(recipient=request.user)
    if notif_ids:
        qs = qs.filter(pk__in=notif_ids)
    updated = qs.update(is_read=True)
    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return JsonResponse({'ok': True, 'updated': updated, 'unread_count': unread_count})


# ══════════════════════════════════════════════════
#  REST API Views using Django REST Framework
# ══════════════════════════════════════════════════

class RescueOrganizationListAPIView(APIView):
    def get(self, request):
        orgs = RescueOrganization.objects.filter(is_active=True).order_by('name')
        serializer = RescueOrganizationSerializer(orgs, many=True, context={'request': request})
        return Response(serializer.data)


class RescuedAnimalListAPIView(APIView):
    def get(self, request):
        animals = RescuedAnimal.objects.filter(adoption_open=True).select_related('rescue_org').order_by('-rescued_at')
        serializer = RescuedAnimalSerializer(animals, many=True, context={'request': request})
        return Response(serializer.data)


class AdoptionInquiryListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = UserProfile.objects.filter(user=request.user).first()
        if not profile or not profile.organization:
            return Response([])

        inquiries = AdoptionInquiry.objects.filter(rescue_org=profile.organization).select_related('user', 'animal', 'rescue_org').order_by('-created_at')
        serializer = AdoptionInquirySerializer(inquiries, many=True, context={'request': request})
        return Response(serializer.data)


# ══════════════════════════════════════════════════
#  JSON / AJAX API ENDPOINTS
# ══════════════════════════════════════════════════

@login_required
@role_required('admin')
def dashboard_stats_api(request):
    """Admin-level stats for the existing Chart.js charts on dashboard.html."""
    today    = date.today()
    monthly  = []
    for i in range(5, -1, -1):
        ms = (today.replace(day=1) - timedelta(days=i * 28)).replace(day=1)
        me = (ms + timedelta(days=32)).replace(day=1)
        monthly.append({
            'month':   ms.strftime('%b'),
            'reports': AnimalReport.objects.filter(reported_at__gte=ms, reported_at__lt=me).count(),
            'rescued': AnimalReport.objects.filter(
                reported_at__gte=ms, reported_at__lt=me,
                status__in=['rescued', 'in_treatment', 'ready_for_adoption', 'adopted']
            ).count(),
        })

    return JsonResponse({
        'total_reports':      AnimalReport.objects.count(),
        'pending_rescues':    AnimalReport.objects.filter(status='pending').count(),
        'rescued_animals':    RescuedAnimal.objects.count(),
        'ready_for_adoption': RescuedAnimal.objects.filter(status='adoption', adoption_open=True).count(),
        'in_treatment':       RescuedAnimal.objects.filter(status__in=['observation', 'recovering']).count(),
        'completed_rescues':  AnimalReport.objects.filter(status__in=['rescued', 'closed', 'ready_for_adoption', 'adopted']).count(),
        'monthly_data':       monthly,
        'animal_breakdown': {
            'dogs':  AnimalReport.objects.filter(animal_type='dog').count(),
            'cats':  AnimalReport.objects.filter(animal_type='cat').count(),
            'other': AnimalReport.objects.filter(animal_type='other').count(),
        },
    })


@login_required
@role_required('admin')
def recent_reports_api(request):
    """Recent reports list for admin dashboard table."""
    reports = AnimalReport.objects.select_related('reporter', 'rescue_org').order_by('-reported_at')[:10]
    data = []
    for r in reports:
        data.append({
            'id':          r.pk,
            'animal_type': r.animal_type,
            'condition':   r.condition,
            'status':      r.status,
            'priority':    r.priority,
            'location':    r.location,
            'description': r.description,
            'reported_at': r.reported_at.isoformat(),
            'reporter':    r.reporter.get_full_name() or r.reporter.username if r.reporter else 'Anonymous',
            'rescue_org':  r.rescue_org.name if r.rescue_org else None,
        })
    return JsonResponse({'reports': data})


@login_required
@role_required('rescue_org')
def org_stats_api(request):
    """JSON stats for the org dashboard's Chart.js charts."""
    profile = _get_or_create_profile(request.user)
    if not profile.organization:
        return JsonResponse({'error': 'No organization linked.'}, status=403)

    org     = profile.organization
    reports = AnimalReport.objects.filter(rescue_org=org)
    animals = RescuedAnimal.objects.filter(rescue_org=org)
    today   = date.today()

    monthly = []
    for i in range(5, -1, -1):
        ms = (today.replace(day=1) - timedelta(days=i * 28)).replace(day=1)
        me = (ms + timedelta(days=32)).replace(day=1)
        monthly.append({
            'month':   ms.strftime('%b'),
            'reports': reports.filter(reported_at__gte=ms, reported_at__lt=me).count(),
            'rescued': reports.filter(
                reported_at__gte=ms, reported_at__lt=me,
                status__in=['rescued', 'in_treatment', 'ready_for_adoption', 'adopted']
            ).count(),
        })

    return JsonResponse({
        'monthly_data': monthly,
        'animal_breakdown': {
            'dogs':  animals.filter(species='dog').count(),
            'cats':  animals.filter(species='cat').count(),
            'other': animals.filter(species='other').count(),
        },
        'status_breakdown': {
            'pending':    reports.filter(status='pending').count(),
            'responding': reports.filter(status='responding').count(),
            'rescued':    reports.filter(status__in=['rescued','in_treatment','ready_for_adoption','adopted']).count(),
            'closed':     reports.filter(status='closed').count(),
        },
    })


@login_required
@role_required('reporter', 'rescue_org', 'admin')
def user_notifications_api(request):
    """JSON list of the current user's notifications."""
    notifs = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:20]
    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    data = [{
        'id':         n.pk,
        'type':       n.type,
        'title':      n.title,
        'body':       n.body,
        'is_read':    n.is_read,
        'created_at': n.created_at.isoformat(),
        'report_id':  n.report_id,
        'animal_id':  n.animal_id,
    } for n in notifs]
    return JsonResponse({'notifications': data, 'unread': unread_count})


@login_required
@role_required('reporter')
def browse_animals_api(request):
    """Filtered list of animals for the browse tab (supports query params)."""
    qs = RescuedAnimal.objects.filter(adoption_open=True)

    species = request.GET.get('species')
    status  = request.GET.get('status')
    q       = request.GET.get('q', '').strip()

    if species and species != 'all':
        qs = qs.filter(species=species)
    if status and status != 'all':
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(breed__icontains=q) | Q(color__icontains=q))

    saved_ids = list(SavedAnimal.objects.filter(user=request.user).values_list('animal_id', flat=True))

    data = []
    for a in qs.order_by('-rescued_at')[:50]:
        primary_photo = a.photos.filter(is_primary=True).first()
        data.append({
            'id':           a.pk,
            'name':         a.display_name(),
            'species':      a.species,
            'sex':          a.sex,
            'approx_age':   a.approx_age,
            'status':       a.status,
            'vaccination':  a.vaccination,
            'shelter':      a.shelter,
            'rescue_org':   a.rescue_org.name if a.rescue_org else '',
            'is_saved':     a.pk in saved_ids,
            'photo_url':    primary_photo.image.url if primary_photo else None,
        })

    return JsonResponse({'animals': data})


# ══════════════════════════════════════════════════
#  CONVERSATION THREAD VIEW (AJAX)
# ══════════════════════════════════════════════════

@login_required
def message_thread_api(request, other_user_id):
    """Return the full message thread between current user and another user."""
    other = get_object_or_404(User, pk=other_user_id)

    thread = Message.objects.filter(
        Q(sender=request.user, recipient=other) |
        Q(sender=other, recipient=request.user)
    ).order_by('sent_at')

    # Mark received messages as read
    thread.filter(recipient=request.user, is_read=False).update(is_read=True)

    # Try to find an associated conversation (if any)
    conv = Conversation.objects.filter(participants=request.user).filter(participants=other).order_by('-updated_at').first()

    data = [{
        'id':        m.pk,
        'from_me':   m.sender_id == request.user.pk,
        'sender':    m.sender.get_full_name() or m.sender.username,
        'body':      m.body,
        'sent_at':   m.sent_at.isoformat(),
        'animal_id': m.animal_id,
    } for m in thread]

    resp = {'messages': data, 'other_user': other.get_full_name() or other.username}
    if conv:
        resp['conversation_id'] = conv.pk
        if conv.last_message:
            resp['conversation_last_message_id'] = conv.last_message_id

    return JsonResponse(resp)


@login_required
def conversations_api(request):
    """Return a list of conversations for the current user with metadata."""
    qs = Conversation.objects.filter(participants=request.user).order_by('-updated_at')[:50]
    data = []
    for c in qs:
        last = c.last_message
        # unread messages in this conversation for the current user
        unread = Message.objects.filter(conversation=c, recipient=request.user, is_read=False).count()
        participants = []
        for p in c.participants.exclude(pk=request.user.pk):
            participants.append({'id': p.pk, 'name': p.get_full_name() or p.username})

        data.append({
            'id': c.pk,
            'subject': c.subject,
            'participants': participants,
            'last_message': {
                'id': last.pk if last else None,
                'sender_id': last.sender_id if last else None,
                'body_preview': (last.body[:200] if last else ''),
                'sent_at': last.sent_at.isoformat() if last else None,
            },
            'unread': unread,
        })

    return JsonResponse({'conversations': data})


@login_required
def animal_detail_api(request, animal_id):
    """Return detailed info for a single animal (for modal display)."""
    animal = get_object_or_404(RescuedAnimal, pk=animal_id)
    
    # Check if user has saved this animal
    is_saved = SavedAnimal.objects.filter(user=request.user, animal=animal).exists()
    
    # Get primary photo
    primary_photo = animal.photos.filter(is_primary=True).first()
    
    data = {
        'id':           animal.pk,
        'name':         animal.display_name(),
        'species':      animal.get_species_display(),
        'breed':        animal.breed or 'Unknown',
        'sex':          animal.get_sex_display(),
        'approx_age':   animal.approx_age or 'Unknown',
        'color':        animal.color or 'Unknown',
        'status':       animal.get_status_display(),
        'vaccination':  animal.get_vaccination_display(),
        'temperament':  animal.temperament or 'Not available',
        'medical_notes':animal.medical_notes or 'None',
        'shelter':      animal.shelter or 'Unknown',
        'rescue_org':   animal.rescue_org.name if animal.rescue_org else 'Unknown',
        'is_saved':     is_saved,
        'adoption_open':animal.adoption_open,
        'photo_url':    primary_photo.image.url if primary_photo else None,
        'source_report':animal.source_report_id,
    }
    return JsonResponse(data)
