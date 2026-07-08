from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Count, Max, Q, Prefetch
from django.utils import timezone
from datetime import date, timedelta
import json
import csv

from .models import RescueOrganization, Announcement
from accounts.models import UserProfile, AdoptionInquiry, Notification, Message
from animals.models import RescuedAnimal
from reports.models import AnimalReport
from django.contrib.auth.models import User
from core.views import _unread_count, _build_pagination_context, _trend_summary


def _org_csv_response(filename):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write('\ufeff')
    return response


def _org_dashboard(request, profile):
    org = profile.organization

    if org is None:
        messages.warning(request, 'Your account is not linked to a rescue organization. Contact an admin.')
        return render(request, 'org_dashboard.html', {'user': request.user, 'org': None, 'page_title': 'Organization Dashboard'})

    reports = AnimalReport.objects.filter(rescue_org=org).select_related('reporter').prefetch_related('photos')
    animals = RescuedAnimal.objects.filter(rescue_org=org)
    today = date.today()

    total_active = reports.filter(status__in=['pending', 'responding', 'rescued', 'under_observation', 'in_treatment']).count()
    under_recovery = animals.filter(status='recovering').count()
    ready_for_adoption = animals.filter(status='adoption').count()
    new_reports_today = reports.filter(reported_at__date=today).count()

    yesterday = today - timedelta(days=1)
    active_cases_previous = reports.filter(status__in=['pending', 'responding', 'rescued', 'under_observation', 'in_treatment'], reported_at__date=yesterday).count()
    recovery_previous = animals.filter(status='recovering', updated_at__date=yesterday).count()
    adoption_previous = animals.filter(status='adoption', updated_at__date=yesterday).count()
    new_reports_previous = reports.filter(reported_at__date=yesterday).count()

    recent_reports = reports.order_by('-reported_at')[:10]
    location_reports = reports.order_by('-reported_at')[:50]
    report_locations_json = json.dumps([
        {
            'id': report.id,
            'animal_type': report.get_animal_type_display(),
            'condition': report.get_condition_display(),
            'status': report.status,
            'status_display': report.get_status_display(),
            'priority': report.priority,
            'priority_display': report.get_priority_display(),
            'location': report.location or '',
            'latitude': report.latitude,
            'longitude': report.longitude,
            'reporter': (report.reporter.get_full_name() or report.reporter.username) if report.reporter else 'Unknown reporter',
            'reported_at': report.reported_at.strftime('%b %d, %Y %I:%M %p') if report.reported_at else '',
            'description': (report.description or '')[:160],
            'has_coordinates': report.latitude is not None and report.longitude is not None,
        }
        for report in location_reports
    ])

    query = request.GET.get('q', '').strip()
    selected_species = request.GET.get('species', '').strip()
    selected_status = request.GET.get('status', '').strip()

    all_animals = animals.prefetch_related('photos')
    if query:
        all_animals = all_animals.filter(
            Q(name__icontains=query) |
            Q(breed__icontains=query) |
            Q(color__icontains=query)
        )
    if selected_species:
        all_animals = all_animals.filter(species=selected_species)
    if selected_status:
        all_animals = all_animals.filter(status=selected_status)
    all_animals = all_animals.order_by('-rescued_at')

    paginator = Paginator(all_animals, 6)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    except EmptyPage:
        page_obj = paginator.get_page(paginator.num_pages)
    visible_animals = page_obj.object_list

    org_animals_json = json.dumps([
        {
            'id': animal.id,
            'name': animal.name,
            'species': animal.species,
            'species_display': animal.get_species_display(),
            'sex': animal.sex,
            'sex_display': animal.get_sex_display(),
            'breed': animal.breed,
            'approx_age': animal.approx_age,
            'color': animal.color,
            'status': animal.status,
            'status_display': animal.get_status_display(),
            'vaccination': animal.vaccination,
            'vaccination_display': animal.get_vaccination_display(),
            'shelter': animal.shelter,
            'medical_notes': animal.medical_notes,
            'temperament': animal.temperament,
            'adoption_open': animal.adoption_open,
            'rescued_at_display': animal.rescued_at.strftime('%B %d, %Y') if animal.rescued_at else '',
            'rescue_org_name': animal.rescue_org.name if animal.rescue_org else '',
            'primary_photo_url': animal.photos.first().image.url if animal.photos.first() else '',
        }
        for animal in visible_animals
    ])

    adoption_animals = animals.filter(status='adoption').annotate(
        inquiry_count=Count('inquiries')
    )

    # Active announcements
    announcements = Announcement.objects.filter(rescue_org=org, is_active=True).order_by('-created_at')[:10]

    # Archived announcements (soft-deleted)
    archived_announcements = Announcement.objects.filter(rescue_org=org, is_active=False).order_by('-created_at')
    show_archived = bool(request.GET.get('archived'))

    unread_messages = Message.objects.filter(recipient=request.user, is_read=False).count()

    recent_inquiries = AdoptionInquiry.objects.filter(rescue_org=org).select_related('user', 'animal', 'rescue_org').prefetch_related(
        Prefetch('messages', queryset=Message.objects.order_by('sent_at'))
    ).order_by('-created_at')[:10]

    total_reports = reports.count()
    status_critical = reports.filter(priority='critical').count()
    status_pending = reports.filter(status='pending').count()
    status_responding = reports.filter(status='responding').count()
    status_rescued = reports.filter(status__in=['rescued','in_treatment','ready_for_adoption','adopted']).count()
    status_closed = reports.filter(status='closed').count()
    status_pending_percentage = round((status_pending / total_reports * 100) if total_reports else 0, 1)
    status_responding_percentage = round((status_responding / total_reports * 100) if total_reports else 0, 1)
    status_rescued_percentage = round((status_rescued / total_reports * 100) if total_reports else 0, 1)
    status_closed_percentage = round((status_closed / total_reports * 100) if total_reports else 0, 1)

    recent_activity = []
    for report in reports.order_by('-reported_at')[:6]:
        recent_activity.append({
            'timestamp': report.reported_at,
            'icon': '🚨',
            'color': 'var(--red-lt)',
            'title': f'New report #{report.pk} received',
            'detail': f'{report.get_animal_type_display()} reported at {report.location}',
        })

    for animal in animals.order_by('-updated_at')[:6]:
        if animal.status == 'recovering':
            recent_activity.append({
                'timestamp': animal.updated_at,
                'icon': '🏥',
                'color': 'var(--teal-lt)',
                'title': f'{animal.display_name()} moved to recovery',
                'detail': f'{animal.get_species_display()} is now under recovery.',
            })
        elif animal.status == 'adoption':
            recent_activity.append({
                'timestamp': animal.updated_at,
                'icon': '🏡',
                'color': 'var(--sage-lt)',
                'title': f'{animal.display_name()} marked ready for adoption',
                'detail': 'The animal profile is now available for adoption.',
            })
        elif animal.status == 'adopted':
            recent_activity.append({
                'timestamp': animal.updated_at,
                'icon': '✅',
                'color': 'var(--sage-lt)',
                'title': f'{animal.display_name()} rescued successfully',
                'detail': 'This animal has completed the rescue journey.',
            })

    for inquiry in recent_inquiries[:6]:
        recent_activity.append({
            'timestamp': inquiry.created_at,
            'icon': '💬',
            'color': 'var(--blue-lt)',
            'title': f'New inquiry for {inquiry.animal.display_name()}',
            'detail': f'From {inquiry.user.get_full_name() or inquiry.user.username}.',
        })

    for message in Message.objects.filter(recipient=request.user).order_by('-sent_at')[:6]:
        recent_activity.append({
            'timestamp': message.sent_at,
            'icon': '✉️',
            'color': 'var(--amber-lt)',
            'title': f'Message from {message.sender.get_full_name() or message.sender.username}',
            'detail': message.subject or 'New message received.',
        })

    recent_activity = sorted(recent_activity, key=lambda item: item['timestamp'], reverse=True)[:8]

    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
    unread_count = notifications.filter(is_read=False).count()
    recent_messages = Message.objects.filter(Q(sender=request.user) | Q(recipient=request.user)).order_by('-sent_at')[:10]

    conversations = Message.objects.filter(recipient=request.user).values('sender').annotate(
        last_sent=Max('sent_at'),
        unread=Count('id', filter=Q(is_read=False))
    ).order_by('-last_sent')[:20]

    conv_users = []
    for c in conversations:
        try:
            sender = User.objects.get(pk=c['sender'])
            c['sender_obj'] = sender
            conv_users.append(c)
        except User.DoesNotExist:
            pass

    monthly_data = []
    for offset in range(11, -1, -1):
        target_month = today.month - offset
        target_year = today.year
        while target_month <= 0:
            target_month += 12
            target_year -= 1
        month_start = date(target_year, target_month, 1)
        if target_month == 12:
            next_year, next_month = target_year + 1, 1
        else:
            next_year, next_month = target_year, target_month + 1
        month_end = date(next_year, next_month, 1)
        monthly_data.append({
            'month': month_start.strftime('%b'),
            'reports': reports.filter(reported_at__gte=month_start, reported_at__lt=month_end).count(),
            'rescued': reports.filter(reported_at__gte=month_start, reported_at__lt=month_end,
                                      status__in=['rescued', 'in_treatment', 'ready_for_adoption', 'adopted']).count(),
        })

    pagination_context = _build_pagination_context(request, page_obj)
    context = {
        'user': request.user,
        'profile': profile,
        'org': org,
        'page_title': 'Organization Dashboard',
        'total_active': total_active,
        'under_recovery': under_recovery,
        'ready_for_adoption': ready_for_adoption,
        'new_reports_today': new_reports_today,
        'active_cases_trend_text': _trend_summary(total_active, active_cases_previous, 'yesterday')['text'],
        'active_cases_trend_class': f"delta-{_trend_summary(total_active, active_cases_previous, 'yesterday')['direction']}",
        'under_recovery_trend_text': _trend_summary(under_recovery, recovery_previous, 'yesterday')['text'],
        'under_recovery_trend_class': f"delta-{_trend_summary(under_recovery, recovery_previous, 'yesterday')['direction']}",
        'ready_for_adoption_trend_text': _trend_summary(ready_for_adoption, adoption_previous, 'yesterday')['text'],
        'ready_for_adoption_trend_class': f"delta-{_trend_summary(ready_for_adoption, adoption_previous, 'yesterday')['direction']}",
        'new_reports_trend_text': _trend_summary(new_reports_today, new_reports_previous, 'yesterday')['text'],
        'new_reports_trend_class': f"delta-{_trend_summary(new_reports_today, new_reports_previous, 'yesterday')['direction']}",
        'recent_reports': recent_reports,
        'report_locations_json': report_locations_json,
        'all_reports': reports.order_by('-reported_at'),
        'all_animals': visible_animals,
        'org_animals_json': org_animals_json,
        'adoption_animals': adoption_animals,
        'announcements': announcements,
        'archived_announcements': archived_announcements,
        'show_archived': show_archived,
        'recent_inquiries': recent_inquiries,
        'recent_activity': recent_activity,
        'notifications': notifications,
        'recent_messages': recent_messages,
        'conv_users': conv_users,
        'unread_messages': unread_messages,
        'unread_count': unread_count,
        'monthly_data_json': json.dumps(monthly_data),
        'dogs_count': animals.filter(species='dog').count(),
        'cats_count': animals.filter(species='cat').count(),
        'other_count': animals.filter(species='other').count(),
        'status_critical': status_critical,
        'status_pending': status_pending,
        'status_responding': status_responding,
        'status_rescued': status_rescued,
        'status_closed': status_closed,
        'status_pending_percentage': status_pending_percentage,
        'status_responding_percentage': status_responding_percentage,
        'status_rescued_percentage': status_rescued_percentage,
        'status_closed_percentage': status_closed_percentage,
    }
    context.update(pagination_context)
    return render(request, 'org_dashboard.html', context)


@login_required
@require_POST
def org_post_announcement(request):
    profile = UserProfile.objects.filter(user=request.user).first()
    if not profile or not profile.organization:
        return JsonResponse({'error': 'No organization linked.'}, status=403)

    announcement_data = {
        'rescue_org': profile.organization,
        'posted_by': request.user,
        'type': request.POST.get('type', 'update'),
        'title': request.POST.get('title', '').strip(),
        'body': request.POST.get('body', '').strip(),
    }
    if 'photo' in request.FILES:
        announcement_data['photo'] = request.FILES['photo']

    ann = Announcement.objects.create(**announcement_data)

    # Notify reporter users about the new announcement
    reporters = UserProfile.objects.filter(role='reporter').select_related('user')
    notifs = []
    for r in reporters:
        notifs.append(Notification(
            recipient=r.user,
            type='rescue_update',
            title=ann.title,
            body=(ann.body or '')[:200],
        ))
    if notifs:
        Notification.objects.bulk_create(notifs)

    messages.success(request, 'Announcement published.')
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'ok': True})
    return redirect('dashboard')


@login_required
@require_POST
def org_edit_announcement(request, announcement_id):
    profile = UserProfile.objects.filter(user=request.user).first()
    if not profile or not profile.organization:
        return JsonResponse({'error': 'No organization linked.'}, status=403)

    ann = get_object_or_404(Announcement, pk=announcement_id, rescue_org=profile.organization)
    ann.type = request.POST.get('type', ann.type)
    ann.title = request.POST.get('title', ann.title).strip()
    ann.body = request.POST.get('body', ann.body).strip()
    if 'photo' in request.FILES:
        ann.photo = request.FILES['photo']
    ann.save()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'ok': True})
    messages.success(request, 'Announcement updated.')
    return redirect('dashboard')


@login_required
@require_POST
def org_archive_announcement(request, announcement_id):
    profile = UserProfile.objects.filter(user=request.user).first()
    if not profile or not profile.organization:
        return JsonResponse({'error': 'No organization linked.'}, status=403)
    ann = get_object_or_404(Announcement, pk=announcement_id, rescue_org=profile.organization)
    ann.is_active = False
    ann.save(update_fields=['is_active', 'updated_at'])

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'ok': True})
    messages.success(request, 'Announcement archived.')
    return redirect('dashboard')


@login_required
@require_POST
def org_restore_announcement(request, announcement_id):
    profile = UserProfile.objects.filter(user=request.user).first()
    if not profile or not profile.organization:
        return JsonResponse({'error': 'No organization linked.'}, status=403)
    ann = get_object_or_404(Announcement, pk=announcement_id, rescue_org=profile.organization)
    ann.is_active = True
    ann.save(update_fields=['is_active', 'updated_at'])

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'ok': True})
    messages.success(request, 'Announcement restored.')
    return redirect(request.META.get('HTTP_REFERER') or 'dashboard')


@login_required
def org_export_reports_csv(request):
    profile = UserProfile.objects.filter(user=request.user).select_related('organization').first()
    if not profile or not profile.organization:
        return JsonResponse({'error': 'No organization linked.'}, status=403)
    org = profile.organization
    response = _org_csv_response(f'{org.name.lower().replace(" ", "_")}_reports_export.csv')
    writer = csv.writer(response)
    writer.writerow(['Report ID', 'Animal Type', 'Condition', 'Reporter', 'Location', 'Latitude', 'Longitude', 'Priority', 'Status', 'Reported At', 'Updated At', 'Description'])
    for report in AnimalReport.objects.filter(rescue_org=org).select_related('reporter').order_by('-reported_at'):
        writer.writerow([
            report.pk,
            report.get_animal_type_display(),
            report.get_condition_display(),
            report.reporter.get_full_name() or report.reporter.username if report.reporter else 'Anonymous',
            report.location,
            report.latitude or '',
            report.longitude or '',
            report.get_priority_display(),
            report.get_status_display(),
            report.reported_at.strftime('%Y-%m-%d %H:%M') if report.reported_at else '',
            report.updated_at.strftime('%Y-%m-%d %H:%M') if report.updated_at else '',
            report.description,
        ])
    return response


@login_required
def org_export_activity_csv(request):
    profile = UserProfile.objects.filter(user=request.user).select_related('organization').first()
    if not profile or not profile.organization:
        return JsonResponse({'error': 'No organization linked.'}, status=403)
    org = profile.organization
    reports = AnimalReport.objects.filter(rescue_org=org).select_related('reporter').prefetch_related('photos')
    today = date.today()
    response = _org_csv_response(f'{org.name.lower().replace(" ", "_")}_activity_export.csv')
    writer = csv.writer(response)
    writer.writerow(['Month', 'Reports', 'Rescued/Completed Reports'])
    for offset in range(11, -1, -1):
        target_month = today.month - offset
        target_year = today.year
        while target_month <= 0:
            target_month += 12
            target_year -= 1
        month_start = date(target_year, target_month, 1)
        month_end = date(target_year + 1, 1, 1) if target_month == 12 else date(target_year, target_month + 1, 1)
        writer.writerow([
            month_start.strftime('%b %Y'),
            reports.filter(reported_at__gte=month_start, reported_at__lt=month_end).count(),
            reports.filter(reported_at__gte=month_start, reported_at__lt=month_end, status__in=['rescued', 'in_treatment', 'ready_for_adoption', 'adopted', 'closed']).count(),
        ])
    return response
