from django.http import HttpResponse

def index(request):
    return HttpResponse("🎓 Hello from your thesis web app!")