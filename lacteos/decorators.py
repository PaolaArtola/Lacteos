from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def admin_or_employee_required(view_func):
    """Decorator to check if user is admin or employee"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Debes iniciar sesión para acceder a esta página.')
            return redirect('login')
        
        # Check if user has profile
        if not hasattr(request.user, 'profile'):
            from .models import UserProfile
            UserProfile.objects.get_or_create(user=request.user)
        
        if not (request.user.profile.is_admin() or request.user.profile.is_employee()):
            messages.error(request, 'No tienes permisos para acceder a esta página.')
            return redirect('home')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def admin_required(view_func):
    """Decorator to check if user is admin"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Debes iniciar sesión para acceder a esta página.')
            return redirect('login')
        
        # Check if user has profile
        if not hasattr(request.user, 'profile'):
            from .models import UserProfile
            UserProfile.objects.get_or_create(user=request.user)
        
        if not request.user.profile.is_admin():
            messages.error(request, 'Solo los administradores pueden acceder a esta página.')
            return redirect('home')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

