import math

from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse

from .forms import AnimalReportForm
from .models import AnimalReport, AnimalReportPhoto
from accounts.models import UserProfile
from animals.models import RescuedAnimal, RescuedAnimalPhoto
from organizations.models import RescueOrganization


def _haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(float, (lat1, lon1, lat2, lon2))
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


@login_required
@require_POST
def submit_animal_report(request):
    form = AnimalReportForm(request.POST, request.FILES)
    if not form.is_valid():
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'errors': form.errors}, status=400)
        messages.error(request, 'Please correct the errors in your report.')
        return redirect('dashboard')

    report = AnimalReport.objects.create(
        reporter=request.user,
        animal_type=form.cleaned_data['animal_type'],
        condition=form.cleaned_data['condition'],
        priority=form.cleaned_data['priority'],
        description=form.cleaned_data['description'],
        location=form.cleaned_data['location'],
        latitude=form.cleaned_data.get('latitude'),
        longitude=form.cleaned_data.get('longitude'),
        status='pending',
    )

    if form.cleaned_data.get('photo'):
        report.photo = form.cleaned_data['photo']
        report.save()

    for f in request.FILES.getlist('photos'):
        AnimalReportPhoto.objects.create(report=report, image=f)

    org = None
    report_lat = form.cleaned_data.get('latitude')
    report_lng = form.cleaned_data.get('longitude')

    if report_lat is not None and report_lng is not None:
        candidates = RescueOrganization.objects.filter(
            is_active=True,
            latitude__isnull=False,
            longitude__isnull=False,
        )
        nearest = None
        nearest_distance = None
        for candidate in candidates:
            distance = _haversine_km(report_lat, report_lng, candidate.latitude, candidate.longitude)
            if nearest_distance is None or distance < nearest_distance:
                nearest = candidate
                nearest_distance = distance
        org = nearest

    if org:
        report.rescue_org = org
        report.save()
        org_members = UserProfile.objects.filter(
            organization=org, role='rescue_org'
        ).select_related('user')
        for member in org_members:
            member.user.notifications.create(
                type='new_report',
                title=f'New rescue report #{report.pk} assigned',
                body=f'{report.get_animal_type_display()} ({report.get_condition_display()}) at {report.location}',
                report=report,
            )

    request.user.notifications.create(
        type='rescue_update',
        title=f'Report #{report.pk} submitted successfully',
        body=f'Your report has been received. {"Assigned to " + org.name + "." if org else "Awaiting assignment."}',
        report=report,
    )

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'report_id': report.pk, 'report_number': report.pk})

    messages.success(request, 'Your report has been submitted successfully.')
    return redirect('dashboard')


def _sync_report_photos_to_animal(report, animal):
    """Copy report photo references to the rescued animal gallery without duplicates.

    The files are already stored by the report upload. Reusing the same file path keeps
    this lightweight and makes rescued animal cards/details show the rescue photos.
    """
    existing = set(
        animal.photos.exclude(image='').values_list('image', flat=True)
    )
    photos_to_copy = []

    if report.photo and report.photo.name not in existing:
        photos_to_copy.append(report.photo.name)
        existing.add(report.photo.name)

    for report_photo in report.photos.all():
        if report_photo.image and report_photo.image.name not in existing:
            photos_to_copy.append(report_photo.image.name)
            existing.add(report_photo.image.name)

    for image_name in photos_to_copy:
        RescuedAnimalPhoto.objects.create(
            animal=animal,
            image=image_name,
            is_primary=not animal.photos.exists(),
        )


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

    _sync_report_photos_to_animal(report, animal)
    return animal


@login_required
@require_POST
def update_animal_report(request, report_id):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if profile.role != 'rescue_org':
        return JsonResponse({'ok': False, 'error': 'Permission denied.'}, status=403)

    report = get_object_or_404(AnimalReport, pk=report_id)
    status = request.POST.get('status')
    notes = request.POST.get('response_notes', '').strip()

    if status and status in dict(AnimalReport.STATUS_CHOICES):
        report.status = status
    if notes:
        report.response_notes = notes
    report.save()

    uploaded_photos = request.FILES.getlist('photos')
    for f in uploaded_photos:
        AnimalReportPhoto.objects.create(report=report, image=f)

    if report.status == 'rescued':
        _ensure_rescued_animal_for_report(report)

    if report.reporter:
        report.reporter.notifications.create(
            type='rescue_update',
            title=f'Update on report #{report.pk}',
            body=f'Status changed to {report.get_status_display()}. {notes}',
            report=report,
        )

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'status': report.status, 'status_display': report.get_status_display()})

    messages.success(request, 'Report updated successfully.')
    return redirect('dashboard')
