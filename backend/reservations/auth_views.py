"""JSON account endpoints. Session cookies authenticate; CSRF protects writes."""
import logging
from urllib.parse import urlencode
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.views.decorators.csrf import csrf_protect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, AuthenticationFailed
from .models import User
from .serializers import UserSerializer, RegisterSerializer, CredentialsSerializer, EmailSerializer, TokenSerializer, ResetSerializer

logger = logging.getLogger(__name__)


def deliver(subject, body, recipient):
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [recipient])
    except Exception:
        logger.exception('Account email delivery failed')
        return False
    return True


def send_verification(user):
    token = signing.dumps({'id': user.pk, 'email': user.email}, salt='email-verification')
    url = settings.FRONTEND_URL + '/?' + urlencode({'verify': token})
    return deliver('Verify your Studyroom email', f'Open this link within 24 hours and confirm:\n{url}', user.email)


@api_view(['GET'])
@permission_classes([AllowAny])
def session(request):
    return Response({
        'user': UserSerializer(request.user).data if request.user.is_authenticated else None,
        'csrf_token': get_token(request),
    })


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_protect
def register(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        user = serializer.save()
    except IntegrityError:
        raise ValidationError('Username or email is already registered.')
    sent = send_verification(user)
    return Response({'message': 'Account created. Check your email to verify.' if sent else
        'Account created, but email delivery failed. Log in and resend verification.'}, status=201)


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_protect
def sign_in(request):
    serializer = CredentialsSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = authenticate(request, **serializer.validated_data)
    if user is None:
        raise AuthenticationFailed('Invalid username or password.')
    login(request, user)
    # Login rotates the CSRF secret; return a new token to the React client.
    return Response({'user': UserSerializer(user).data, 'csrf_token': get_token(request)})


@api_view(['POST'])
def sign_out(request):
    logout(request)
    return Response({'message': 'Signed out.', 'csrf_token': get_token(request)})


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_protect
def verify_email(request):
    serializer = TokenSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        data = signing.loads(serializer.validated_data['token'], salt='email-verification', max_age=86400)
        user = User.objects.get(pk=data['id'], email=data['email'], is_active=True)
    except (signing.BadSignature, User.DoesNotExist, KeyError, TypeError, ValueError):
        raise ValidationError('Invalid or expired verification link.')
    user.email_verified = True
    user.save(update_fields=['email_verified'])
    return Response({'message': 'Email verified. You can now manage reservations.'})


@api_view(['POST'])
def resend(request):
    if request.user.email_verified:
        return Response({'message': 'Email is already verified.'})
    now = timezone.now().timestamp()
    if now - request.session.get('verification_sent', 0) < 60:
        raise ValidationError('Please wait a minute before requesting another email.')
    sent = send_verification(request.user)
    if sent:
        request.session['verification_sent'] = now
    return Response({'message': 'Verification email sent.' if sent else 'Email delivery failed. Try again later.'}, status=200 if sent else 503)


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_protect
def password_reset(request):
    serializer = EmailSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = User.objects.filter(email__iexact=serializer.validated_data['email'], is_active=True).first()
    if user and user.has_usable_password():
        query = urlencode({'reset': default_token_generator.make_token(user), 'uid': urlsafe_base64_encode(force_bytes(user.pk))})
        deliver('Reset your Studyroom password', f'Open this link within one hour:\n{settings.FRONTEND_URL}/?{query}', user.email)
    return Response({'message': 'If an active account exists, a reset link has been sent.'})


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_protect
def password_confirm(request):
    serializer = ResetSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    try:
        user_id = int(urlsafe_base64_decode(data['uid']).decode())
    except (ValueError, UnicodeDecodeError, OverflowError):
        raise ValidationError('Invalid reset link.')
    with transaction.atomic():
        try:
            user = User.objects.select_for_update().get(pk=user_id, is_active=True)
        except User.DoesNotExist:
            raise ValidationError('Invalid reset link.')
        if not default_token_generator.check_token(user, data['token']):
            raise ValidationError('Invalid or expired reset link.')
        try:
            validate_password(data['password'], user)
        except DjangoValidationError as exc:
            raise ValidationError({'password': exc.messages})
        user.set_password(data['password'])
        user.save(update_fields=['password'])
    return Response({'message': 'Password updated. Log in with your new password.'})
