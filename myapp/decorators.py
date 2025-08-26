from django.shortcuts import redirect, render
from functools import wraps
from functools import wraps
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from urllib.parse import quote

def role_required(allowed_roles):
    allowed = {r.lower() for r in allowed_roles}

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            role = (request.session.get('role') or "").lower()
            is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"
            wants_json = is_ajax or "application/json" in (request.headers.get("accept") or "")

            # Not logged in (no role in session)
            if not role:
                if wants_json:
                    return JsonResponse({"detail": "Authentication required"}, status=401)
                # keep normal browser flow
                next_url = quote(request.get_full_path())
                return redirect(f"{reverse('login')}?next={next_url}")

            # Authorized
            if role in allowed:
                return view_func(request, *args, **kwargs)

            # Forbidden
            if wants_json:
                return JsonResponse({"detail": "Forbidden"}, status=403)
            return render(request, "403.html", status=403)

        return wrapped
    return decorator
