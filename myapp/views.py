from django.http import HttpResponse
from django.shortcuts import render

def index(request):
    return HttpResponse("🎓 Hello from your thesis web app!")
def home_view(request):
    return render(request, 'myapp/client_home.html')
def login_view(request):
    return render (request, 'myapp/login.html')
def guard_violation_view(request):
    return render (request, 'myapp/guard_violation.html')
def guard_report_view(request):
    return render (request, 'myapp/guard_report.html')