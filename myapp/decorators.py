from django.shortcuts import redirect, render
from functools import wraps
from functools import wraps
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from urllib.parse import quote
from django.contrib import messages
from myapp.models import Facilitator
from .utils import no_store
from django.views.decorators.cache import never_cache

def role_required(allowed_roles):
    allowed = {r.lower() for r in allowed_roles}

    def decorator(view_func):
        @wraps(view_func)
        @never_cache  
        def wrapped(request, *args, **kwargs):
            role = (request.session.get('role') or "").lower()
            is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"
            wants_json = is_ajax or "application/json" in (request.headers.get("accept") or "")

            if not role:
                if wants_json:
                    return no_store(JsonResponse({"detail": "Authentication required"}, status=401))
                next_url = quote(request.get_full_path())
                resp = redirect(f"{reverse('login')}?next={next_url}")
                return no_store(resp)

            if role in allowed:
                resp = view_func(request, *args, **kwargs)
                return no_store(resp)

            if wants_json:
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
        resp = viewfunc(request, *args, **kwargs)
        return no_store(resp)
    return _wrapped