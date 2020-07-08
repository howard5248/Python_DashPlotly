from django.shortcuts import render
from .models import Stinfo,o2013Obs,o2014Obs,o2015Obs,o2016Obs,o2017Obs,o2018Obs,o2019Obs

# from django.db.models import Q
from . import dashApp1


def app1(request):
    # stlists = Stinfo.objects.using(DBname).all().filter(~Q(type='FPG')).order_by("-county")
    return render(request, 'test1/test1.html')