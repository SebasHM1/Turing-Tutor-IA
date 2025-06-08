# tutor_inteligente/users/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login # Para loguear al usuario después del registro
#from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required # Para el dashboard
from .forms import CustomUserCreationForm # <--- Usa tu formulario personalizado
from .models import UserState 

def register_view(request):
    # Eliminamos por completo el if request.user.is_authenticated

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # Activamos el estado y marcamos activo
            user.state = UserState.ACTIVE
            user.is_active = True
            user.save()
            # Redirigimos al login, no hacemos login automático
            return redirect('login')
    else:
        form = CustomUserCreationForm()

    return render(request, 'registration/register.html', {'form': form})