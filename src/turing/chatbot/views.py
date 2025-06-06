# chatbot/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def chatbot_view(request):
    context = {
        # Opciones para mostrar información del usuario:
        'user_email': request.user.email,                 # Email del usuario
        'user_name': request.user.name,                   # Nombre
        'user_last_name': request.user.last_name,         # Apellido
        'user_full_name': request.user.get_full_name(),   # Método si lo definiste
        # Elige el que quieras pasar a la plantilla
    }
    return render(request, 'chatbot/chat_interface.html', context)