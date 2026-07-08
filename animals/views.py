from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse

from .models import RescuedAnimal, RescuedAnimalPhoto
from accounts.models import UserProfile, SavedAnimal, Notification
from reports.models import AnimalReport


@login_required
@require_POST
def org_add_animal(request):
    profile = UserProfile.objects.filter(user=request.user).first()
    if not profile or not profile.organization:
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
        rescue_org=profile.organization,
        name=request.POST.get('name', '').strip(),
        species=species,
        sex=sex,
        approx_age=request.POST.get('approx_age', '').strip(),
        color=request.POST.get('color', '').strip(),
        breed=request.POST.get('breed', '').strip(),
        status=status,
        vaccination=vaccination,
        shelter=request.POST.get('shelter', '').strip(),
        medical_notes=request.POST.get('medical_notes', '').strip(),
        temperament=request.POST.get('temperament', '').strip(),
        adoption_open=request.POST.get('adoption_open') == 'on',
    )

    source_id = request.POST.get('source_report_id')
    if source_id:
        try:
            source_report = AnimalReport.objects.get(pk=source_id)
            animal.source_report = source_report
            animal.save()
        except AnimalReport.DoesNotExist:
            pass

    for index, photo in enumerate(request.FILES.getlist('photos')):
        RescuedAnimalPhoto.objects.create(
            animal=animal,
            image=photo,
            is_primary=(index == 0),
        )

    messages.success(request, f'Animal profile for "{animal.display_name()}" created.')
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'animal_id': animal.pk, 'animal_name': animal.display_name()})
    return redirect('dashboard')


@login_required
@require_POST
def org_edit_animal(request, animal_id):
    profile = UserProfile.objects.filter(user=request.user).first()
    animal = get_object_or_404(RescuedAnimal, pk=animal_id, rescue_org=profile.organization)

    species = request.POST.get('species', animal.species)
    sex = request.POST.get('sex', animal.sex)
    status = request.POST.get('status', animal.status)
    vaccination = request.POST.get('vaccination', animal.vaccination)

    if species not in dict(RescuedAnimal.SPECIES_CHOICES):
        species = animal.species
    if sex not in dict(RescuedAnimal.SEX_CHOICES):
        sex = animal.sex
    if status not in dict(RescuedAnimal.STATUS_CHOICES):
        status = animal.status
    if vaccination not in dict(RescuedAnimal.VACCINATION_CHOICES):
        vaccination = animal.vaccination

    animal.name = request.POST.get('name', animal.name).strip()
    animal.species = species
    animal.sex = sex
    animal.approx_age = request.POST.get('approx_age', animal.approx_age).strip()
    animal.color = request.POST.get('color', animal.color).strip()
    animal.breed = request.POST.get('breed', animal.breed).strip()
    animal.status = status
    animal.vaccination = vaccination
    animal.shelter = request.POST.get('shelter', animal.shelter).strip()
    animal.medical_notes = request.POST.get('medical_notes', animal.medical_notes).strip()
    animal.temperament = request.POST.get('temperament', animal.temperament).strip()
    animal.adoption_open = request.POST.get('adoption_open') == 'on'
    animal.save()

    for photo in request.FILES.getlist('photos'):
        RescuedAnimalPhoto.objects.create(animal=animal, image=photo)

    if animal.status == 'adoption':
        saved_users = SavedAnimal.objects.filter(animal=animal).select_related('user')
        for saved in saved_users:
            Notification.objects.get_or_create(
                recipient=saved.user,
                type='adoption_ready',
                animal=animal,
                defaults={
                    'title': f'{animal.display_name()} is now ready for adoption!',
                    'body': f'Good news! {animal.display_name()} at {profile.organization.name} is now available.',
                }
            )

    messages.success(request, 'Animal profile updated.')
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'animal_id': animal.pk})
    return redirect('dashboard')


@login_required
@require_POST
def org_toggle_adoption(request, animal_id):
    profile = UserProfile.objects.filter(user=request.user).first()
    animal = get_object_or_404(RescuedAnimal, pk=animal_id, rescue_org=profile.organization)

    animal.adoption_open = not animal.adoption_open
    if animal.adoption_open:
        animal.status = 'adoption'
    animal.save()

    return JsonResponse({'adoption_open': animal.adoption_open, 'status': animal.status})
