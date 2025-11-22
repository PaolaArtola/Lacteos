from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from lacteos.models import Lacteo, UserProfile

def home(request):
    # Get featured products (first 4 with stock)
    featured_products = Lacteo.objects.filter(stock__gt=0)[:4]
    context = {
        'featured_products': featured_products,
    }
    return render(request, 'home.html', context)

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create profile with customer role by default
            UserProfile.objects.get_or_create(user=user, defaults={'role': 'customer'})
            login(request, user)
            messages.success(request, '¡Cuenta creada exitosamente!')
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})


def logout_view(request):
    """Custom logout view that accepts GET requests"""
    logout(request)
    messages.success(request, 'Has cerrado sesión exitosamente.')
    return redirect('home')