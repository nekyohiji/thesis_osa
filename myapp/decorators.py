from django.shortcuts import redirect, render
from functools import wraps

def role_required(allowed_roles):
    allowed = {r.lower() for r in allowed_roles}
    def decorator(view_func):
        @wraps(view_func)  # keep name/docs; better debugging
        def wrapped(request, *args, **kwargs):
            role = (request.session.get('role') or "").lower()
            if not role:
                # not logged in (no role in session)
                return redirect('login')  # optionally add ?next=request.path
            if role in allowed:
                return view_func(request, *args, **kwargs)
            # Forbidden (don’t 302 to login if already logged in)
            return render(request, "403.html", status=403)
        return wrapped
    return decorator
