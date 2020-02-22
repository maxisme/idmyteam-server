from django.shortcuts import render

# Create your views here.

def welcome_handler(request):
    return render(request, 'base.html')