from django.urls import re_path

from . import views


urlpatterns = [
    re_path(r'^proxy/(?P<path>.*?)$', views.ProxyView.as_view()),
    re_path(r'^naive/(?P<path>.*?)$', views.NaiveView.as_view()),
]
