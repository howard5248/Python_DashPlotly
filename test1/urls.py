from django.urls import path,include
from . import views

urlpatterns = [
    path('app1',views.app1,name='app1'),
]