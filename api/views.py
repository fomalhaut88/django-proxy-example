import requests
from django.http import HttpResponse, StreamingHttpResponse
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView


CHUNK_SIZE = 65536


def dict_keep(dct, keys):
    return {
        k: v
        for k, v in dct.items()
        if k.lower() in keys
    }


class ProxyView(APIView):
    permission_classes = [AllowAny]

    def dispatch(self, request, *args, **kwargs):
        path = kwargs.get('path', '')
        qs = request.GET.urlencode()
        url = f'http://localhost:8080/{path}'
        if qs:
            url += '?' + qs
        with requests.request(
                request.method, url, data=request, 
                headers=dict_keep(request.headers, ['content-type', 'accept'])
                ) as resp:
            return StreamingHttpResponse(
                resp.iter_content(chunk_size=CHUNK_SIZE), 
                status=resp.status_code, 
                headers=resp.headers,
            )


class NaiveView(APIView):
    permission_classes = [AllowAny]

    def dispatch(self, request, *args, **kwargs):
        path = kwargs.get('path', '')
        qs = request.GET.urlencode()
        url = f'http://localhost:8080/{path}'
        if qs:
            url += '?' + qs
        with requests.request(
                request.method, url, data=request.body, 
                headers=dict_keep(request.headers, ['content-type', 'accept'])
                ) as resp:
            return HttpResponse(resp.content, status=resp.status_code, 
                                headers=resp.headers)
