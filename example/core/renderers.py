'''

Renderers

'''
import json

from django.conf import settings
from django.utils import six
from example.core.constants import HTTP_API_ERROR
from rest_framework import status
from rest_framework.compat import (INDENT_SEPARATORS, LONG_SEPARATORS,
                                   SHORT_SEPARATORS)
from rest_framework.renderers import JSONRenderer


class ApiRenderer(JSONRenderer):
    '''
    Api Renderer

    '''

    def check_status(self, data, api_status):
        '''
        Check Status

        '''
        _ = self
        message = data.get('error') if data.get('error', None) else data
        data = {
            'message': message['message'] if message.get('message') else message,
            'status': api_status
        }
        return data

    def check_else(self, data, api_status):
        '''
        Check Else

        '''
        _ = self
        error = data.get('error') if data.get('error', None) else data
        data = {
            'status': api_status,
            'message':  error.get('message') if error.get('message', None) else data
        }
        return data

    def check_200_201(self, data):
        '''
        Handling 200-201 status

        '''
        _ = self
        if 'message' in data:
            extras = data['extras'] if data.get('extras') else None
            data = {
                'message': data['message'],
            }
            if extras:
                data['response'] = extras
        else:
            data = {
                'response': data,
            }
        data['status'] = status.HTTP_200_OK
        return data

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Render `data` into JSON, returning a bytestring.

        """
        if data is None:
            return bytes()

        renderer_context = renderer_context or {}
        indent = self.get_indent(accepted_media_type, renderer_context)

        if indent is None:
            separators = SHORT_SEPARATORS if self.compact else LONG_SEPARATORS
        else:
            separators = INDENT_SEPARATORS

        status_code = renderer_context['response'].status_code
        renderer_context['response'].status_code = status.HTTP_200_OK

        if status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]:
            data = self.check_200_201(data)
        elif status_code in [HTTP_API_ERROR, status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_400_BAD_REQUEST]:
            status_c = HTTP_API_ERROR
            data = self.check_status(data, status_c)

        elif status_code in [status.HTTP_401_UNAUTHORIZED]:
            status_c = status.HTTP_401_UNAUTHORIZED
            data = self.check_status(data, status_c)

        elif status_code in [status.HTTP_302_FOUND]:
            status_c = status.HTTP_302_FOUND
            data = self.check_status(data, status_c)

        elif status_code in [status.HTTP_303_SEE_OTHER]:
            status_c = status.HTTP_303_SEE_OTHER
            data = self.check_status(data, status_c)

        elif status_code in [status.HTTP_301_MOVED_PERMANENTLY]:
            status_c = status.HTTP_301_MOVED_PERMANENTLY
            data = self.check_status(data, status_c)
        else:
            status_c = HTTP_API_ERROR
            data = self.check_else(data, status_c)
        ret = json.dumps(
            data, cls=self.encoder_class,
            indent=indent, ensure_ascii=self.ensure_ascii,
            separators=separators
        )

        if isinstance(ret, six.text_type):
            ret = ret.replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
            return bytes(ret.encode('utf-8'))
        return ret
