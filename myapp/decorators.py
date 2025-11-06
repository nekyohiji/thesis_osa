# decorators.py
from functools import wraps
from urllib.parse import quote

from django.conf import settings  # still fine to keep if you want
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.cache import never_cache

from myapp.models import Facilitator
from .utils import no_store

def _wants_json(request):
    is_htmx = request.headers.get("HX-Request") == "true"
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"
    return is_htmx or is_ajax or "application/json" in (request.headers.get("accept") or "")

def _json_or_redirect_login(request, msg="Authentication required"):
    if _wants_json(request):
        return no_store(JsonResponse({"detail": msg, "code": "AUTH"}, status=401))
    next_url = quote(request.get_full_path())
    return no_store(redirect(f"{reverse('login')}?next={next_url}"))

def role_required(allowed_roles):
    allowed = {r.lower() for r in allowed_roles}

    def decorator(view_func):
        @wraps(view_func)
        @never_cache
        def wrapped(request, *args, **kwargs):
            role = (request.session.get('role') or "").lower()
            if not role:
                # Not authenticated → let middleware handle timeout, we just route to login/401
                return _json_or_redirect_login(request)

            if role in allowed:
                return no_store(view_func(request, *args, **kwargs))

            if _wants_json(request):
                return no_store(JsonResponse({"detail": "Forbidden"}, status=403))
            return no_store(render(request, "403.html", status=403))
        return wrapped
    return decorator

def facilitator_required(viewfunc):
    @wraps(viewfunc)
    @never_cache
    def _wrapped(request, *args, **kwargs):
        fpk = request.session.get("facilitator_pk")
        if not fpk or not Facilitator.objects.filter(pk=fpk, is_active=True).exists():
            for k in ("facilitator_pk", "facilitator_id", "facilitator_name"):
                request.session.pop(k, None)
            messages.error(request, "Please log in with your Faculty ID.")
            return no_store(redirect("client_CS"))

        # No idle logic here; middleware owns it
        return no_store(viewfunc(request, *args, **kwargs))
    return _wrapped
