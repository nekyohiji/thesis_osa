from django.shortcuts import redirect

def role_required(allowed_roles):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            role = request.session.get('role')
            if role in allowed_roles:
                return view_func(request, *args, **kwargs)
            return redirect('login')  # or render 403 page
        return wrapper
    return decorator
