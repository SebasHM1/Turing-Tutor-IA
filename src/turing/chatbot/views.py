from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required # Asegura que solo usuarios logueados puedan acceder
def chatbot_view(request):
    # Logica para el chatbot y sus vistas a implementar 
    context = {
        'username': request.user.username,
        # Pasaremos mas datos a futuro
    }
    return render(request, 'chatbot/chat_interface.html', context)