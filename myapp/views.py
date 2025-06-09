from django.http import HttpResponse
from django.shortcuts import render

def index(request):
    return HttpResponse("🎓 Hello from your thesis web app!")
def home_view(request):
    return render(request, 'myapp/home.html')