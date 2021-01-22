'''
definition for exception handler
'''
from django.conf import settings
from example.core.constants import HTTP_API_ERROR
from rest_framework import status
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    '''
    custom exception handler
    '''
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # Now add the HTTP status code to the response.
    if response is not None and response.template_name is None:
        error_response = {}
        error_response['error'] = {'message': response.data.get(
            'detail') if response.data.get('detail', None) else response.data}
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            error_response['status'] = exc.status_code
        else:
            error_response['status'] = HTTP_API_ERROR
        response.data = error_response
    return response
