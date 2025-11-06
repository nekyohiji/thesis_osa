# myapp/middleware.py
import time
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from urllib.parse import quote
from django.conf import settings

class IdleTimeoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        timeout = getattr(settings, "IDLE_TIMEOUT_SECONDS", 900)
        path = request.path

        login_path = reverse("login")
        exempt_prefixes = (login_path, "/logout", "/static/", "/media/")
        if any(path.startswith(p) for p in exempt_prefixes):
            return self.get_response(request)

        # No authenticated session -> proceed
        if not request.session.get("user_id"):
            return self.get_response(request)

        now = int(time.time())
        last = request.session.get("last_touch")

        # Expired?
        if last is not None and (now - int(last)) > timeout:
            request.session.flush()
            # XHR/HTMX → 440 so JS can redirect
            is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"
            is_htmx = request.headers.get("HX-Request") == "true"
            if is_ajax or is_htmx or "application/json" in (request.headers.get("accept") or ""):
                return JsonResponse({"detail": "Session timed out"}, status=440)
            next_url = quote(request.get_full_path())
            return redirect(f"{login_path}?next={next_url}")

        # Only bump the timer on real user actions
        if request.headers.get("X-User-Activity") == "1":
            request.session["last_touch"] = now

        return self.get_response(request)