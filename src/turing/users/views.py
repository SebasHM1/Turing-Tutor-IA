from django.shortcuts import render, redirect
from django.contrib.auth import login 
from django.contrib.auth.decorators import login_required 
from .forms import CustomUserCreationForm 
from .models import UserState 
from .models import UserRole

def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.state = UserState.ACTIVE
            user.is_active = True
            user.save()
            return redirect('login')
    else:
        form = CustomUserCreationForm()

    return render(request, 'registration/register.html', {'form': form})


@login_required
def redirect_after_login(request):
    """
    Redirige a los usuarios a su dashboard correspondiente
    basado en su rol.
    """
    if request.user.role == UserRole.TEACHER:
        return redirect('teachers:dashboard') 
    elif request.user.role == UserRole.STUDENT:
        return redirect('chatbot:chatbot') 