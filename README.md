# django-proxy-example

Here is an example of the backend powered by Django + REST Framework that
implements proxy to Lbasedb managing the necessady permissions with Django
build-in admin groups. Below, we step-by-step are developing the software.


## Step 1. Install Django + REST Framework

1. Install Python virtual environment. In my case I have Python 3.12.3 on Ubuntu 24.04.2 LTS.

```
python3 -m virtualenv .venv
source .venv/bin/activate
```

2. Install Django and REST Framework

```
pip install django
pip install djangorestframework
```

3. Save the dependencies into `requirements.txt` (to view the versions `pip freeze`):

```
Django==5.2
djangorestframework==3.16.0
```

4. Create a new django project: `django-admin startproject django_proxy_example .`

5. Migrate the database (it is SQLite by default in Django): `python manage.py migrate`

6. Create a superuser to manage permissions: `python manage.py createsuperuser` (add username as `admin` and password `qwerty123`)

7. Now the project can be run by: `python manage.py runserver` (visit http://localhost:8000/ to see the result).

8. Create Django app for REST API: `python manage.py startapp api` and add `rest_framework` and `api` to `INSTALLED_APPS` in `settings.py`.


## Step 2. Configure REST Framework proxy view

1. Add REST view in `api/views.py`:

```python
from django.http import HttpResponse
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView


class ProxyView(APIView):
    permission_classes = [AllowAny]

    def dispatch(self, request, *args, **kwargs):
        return HttpResponse('ok')
```

2. Add file `api/urls.py` with the following content:

```python
from django.urls import path

from . import views


urlpatterns = [
	path('proxy/', views.ProxyView.as_view()),
]
```

3. The content of `django_proxy_example/urls.py` should be (adding `api` endpoint):

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
]
```

4. Once it is done, run the server (`python manage.py runserve`) and 
try http://localhost:8000/api/proxy/ (in Postman, for example). 
The content `ok` should be responded (for any HTTP method).


## Step 3. Download, run and configure Lbasedb

1. Go to the official `Lbasedb` page on Docker Hub: https://hub.docker.com/r/fomalhaut88/lbasedb. 
There is all the details of the API and the installation.

2. Pull the image: `docker pull fomalhaut88/lbasedb`

3. Run the container (in a separate tab, so you can see the log of the requests):

```
docker run \
    -p 8080:8080 \
    -it --rm \
    --ulimit nofile=1024:1024 \
    --volume /tmp/lbasedb:/app/db \
    --name lbasedb-app \
    --env WORKERS=2 \
    fomalhaut88/lbasedb
```

4. After that, you can request Lbasedb API directly via Postman. For example, try: http://localhost:8080/version

5. Create a new feed called `xy`: make `POST http://localhost:8080/feed` with the JSON body `{"name":"xy"}`. 
If everything is correct, http://localhost:8080/feed will show the available feed.

6. Create calls `x` and `y` in the feed `xy`: make two requests `POST http://localhost:8080/col?feed=xy` 
with the JSON contents `{"name":"x","datatype":"Float64"}` and `{"name":"x","datatype":"Float64"}`.
Once it is done, http://localhost:8080/col?feed=xy will print the columns you have just added.


## Step 4. Fill the database with a big dataset

Create a script `db_fill.py` with the following content:

```python
import random
import asyncio

import aiohttp


def generate_dataset(size):
    return {
        'x': [random.random() for _ in range(size)],
        'y': [random.random() for _ in range(size)],
    }


async def get_size():
    async with aiohttp.ClientSession(raise_for_status=True) as client:
        async with client.get("http://localhost:8080/size?feed=xy") as resp:
            data = await resp.json()
            return data['size']


async def clear():
    async with aiohttp.ClientSession(raise_for_status=True) as client:
        async with client.put("http://localhost:8080/size?feed=xy", 
                              json={'size': 0}):
            pass


async def push_dataset(dataset):
    async with aiohttp.ClientSession(raise_for_status=True) as client:
        async with client.post("http://localhost:8080/data?feed=xy", 
                               json=dataset):
            pass


async def main():
    await clear()
    dataset = generate_dataset(1_000_000)
    await push_dataset(dataset)
    print(await get_size())


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
```

Before the run, install `aiohttp`: `pip install aiohttp`.

Once everything is ready, run the script so it fills the database with data.


## Step 5. Develop proxy view (chain and stream)

1. First, install `requests`: `pip install requests` and add `requests==2.32.3` to `requirements.txt`.

2. Improve the views adding `ProxyView` (with stream response) and `NaiveView` (that keeps full response body in the memory).

```python
import requests
from django.http import HttpResponse, StreamingHttpResponse
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView


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
                headers=dict_keep(request.headers, ['content-type', 'accept']),
                stream=True
                ) as resp:
            return HttpResponse(
                resp.raw,
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

```


## Step 6. Load test for get and update

Before we start, we prepare data to insert for `wrk`: `curl "http://localhost:8080/data?feed=xy&ix=0&size=1000000&col[]=x&col[]=y" > data.json`

We run Django project with UWSGI (`uwsgi --ini ./uwsgi.ini`) in 1 process. The load test log corresponds to the template:

`command` - RPS (Comment)


#### Get short data (using UWSGI):

`wrk -c 1 -d 5 -t 1 http://localhost:8080/version` - 16300

`wrk -c 1 -d 5 -t 1 http://localhost:8000/api/naive/version` - 800

`wrk -c 1 -d 5 -t 1 http://localhost:8000/api/proxy/version` - 800

This shows how slow Django is even with UWSGI.

#### Get big dataset (1M rows):

`wrk -c 1 -d 10 -t 1 "http://localhost:8080/data?feed=xy&ix=0&size=1000000&col[]=x&col[]=y"` - 9.7

`wrk -c 1 -d 10 -t 1 "http://localhost:8000/api/naive/data?feed=xy&ix=0&size=1000000&col[]=x&col[]=y"` - 4.1 (server memory jumps from 40MB to 80MB)

`wrk -c 1 -d 10 -t 1 "http://localhost:8000/api/proxy/data?feed=xy&ix=0&size=1000000&col[]=x&col[]=y"` - 4.6 (server memory is mainly stable, sometimes jump happens, maybe due to GC)

`proxy` is faster and in most cases has no big jumps.

#### Send big dataset (1M rows):

`wrk -c 1 -d 10 -t 1 -s load-update.lua "http://localhost:8080/data?feed=xy&ix=0"` - 1.7

`wrk -c 1 -d 10 -t 1 -s load-update.lua "http://localhost:8000/api/naive/data?feed=xy&ix=0"` - 1.4 (server memory jumps from 40MB to 460MB)

`wrk -c 1 -d 10 -t 1 -s load-update.lua "http://localhost:8000/api/proxy/data?feed=xy&ix=0"` - 1.6 (server memory is stable)

`proxy` is 15% faster and have no jumps totally compaing to `naive` that consumes extremely much memory.
