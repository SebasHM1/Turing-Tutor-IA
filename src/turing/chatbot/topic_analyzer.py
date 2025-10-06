import os
import json
from typing import Optional
from django.conf import settings
from openai import OpenAI
from django.utils import timezone
from .models import TopicWeight
from courses.models import CourseTopics

class TopicAnalyzer:
    def __init__(self):
        os.environ['OPENAI_API_KEY'] = getattr(settings, 'OPENAI_API_KEY', None) or os.getenv('OPENAI_API_KEY')
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def analyze_message_topic(self, message):
        """
        Analiza un mensaje y SOLO crea registro si está relacionado con un tema
        Retorna: TopicWeight o None
        """
        
        # Solo analizar mensajes de usuarios en cursos
        if not message.session.course_id or message.sender != 'user':
            return None
        
        # Obtener temas del curso
        topics = CourseTopics.objects.filter(
            course_id=message.session.course_id, 
            is_active=True
        )
        
        if not topics.exists():
            return None
        
        # Preparar contexto para la IA
        topics_context = self._prepare_topics_context(topics)
        
        # Llamar a la IA para analizar
        topic_id = self._call_ai_analysis(message.message, topics_context)
        
        # SOLO crear registro si encontró un tema relevante
        if topic_id is None:
            return None
        
        # Verificar que el topic_id existe
        if not CourseTopics.objects.filter(id=topic_id, course_id=message.session.course_id).exists():
            return None
        
        # Crear el peso (1 punto por mensaje relevante)
        topic_weight = TopicWeight.objects.create(
            message=message,
            student=message.session.user,
            course_id=message.session.course_id,
            topic_id=topic_id,
            date=timezone.now().date()
        )
        
        return topic_weight
    
    def _prepare_topics_context(self, topics) -> str:
        """Prepara el contexto de temas para la IA"""
        topics_list = []
        for topic in topics:
            topic_info = f"ID: {topic.id}, Nombre: {topic.name}"
            if topic.description:
                topic_info += f", Descripción: {topic.description}"
            if topic.keywords:
                topic_info += f", Palabras clave: {topic.keywords}"
            topics_list.append(topic_info)
        
        return "\n".join(topics_list)
    
    def _call_ai_analysis(self, user_message: str, topics_context: str) -> Optional[int]:
        """
        Llama a la IA para analizar el mensaje
        Retorna: topic_id o None
        """
        system_prompt = f"""
        Eres un analizador de temas educativos. Analiza si el mensaje del estudiante está relacionado con alguno de los temas del curso.

        TEMAS DISPONIBLES:
        {topics_context}

        CRITERIOS ESTRICTOS:
        - Solo responde con un tema si el mensaje está CLARAMENTE relacionado
        - El mensaje debe mencionar conceptos, preguntas o problemas del tema
        - Saludos, despedidas, agradecimientos generales = NO_TOPIC
        - Preguntas administrativas no relacionadas con el contenido = NO_TOPIC
        - Conversación casual = NO_TOPIC

        RESPONDE SOLO CON:
        - El ID del tema (número) si está relacionado
        - "NO_TOPIC" si no está relacionado

        NO uses JSON, solo responde el ID o NO_TOPIC.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.1
            )
            
            content = response.choices[0].message.content.strip()
            
            if content == "NO_TOPIC":
                return None
            
            try:
                topic_id = int(content)
                return topic_id
            except ValueError:
                return None
                
        except Exception as e:
            print(f"Error en análisis de temas: {e}")
            return None

# Instancia global
topic_analyzer = TopicAnalyzer()