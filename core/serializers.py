from rest_framework import serializers

# Import from correct apps
from accounts.models import AdoptionInquiry
from organizations.models import RescueOrganization
from animals.models import RescuedAnimal


class RescueOrganizationSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = RescueOrganization
        fields = [
            'id',
            'name',
            'contact_email',
            'contact_phone',
            'address',
            'description',
            'logo_url',
            'is_active',
            'created_at',
        ]

    def get_logo_url(self, obj):
        return obj.logo.url if obj.logo else None


class RescuedAnimalSerializer(serializers.ModelSerializer):
    rescue_org_name = serializers.CharField(source='rescue_org.name', read_only=True)
    primary_photo_url = serializers.SerializerMethodField()

    class Meta:
        model = RescuedAnimal
        fields = [
            'id',
            'name',
            'species',
            'breed',
            'sex',
            'approx_age',
            'color',
            'status',
            'vaccination',
            'shelter',
            'rescue_org_name',
            'adoption_open',
            'primary_photo_url',
            'rescued_at',
            'updated_at',
        ]

    def get_primary_photo_url(self, obj):
        photo = obj.photos.filter(is_primary=True).first()
        return photo.image.url if photo else None


class AdoptionInquirySerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    animal_id = serializers.IntegerField(source='animal.id', read_only=True)
    animal_name = serializers.CharField(source='animal.display_name', read_only=True)
    animal_species = serializers.CharField(source='animal.get_species_display', read_only=True)
    animal_age = serializers.CharField(source='animal.approx_age', read_only=True)
    rescue_org_name = serializers.CharField(source='rescue_org.name', read_only=True)

    class Meta:
        model = AdoptionInquiry
        fields = [
            'id',
            'user_name',
            'animal_id',
            'animal_name',
            'animal_species',
            'animal_age',
            'rescue_org_name',
            'living_situation',
            'other_pets',
            'message',
            'status',
            'created_at',
            'updated_at',
        ]