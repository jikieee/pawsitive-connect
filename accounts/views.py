from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Count, Max, Q
from django.utils import timezone
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from datetime import date, timedelta
import json

# Core helpers
from core.views import _unread_count, _build_pagination_context, _trend_summary, role_required

# Models
from animals.models import RescuedAnimal
from reports.models import AnimalReport
from accounts.models import AdoptionInquiry, UserProfile, SavedAnimal, Notification, Message, Conversation
from organizations.models import RescueOrganization, Announcement
from django.contrib.auth.models import User   # for conversation loop


# ══════════════════════════════════════════════════
#  USER DASHBOARD
# ══════════════════════════════════════════════════

def _user_dashboard(request, profile):
    my_reports     = AnimalReport.objects.filter(reporter=request.user).select_related('rescue_org').prefetch_related('photos').order_by('-reported_at')
    saved_ids      = SavedAnimal.objects.filter(user=request.user).values_list('animal_id', flat=True)
    saved_animals  = RescuedAnimal.objects.filter(pk__in=saved_ids).select_related('rescue_org').prefetch_related('photos')

    # Search + Filter
    query = request.GET.get('q', '').strip()
    selected_species = request.GET.get('species', '').strip()
    selected_status = request.GET.get('status', '').strip()

    # User Browse Animals should only show animals actually managed by rescue organizations.
    # This removes old/unassigned seed/demo animals from the public browse page.
    available_animals = (
        RescuedAnimal.objects
        .filter(rescue_org__isnull=False)
        .exclude(status='adopted')
        .select_related('rescue_org')
        .prefetch_related('photos')
    )

    filtered_animals = available_animals
    if query:
        filtered_animals = filtered_animals.filter(
            Q(name__icontains=query) |
            Q(breed__icontains=query) |
            Q(color__icontains=query)
        )
    if selected_species:
        filtered_animals = filtered_animals.filter(species=selected_species)
    if selected_status:
        filtered_animals = filtered_animals.filter(status=selected_status)

    filtered_animals = filtered_animals.order_by('-rescued_at')
    available_animals_total = filtered_animals.count()

    # Pagination
    paginator = Paginator(filtered_animals, 6)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    except EmptyPage:
        page_obj = paginator.get_page(paginator.num_pages)

    page_animals = page_obj.object_list

    # Other data
    adoption_ready = available_animals.filter(status='adoption', adoption_open=True)
    adoption_inquiries = (
        AdoptionInquiry.objects
        .filter(user=request.user)
        .select_related('animal', 'rescue_org').prefetch_related('animal__photos')
        .prefetch_related('messages', 'conversations')
        .order_by('-created_at')
    )
    my_inquiries = adoption_inquiries
    inquiry_reply_targets = {}
    for inquiry in adoption_inquiries:
        recipient_id = None
        if inquiry.rescue_org:
            recipient_id = UserProfile.objects.filter(organization=inquiry.rescue_org, role='rescue_org').values_list('user_id', flat=True).first()
        inquiry_reply_targets[inquiry.pk] = recipient_id
    # Recent announcements for users (only active)
    announcements = Announcement.objects.select_related('rescue_org', 'posted_by').filter(is_active=True).order_by('-created_at')[:10]
    notifications  = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:20]
    org_names = available_animals.values_list('rescue_org__name', flat=True).distinct()

    context = {
        'user':              request.user,
        'profile':           profile,
        'page_title':        'My Dashboard',

        'query':             query,
        'selected_species':  selected_species,
        'selected_status':   selected_status,

        # Stats
        'reports_count':     my_reports.count(),
        'active_rescues':    my_reports.filter(status__in=['pending','responding','rescued','under_observation','in_treatment']).count(),
        'saved_count':       saved_animals.count(),
        'unread_count':      _unread_count(request.user),
        'next_report_number': (AnimalReport.objects.aggregate(next_id=Max('id'))['next_id'] or 0) + 1,

        # Data
        'my_reports':        my_reports[:10],
        'my_reports_full':   my_reports,
        'saved_animals':     saved_animals,
        'adoption_ready':    adoption_ready,
        'all_animals':       page_animals,
        'all_animals_total': available_animals_total,
        'adoption_inquiries': adoption_inquiries,
        'my_inquiries':      my_inquiries,
        'inquiry_reply_targets': inquiry_reply_targets,
        'announcements': announcements,
        'notifications':     notifications,
        'saved_ids_list':    list(saved_ids),
        'browse_org_names':  org_names,
    }

    context.update(_build_pagination_context(request, page_obj))
    return render(request, 'user_dashboard.html', context)


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
    animal = get_object_or_404(RescuedAnimal, pk=animal_id, adoption_open=True)

    inquiry, created = AdoptionInquiry.objects.update_or_create(
        user=request.user,
        animal=animal,
        defaults={
            'rescue_org': animal.rescue_org,
            'living_situation': request.POST.get('living_situation', 'house'),
            'other_pets': request.POST.get('other_pets', 'none'),
            'message': request.POST.get('message', '').strip(),
            'status': 'pending',
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
        recipient = None
        if animal.rescue_org:
            recipient = UserProfile.objects.filter(organization=animal.rescue_org, role='rescue_org').values_list('user_id', flat=True).first()
        recipient_user = User.objects.get(pk=recipient) if recipient else request.user
        message = Message.objects.create(
            sender=request.user,
            recipient=recipient_user,
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
    body = request.POST.get('body', '').strip()

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
        sender=request.user,
        recipient=recipient,
        conversation=conv,
        inquiry=inquiry,
        body=body,
        subject=request.POST.get('subject', ''),
    )

    animal_id = request.POST.get('animal_id')
    if animal_id:
        try:
            msg.animal = RescuedAnimal.objects.get(pk=animal_id)
            msg.save()
        except RescuedAnimal.DoesNotExist:
            pass

    if inquiry:
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
            recipient=recipient,
            type='new_user_message',
            title=f'New message from {request.user.get_full_name() or request.user.username}',
            body=body[:200],
        )

    conv.last_message = msg
    conv.updated_at = timezone.now()
    conv.save()

    return JsonResponse({'ok': True, 'message_id': msg.pk})


@login_required
@role_required('reporter', 'rescue_org', 'admin')
@require_POST
def user_mark_notifications_read(request):
    """Mark all (or specific) notifications as read."""
    raw_ids = request.POST.getlist('ids')
    clean_ids = []
    for value in raw_ids:
        try:
            clean_ids.append(int(str(value).strip()))
        except (TypeError, ValueError):
            continue

    qs = Notification.objects.filter(recipient=request.user)
    if clean_ids:
        qs = qs.filter(pk__in=clean_ids)
    updated = qs.update(is_read=True)
    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return JsonResponse({'ok': True, 'updated': updated, 'unread_count': unread_count})