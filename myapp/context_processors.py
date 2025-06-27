def user_role_context(request):
    return {
        'user_role': request.session.get('role'),
        'user_full_name': request.session.get('full_name'),
    }