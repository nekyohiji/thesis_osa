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
def admin_dashboard_view(request):
    return render (request, 'myapp/admin_dashboard.html')
def admin_accounts_view(request):
    return render (request, 'myapp/admin_accounts.html')
def admin_ackreq_view(request):
    return render (request, 'myapp/admin_ackreq.html')
def admin_ACSO_view(request):
    return render (request, 'myapp/admin_ACSO.html')
def admin_assistantship_view(request):
    return render (request, 'myapp/admin_assistantship.html')
def admin_CS_view(request):
    return render (request, 'myapp/admin_CS.html')
def admin_election_view(request):
    return render (request, 'myapp/admin_election.html')
def admin_goodmoral_view(request):
    return render (request, 'myapp/admin_goodmoral.html')
def admin_lostandfound_view(request):
    return render (request, 'myapp/admin_lostandfound.html')
def admin_report_view(request):
    return render (request, 'myapp/admin_report.html')
def admin_scholarships_view(request):
    return render (request, 'myapp/admin_scholarships.html')
def admin_view_ackreq_view(request):
    return render (request, 'myapp/admin_view_ackreq.html')
def admin_view_CS_view(request):
    return render (request, 'myapp/admin_view_CS.html')
def admin_view_goodmoral_view(request):
    return render (request, 'myapp/admin_view_goodmoral.html')
def admin_view_violation_view(request):
    return render (request, 'myapp/admin_view_violation.html')
def admin_violation_view(request):
    return render (request, 'myapp/admin_violation.html')



