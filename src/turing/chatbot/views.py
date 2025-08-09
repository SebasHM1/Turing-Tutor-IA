from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import ChatSession, ChatMessage
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from datetime import datetime


import google.generativeai as genai

genai.configure(api_key=settings.GEMINI_API_KEY)  # Asegúrate de tener GEMINI_API_KEY en settings.py

@login_required
def chatbot_view(request, session_id=None):
    if session_id:
        session = ChatSession.objects.filter(id=session_id, user=request.user).first()
    else:
        session = ChatSession.objects.filter(user=request.user).order_by('-created_at').first()
        if not session:
            session = ChatSession.objects.create(user=request.user, name="New Chat")
    
    messages = ChatMessage.objects.filter(session=session).order_by('timestamp') if session else []
    recent_chats = ChatSession.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'chatbot/chat_interface.html', {
        'messages': messages,
        'recent_chats': recent_chats,
        'current_session': session
    })

@csrf_exempt
@login_required
def send_message(request):
    if request.method == 'POST':
        try:
            user_message = request.POST.get('message')
            session_id = request.POST.get('session_id')
            session = ChatSession.objects.get(id=session_id, user=request.user)
            
            ChatMessage.objects.create(session=session, sender='user', message=user_message)

            try:
                model = genai.GenerativeModel('gemini-2.0-flash')
                response = model.generate_content(user_message)
                bot_message = response.text
            except Exception:
                bot_message = "Sorry, there was an error with the AI service."

            ChatMessage.objects.create(session=session, sender='bot', message=bot_message)
            return JsonResponse({'bot_message': bot_message})
        except ChatSession.DoesNotExist:
            return JsonResponse({'error': 'Chat session not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': 'An error occurred'}, status=500)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def create_session(request):
    session = ChatSession.objects.create(user=request.user, name=f"Chat {datetime.now().strftime('%H:%M')}")
    return redirect('chatbot:chat_detail', session.id)

@login_required
def delete_session(request, session_id):
    try:
        session = ChatSession.objects.get(id=session_id, user=request.user)
        session.delete()
    except ChatSession.DoesNotExist:
        # Session doesn't exist or doesn't belong to user, just redirect
        pass
    return redirect('chatbot:chatbot')