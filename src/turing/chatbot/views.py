from datetime import datetime

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.utils.html import escape

from users.decorators import student_required
from .models import ChatSession, ChatMessage
from courses.models import Enrollment, Course
from courses.rag_utils import rag_processor
from .topic_analyzer import topic_analyzer

import os
import json
from openai import OpenAI

import markdown
from markdown.extensions import codehilite




@login_required
def chatbot_view(request, session_id=None, course_id=None):
    """
    - Si viene course_id: abre (o crea) la última sesión del usuario para ese curso.
    - Si viene session_id: abre esa sesión (y deduce el curso).
    - Si no viene nada: abre la última sesión del usuario (puede no tener curso).
    """
    course = None
    session = None

    # 1) Entré por curso
    if course_id is not None:
        # validar matrícula por GRUPO 
        is_enrolled = Enrollment.objects.filter(student=request.user).filter(
            Q(group__course_id=course_id) | Q(legacy_course_id=course_id)
        ).exists()
        if not is_enrolled:
            return redirect('courses:my_student_groups')

        course = get_object_or_404(Course, pk=course_id)

        session = (ChatSession.objects
                   .filter(user=request.user, course_id=course_id)
                   .order_by('-created_at')
                   .first())
        if session is None:
            session = ChatSession.objects.create(
                user=request.user,
                course=course,
                name=f"Chat {datetime.now().strftime('%H:%M')}"
            )

    # 2) Entré por sesión
    elif session_id is not None:
        session = (ChatSession.objects
                   .filter(id=session_id, user=request.user)
                   .select_related('course')
                   .first())
        if session is None:
            return redirect('courses:my_student_groups')
        course = session.course

    # 3) Última sesión del usuario (fallback)
    else:
        session = (ChatSession.objects
                   .filter(user=request.user)
                   .order_by('-created_at')
                   .first())
        if session is None:
            session = ChatSession.objects.create(user=request.user, name="New Chat")
        course = session.course 
    messages = ChatMessage.objects.filter(session=session).order_by('timestamp')
    if course is not None:
        recent_chats = (ChatSession.objects
                        .filter(user=request.user, course=course)
                        .order_by('-created_at'))
    else:
        recent_chats = (ChatSession.objects
                        .filter(user=request.user)
                        .order_by('-created_at'))

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
            user_chat_message = ChatMessage.objects.create(session=session, sender='user', message=user_message)

            # ANÁLISIS DE TEMAS: Solo se guarda si está relacionado con un tema
            try:
                topic_analyzer.analyze_message_topic(user_chat_message)
            except Exception as e:
                print(f"Error en análisis de temas: {e}")

            try:
                # Configura la API Key de OpenAI
                os.environ['OPENAI_API_KEY'] = getattr(settings, 'OPENAI_API_KEY', None) or os.getenv('OPENAI_API_KEY')
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

                # Memoria de conversación
                context_messages = get_chat_context(session, limit=5)
                
                # RAG: Buscar contexto relevante de la base de conocimiento
                rag_context = ""
                if session.course_id:
                    try:
                        rag_context = rag_processor.create_rag_context(user_message, session.course_id)
                    except Exception:
                        rag_context = ""
                else:
                    rag_context = ""
                
                # Construir el prompt del sistema base
                system_prompt = "Eres un asistente de IA útil para estudiantes universitarios."
                
                # Preparar mensajes para OpenAI
                messages_for_api = [{"role": "system", "content": system_prompt}]
                
                # Añadir contexto de conversación (incluye prompt del curso si existe)
                messages_for_api.extend(context_messages)
                
                # Añadir contexto RAG si está disponible
                if rag_context:
                    messages_for_api.append({"role": "system", "content": rag_context})
                
                # Añadir mensaje del usuario
                messages_for_api.append({"role": "user", "content": user_message})

                completion = client.chat.completions.create(
                    model="gpt-4o-mini",  # Puedes cambiar el modelo si lo deseas
                    messages=messages_for_api
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
    is_enrolled = Enrollment.objects.filter(student=request.user).filter(
        Q(group__course_id=course_id) | Q(legacy_course_id=course_id)
    ).exists()
    if not is_enrolled:
        return redirect('courses:my_student_groups')

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
    Devuelve los últimos mensajes en formato messages para OpenAI,
    incluyendo siempre el prompt del curso si existe
    """
    recent_messages = ChatMessage.objects.filter(
        session=session
    ).order_by('-timestamp')[:limit]

    messages = []
    
    # Añadir prompt del curso al inicio del contexto si existe
    if session.course_id:
        try:
            from courses.models import CoursePrompt
            course_prompt = CoursePrompt.objects.get(course_id=session.course_id)
            if course_prompt.content.strip():
                # Incluir el prompt del curso como contexto del sistema
                course_context = f"""Instrucciones específicas para el curso {session.course.name}:
{course_prompt.content}

Recuerda seguir estas instrucciones en todas tus respuestas para este curso."""
                messages.append({"role": "system", "content": course_context})
        except CoursePrompt.DoesNotExist:
            # No hay prompt personalizado para este curso
            pass
        except Exception as e:
            print(f"Error loading course prompt: {e}")
    
    # Añadir historial de conversación
    for msg in reversed(recent_messages):
        role = 'assistant' if msg.sender == 'bot' else 'user'
        messages.append({"role": role, "content": msg.message})
        
    return messages

@login_required
@require_POST
def rename_session(request, pk):
    name = (request.POST.get('name') or '').strip()
    if not name:
        return HttpResponseBadRequest('Nombre requerido')
    
    session = get_object_or_404(ChatSession, id=pk, user=request.user)
    session.name = name[:80]
    session.save(update_fields=['name'])

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'name': session.name})
    return redirect('chatbot:chat_detail', pk=session.id)

@student_required
@login_required
@require_GET
def poll_messages(request):
    """
    Devuelve mensajes nuevos de una sesión, posteriores a after_id.
    Respuesta: { messages: [{id, sender, html, timestamp}] }
    """
    session_id = request.GET.get('session_id')
    after_id = request.GET.get('after_id')

    if not session_id:
        return JsonResponse({'error': 'session_id requerido'}, status=400)

    try:
        session = ChatSession.objects.select_related('course').get(id=session_id, user=request.user)
    except ChatSession.DoesNotExist:
        return JsonResponse({'error': 'Sesión no encontrada'}, status=404)

    qs = ChatMessage.objects.filter(session=session).order_by('id')
    if after_id:
        try:
            qs = qs.filter(id__gt=int(after_id))
        except ValueError:
            pass

    out = []
    for msg in qs:
        # El bot guarda HTML ya convertido con markdown; el usuario es texto plano.
        if msg.sender == 'user':
            html = escape(msg.message)  # evitamos inyección accidental
        else:
            html = msg.message  # ya es HTML seguro para mostrar

        out.append({
            'id': msg.id,
            'sender': msg.sender,
            'html': html,
            'timestamp': msg.timestamp.strftime('%H:%M'),
        })

    return JsonResponse({'messages': out})
