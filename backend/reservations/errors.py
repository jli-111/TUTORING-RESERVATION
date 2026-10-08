from django.http import JsonResponse
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler as drf_exception_handler


class Conflict(APIException):
    status_code = 409
    default_detail = 'The schedule changed. Refresh and try again.'
    default_code = 'conflict'


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is not None:
        detail = response.data
        message = detail.get('detail', 'Please check the submitted fields.') if isinstance(detail, dict) else 'Invalid request.'
        response.data = {'error': {'message': str(message), 'details': detail}}
    return response


def csrf_failure(request, reason=''):
    return JsonResponse({'error': {'message': 'CSRF check failed. Refresh the page and try again.'}}, status=403)
