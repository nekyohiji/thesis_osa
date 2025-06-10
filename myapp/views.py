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
def client_goodmoral_view(request):
    return render (request, 'myapp/client_goodmoral.html')
def client_scholarships_view(request):
    return render (request, 'myapp/client_scholarships.html')
def client_CS_view(request):
    return render (request, 'myapp/client_CS.html')
def client_SurrenderingID_view(request):
    return render (request, 'myapp/client_SurrenderingID.html')
def client_studentAssistantship_view(request):
    return render (request, 'myapp/client_studentAssistantship.html')
def client_ACSO_view(request):
    return render (request, 'myapp/client_ACSO.html')
def client_lostandfound_view(request):
    return render (request, 'myapp/client_lostandfound.html')