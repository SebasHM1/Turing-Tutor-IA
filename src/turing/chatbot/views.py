from datetime import datetime

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404

from users.decorators import student_required
from .models import ChatSession, ChatMessage
from courses.models import Enrollment, Course


import os
import json
from openai import OpenAI

import markdown
from markdown.extensions import codehilite




@login_required
def chatbot_view(request, session_id=None, course_id=None):
    """
    - Si viene course_id: abre (o crea) la última sesión del usuario para esa materia.
    - Si viene session_id: abre esa sesión (y deduce la materia).
    - Si no viene nada: Abre la última sesión del usuario).
    """
    course = None
    session = None


    if course_id is not None:
        # Aqui verifico que el estudiante esté inscrito en esa materia
        if not Enrollment.objects.filter(student=request.user, course_id=course_id).exists():
            return redirect('courses:my_student_courses')

        course = get_object_or_404(Course, pk=course_id)
        session = (ChatSession.objects
                   .filter(user=request.user, course_id=course_id)
                   .order_by('-created_at')
                   .first())
        if not session:
            session = ChatSession.objects.create(
                user=request.user,
                course_id=course_id,
                name=f"Chat {datetime.now().strftime('%H:%M')}"
            )

    # Abrir por id de sesión
    elif session_id is not None:
        session = ChatSession.objects.filter(id=session_id, user=request.user).select_related('course').first()
        if not session:
            return redirect('courses:my_student_courses')
        course = session.course

    # Ultima sesión del usuario 
    else:
        session = ChatSession.objects.filter(user=request.user).order_by('-created_at').first()
        if not session:
            session = ChatSession.objects.create(user=request.user, name="New Chat")
        course = session.course

    messages = ChatMessage.objects.filter(session=session).order_by('timestamp')
    # Filtra recientes por la misma materia si no, por todas del usuario
    if course:
        recent_chats = ChatSession.objects.filter(user=request.user, course=course).order_by('-created_at')
    else:
        recent_chats = ChatSession.objects.filter(user=request.user).order_by('-created_at')

    return render(request, 'chatbot/chat_interface.html', {
        'messages': messages,
        'recent_chats': recent_chats,
        'current_session': session,
        'current_course': course,
    })

@student_required
@login_required
def send_message(request):
    if request.method == 'POST':
        try:
            user_message = request.POST.get('message') or ''
            session_id = request.POST.get('session_id')

            session = ChatSession.objects.select_related('course').get(id=session_id, user=request.user)
            ChatMessage.objects.create(session=session, sender='user', message=user_message)


            try:
                # Configura la API Key de OpenAI
                os.environ['OPENAI_API_KEY'] = getattr(settings, 'OPENAI_API_KEY', None) or os.getenv('OPENAI_API_KEY')
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

                # Memoria de conversación
                context = get_chat_context(session, limit=5)
                full_prompt = f"{context}{user_message}"

                completion = client.chat.completions.create(
                    model="gpt-4o-mini",  # Puedes cambiar el modelo si lo deseas
                    messages=[
                        {"role": "system", "content": "Eres un asistente de IA útil para estudiantes universitarios."},
                        {"role": "user", "content": full_prompt}
                    ]
                )

                data = json.loads(completion.model_dump_json())
                bot_message = data['choices'][0]['message']['content']

                # Procesar markdown a HTML con resaltado de sintaxis
                md = markdown.Markdown(extensions=[
                    'codehilite',
                    'fenced_code'
                ])
                bot_message = md.convert(bot_message)
            except Exception as e:
                print(f"Error with OpenAI API: {e}")
                bot_message = "Sorry, there was an error with the AI service."

            ChatMessage.objects.create(session=session, sender='bot', message=bot_message)
            return JsonResponse({'bot_message': bot_message})

        except ChatSession.DoesNotExist:
            return JsonResponse({'error': 'Chat session not found'}, status=404)
        except Exception:
            return JsonResponse({'error': 'An error occurred'}, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)


@student_required
@login_required
def create_session_course(request, course_id):
    # Garantiza que el usuario pertenece a la materia
    if not Enrollment.objects.filter(student=request.user, course_id=course_id).exists():
        return redirect('courses:my_student_courses')
    session = ChatSession.objects.create(
        user=request.user,
        course_id=course_id,
        name=f"Chat {datetime.now().strftime('%H:%M')}"
    )
    return redirect('chatbot:chat_detail', session.id)


@student_required
@login_required
def delete_session(request, session_id):
    try:
        session = ChatSession.objects.get(id=session_id, user=request.user)
        course_id = session.course_id
        session.delete()
        if course_id:
            return redirect('chatbot:course_chat', course_id)
    except ChatSession.DoesNotExist:
        pass
    return redirect('chatbot:chatbot')


def get_chat_context(session, limit=5):
    """
    Devuelve los últimos mensajes en formato messages para OpenAI
    """
    recent_messages = ChatMessage.objects.filter(
        session=session
    ).order_by('-timestamp')[:limit]

    messages = []
    for msg in reversed(recent_messages):
        role = 'assistant' if msg.sender == 'bot' else 'user'
        messages.append({"role": role, "content": msg.message})
    return messages
