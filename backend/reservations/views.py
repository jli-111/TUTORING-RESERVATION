"""HTTP controllers: validate JSON, call services, return JSON and status codes."""
from django.db import IntegrityError, OperationalError
from django.db.models import Exists, OuterRef
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from .models import Slot, Booking
from .serializers import SlotSerializer, BookingSerializer, BookingRequestSerializer
from .services import book, cancel, save_slot
from .errors import Conflict


def schedule():
    active = Booking.objects.filter(slot_id=OuterRef('pk'), cancelled_at__isnull=True)
    return Slot.objects.select_related('tutor').annotate(occupied=Exists(active))


def write(operation):
    try:
        return operation()
    except IntegrityError:
        raise Conflict('The reservation conflicts with an existing record. Refresh and try again.')
    except OperationalError as exc:
        if exc.args and exc.args[0] in (1205, 1213):
            raise Conflict('The schedule is busy. Please retry.')
        raise


@api_view(['GET'])
@permission_classes([AllowAny])
def slots(request):
    rows = schedule().filter(starts_at__gt=timezone.now(), occupied=False,
        tutor__is_active=True, tutor__email_verified=True, tutor__tutor_approved=True, tutor__role='tutor')
    query = request.query_params.get('q', '').strip()
    if query:
        rows = rows.filter(subject__icontains=query)
    return Response(SlotSerializer(rows, many=True).data)


@api_view(['GET', 'POST'])
def tutor_slots(request):
    if request.user.role != 'tutor':
        raise PermissionDenied('Tutor access required.')
    if request.method == 'GET':
        return Response(SlotSerializer(schedule().filter(tutor=request.user, ends_at__gt=timezone.now()), many=True).data)
    serializer = SlotSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    slot = write(lambda: save_slot(request.user, serializer.validated_data))
    return Response(SlotSerializer(slot).data, status=201)


@api_view(['PUT'])
def tutor_slot_detail(request, pk):
    serializer = SlotSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    slot = write(lambda: save_slot(request.user, serializer.validated_data, pk))
    return Response(SlotSerializer(slot).data)


@api_view(['GET', 'POST'])
def bookings(request):
    if request.method == 'GET':
        rows = Booking.objects.select_related('slot__tutor', 'student').filter(student=request.user)
        return Response(BookingSerializer(rows, many=True).data)
    serializer = BookingRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    booking = write(lambda: book(request.user, serializer.validated_data['slot_id']))
    return Response(BookingSerializer(booking).data, status=201)


@api_view(['POST'])
def booking_cancel(request, pk):
    booking = write(lambda: cancel(request.user, pk))
    return Response(BookingSerializer(booking).data)
