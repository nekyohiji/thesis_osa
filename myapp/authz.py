from django.conf import settings

def can_view_superadmins(request):
    u = getattr(request, "user", None)
    return bool(u and u.is_authenticated and getattr(u, "email", None) in getattr(settings, "SUPERADMIN_VIEWERS", []))