# tutor_inteligente/users/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login # Para loguear al usuario después del registro
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required # Para el dashboard

# ... (tu vista dashboard_view si ya la tienes)
@login_required
def dashboard_view(request):
    # Asumiendo que tienes una plantilla 'users/dashboard.html' o 'dashboard.html'
    return render(request, 'users/dashboard.html') # Ajusta la ruta de la plantilla si es necesario

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard') # Si ya está logueado, que vaya al dashboard

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user) # Loguear al usuario automáticamente después del registro
            return redirect('dashboard') # Redirigir al dashboard (o a donde definas en LOGIN_REDIRECT_URL)
        # Si el formulario no es válido, se volverá a renderizar la plantilla con los errores
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})