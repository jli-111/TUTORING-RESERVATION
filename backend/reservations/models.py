"""Relational entities; migrations create these tables in MySQL."""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=[('student', 'Student'), ('tutor', 'Tutor')])
    email_verified = models.BooleanField(default=False)
    tutor_approved = models.BooleanField(default=False)


class Slot(models.Model):
    tutor = models.ForeignKey(User, on_delete=models.PROTECT, related_name='slots')
    subject = models.CharField(max_length=120)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    location = models.CharField(max_length=200, default='Online')

    class Meta:
        ordering = ['starts_at', 'id']
        constraints = [models.CheckConstraint(
            condition=models.Q(ends_at__gt=models.F('starts_at')),
            name='slot_end_after_start',
        )]
        indexes = [models.Index(fields=['tutor', 'starts_at'])]


class Booking(models.Model):
    student = models.ForeignKey(User, on_delete=models.PROTECT, related_name='bookings')
    slot = models.ForeignKey(Slot, on_delete=models.PROTECT, related_name='bookings')
    created_at = models.DateTimeField(auto_now_add=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    # MySQL has no partial unique indexes. Active rows generate their slot ID;
    # cancelled rows generate NULL, of which a UNIQUE index allows many.
    active_slot_key = models.GeneratedField(
        expression=models.Case(
            models.When(cancelled_at__isnull=True, then=models.F('slot_id')),
            default=models.Value(None), output_field=models.BigIntegerField(),
        ),
        output_field=models.BigIntegerField(), db_persist=True, unique=True, null=True,
    )

    class Meta:
        ordering = ['slot__starts_at', 'id']
