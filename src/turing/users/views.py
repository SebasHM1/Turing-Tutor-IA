# tutor_inteligente/users/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login # Para loguear al usuario después del registro
#from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required # Para el dashboard
from .forms import CustomUserCreationForm # <--- Usa tu formulario personalizado
from .models import UserState 

def register_view(request):
    if request.user.is_authenticated:
        return redirect('chatbot:chat_interface')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST) # <--- Usa tu formulario
        if form.is_valid():
            user = form.save()
            # Asegurarse que el estado sea activo para nuevos registros via web
            user.state = UserState.ACTIVE
            user.is_active = True # Asegura que Django lo vea como activo
            user.save()
            login(request, user)
            return redirect('chatbot:chat_interface')
    else:
        form = CustomUserCreationForm() # <--- Usa tu formulario
    return render(request, 'registration/register.html', {'form': form})