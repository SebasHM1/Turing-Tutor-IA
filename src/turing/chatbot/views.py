from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import ChatSession, ChatMessage
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings


import google.generativeai as genai

genai.configure(api_key=settings.GEMINI_API_KEY)  # Asegúrate de tener GEMINI_API_KEY en settings.py

@login_required
def chatbot_view(request):
    session, _ = ChatSession.objects.get_or_create(user=request.user)
    messages = ChatMessage.objects.filter(session=session).order_by('timestamp')
    return render(request, 'chatbot/chat_interface.html', {'messages': messages})

@csrf_exempt
@login_required
def send_message(request):
    if request.method == 'POST':
        user_message = request.POST.get('message')
        session, _ = ChatSession.objects.get_or_create(user=request.user)
        ChatMessage.objects.create(session=session, sender='user', message=user_message)

        try:
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(user_message)
            bot_message = response.text
        except Exception as e:
            bot_message = "Sorry, there was an error with the AI service."

        ChatMessage.objects.create(session=session, sender='bot', message=bot_message)
        return JsonResponse({'bot_message': bot_message})
    return JsonResponse({'error': 'Invalid request'}, status=400)