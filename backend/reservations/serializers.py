"""Validate incoming JSON and serialize safe public fields."""
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers
from .models import User, Slot, Booking


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'email_verified', 'tutor_approved']
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'role', 'password']

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('This email is already registered.')
        return value

    def validate(self, data):
        try:
            validate_password(data['password'], User(username=data['username'], email=data['email']))
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'password': exc.messages})
        return data

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class CredentialsSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(trim_whitespace=False)


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField()


class TokenSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=2048)


class ResetSerializer(serializers.Serializer):
    uid = serializers.CharField(max_length=100)
    token = serializers.CharField(max_length=200)
    password = serializers.CharField(trim_whitespace=False)


class BookingRequestSerializer(serializers.Serializer):
    slot_id = serializers.IntegerField(min_value=1)


class SlotSerializer(serializers.ModelSerializer):
    tutor_name = serializers.CharField(source='tutor.username', read_only=True)
    available = serializers.SerializerMethodField()

    class Meta:
        model = Slot
        fields = ['id', 'tutor', 'tutor_name', 'subject', 'starts_at', 'ends_at', 'location', 'available']
        read_only_fields = ['id', 'tutor', 'tutor_name', 'available']

    def get_available(self, slot):
        if hasattr(slot, 'occupied'):
            return not slot.occupied
        return not slot.bookings.filter(cancelled_at__isnull=True).exists()

    def validate(self, data):
        start, end = data.get('starts_at'), data.get('ends_at')
        if start and start <= timezone.now():
            raise serializers.ValidationError({'starts_at': 'Choose a future time.'})
        if start and end and end <= start:
            raise serializers.ValidationError({'ends_at': 'Must be after start time.'})
        return data


class BookingSerializer(serializers.ModelSerializer):
    slot = SlotSerializer(read_only=True)
    student_name = serializers.CharField(source='student.username', read_only=True)

    class Meta:
        model = Booking
        fields = ['id', 'student_name', 'slot', 'created_at', 'cancelled_at']
        read_only_fields = fields
