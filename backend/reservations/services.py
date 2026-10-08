"""Business rules shared by HTTP controllers and tests; MySQL/InnoDB required."""
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from .errors import Conflict
from .models import User, Slot, Booking


def verified(user):
    if not user.is_active or not user.email_verified:
        raise PermissionDenied('An active account and verified email are required.')


def lock_users(*ids):
    # Every scheduling operation locks affected users in primary-key order,
    # then locks the slot. This serializes overlap checks across distinct slots.
    return {u.pk: u for u in User.objects.select_for_update().filter(pk__in=set(ids)).order_by('pk')}


def slot_reference(slot_id):
    try:
        return Slot.objects.get(pk=slot_id)
    except Slot.DoesNotExist:
        raise NotFound('Slot not found.')


@transaction.atomic
def book(user, slot_id):
    reference = slot_reference(slot_id)
    users = lock_users(user.pk, reference.tutor_id)
    student, tutor = users[user.pk], users[reference.tutor_id]
    verified(student)
    if student.role != 'student':
        raise PermissionDenied('Only students can reserve sessions.')
    slot = Slot.objects.select_for_update().get(pk=slot_id)
    if not tutor.is_active or not tutor.email_verified or not tutor.tutor_approved or tutor.role != 'tutor':
        raise Conflict('This tutor is not available.')
    if slot.starts_at <= timezone.now():
        raise Conflict('This session has already started.')
    if Booking.objects.filter(slot=slot, cancelled_at__isnull=True).exists():
        raise Conflict('This slot has just been reserved. Please choose another time.')
    if Booking.objects.filter(student=student, cancelled_at__isnull=True,
            slot__starts_at__lt=slot.ends_at, slot__ends_at__gt=slot.starts_at).exists():
        raise Conflict('You already have a lesson during this time.')
    return Booking.objects.create(student=student, slot=slot)


@transaction.atomic
def cancel(user, booking_id):
    try:
        reference = Booking.objects.select_related('slot').get(pk=booking_id, student=user)
    except Booking.DoesNotExist:
        raise NotFound('Reservation not found.')
    users = lock_users(user.pk, reference.slot.tutor_id)
    verified(users[user.pk])
    slot = Slot.objects.select_for_update().get(pk=reference.slot_id)
    booking = Booking.objects.select_for_update().get(pk=booking_id)
    if booking.cancelled_at is not None:
        return booking
    if slot.starts_at <= timezone.now():
        raise Conflict('Started sessions cannot be cancelled.')
    booking.cancelled_at = timezone.now()
    booking.save(update_fields=['cancelled_at'])
    return booking


@transaction.atomic
def save_slot(user, data, slot_id=None):
    tutor = lock_users(user.pk)[user.pk]
    verified(tutor)
    if tutor.role != 'tutor' or not tutor.tutor_approved:
        raise PermissionDenied('Administrator approval is required for tutors.')
    if slot_id:
        try:
            slot = Slot.objects.select_for_update().get(pk=slot_id, tutor=tutor)
        except Slot.DoesNotExist:
            raise NotFound('Slot not found.')
        if slot.starts_at <= timezone.now() or slot.bookings.filter(cancelled_at__isnull=True).exists():
            raise Conflict('Only future, unbooked slots can be edited.')
    else:
        slot = Slot(tutor=tutor)
    if data['starts_at'] <= timezone.now() or data['ends_at'] <= data['starts_at']:
        raise ValidationError('Choose a valid future time range.')
    if Slot.objects.filter(tutor=tutor, starts_at__lt=data['ends_at'],
            ends_at__gt=data['starts_at']).exclude(pk=slot.pk).exists():
        raise Conflict('This time overlaps another slot on your schedule.')
    for field in ('subject', 'starts_at', 'ends_at', 'location'):
        if field in data:
            setattr(slot, field, data[field])
    slot.save()
    return slot
