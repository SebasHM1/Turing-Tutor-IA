import re
from typing import List
from django.utils import timezone
from .models import TopicWeight
from courses.models import CourseTopics, TopicKeyword

class TopicAnalyzer:
    """
    Analizador de temas basado en regex para detectar palabras clave en mensajes.
    Reemplaza el sistema anterior basado en IA/NLP.
    """
    
    def analyze_message_topic(self, message):
        """
        Analiza un mensaje y crea un registro TopicWeight por cada palabra clave encontrada.
        Retorna: Lista de TopicWeight creados
        """
        
        # Solo analizar mensajes de usuarios en cursos
        if not message.session.course_id or message.sender != 'user':
            return []
        
        # Obtener temas activos del curso con sus keywords
        topics = CourseTopics.objects.filter(
            course_id=message.session.course_id, 
            is_active=True
        ).prefetch_related('keywords')
        
        if not topics.exists():
            return []
        
        # Buscar keywords en el mensaje
        matched_keywords = self._find_keywords_in_message(message.message, topics)
        
        if not matched_keywords:
            return []
        
        # Crear un TopicWeight por cada keyword encontrada
        weights_created = []
        for keyword_obj in matched_keywords:
            weight = TopicWeight.objects.create(
                message=message,
                student=message.session.user,
                course_id=message.session.course_id,
                topic=keyword_obj.topic,
                keyword=keyword_obj,
                date=timezone.now().date()
            )
            weights_created.append(weight)
        
        return weights_created
    
    def _find_keywords_in_message(self, message_text: str, topics) -> List:
        """
        Busca palabras clave en el mensaje usando regex flexible (case-insensitive).
        Busca tanto el keyword principal como sus variaciones.
        
        Ejemplos:
        - Keyword: "buenas prácticas de programación"
        - Variaciones: "buenas practicas", "mejores practicas", "clean code"
        - Cualquiera de estas detectará el keyword principal
        
        Retorna lista de objetos TopicKeyword únicos encontrados.
        """
        message_lower = message_text.lower()
        matched_keywords = set()
        
        for topic in topics:
            # Obtener keywords del tema (solo temas activos se pasan desde analyze_message_topic)
            keywords = topic.keywords.prefetch_related('variations')
            
            for keyword_obj in keywords:
                # Intentar match con el keyword principal
                if self._matches_text(keyword_obj.keyword, message_lower):
                    matched_keywords.add(keyword_obj)
                    continue  # Ya lo encontramos, no necesitamos revisar variaciones
                
                # Si no match el principal, intentar con las variaciones
                variations = keyword_obj.variations.all()
                for variation in variations:
                    if self._matches_text(variation.variation, message_lower):
                        matched_keywords.add(keyword_obj)
                        break  # Una variación es suficiente
        
        return list(matched_keywords)
    
    def _matches_text(self, search_term: str, message_lower: str) -> bool:
        """
        Verifica si un término de búsqueda está presente en el mensaje.
        Para términos multi-palabra, verifica que TODAS las palabras estén presentes.
        """
        search_term_lower = search_term.lower()
        words = search_term_lower.split()
        
        if len(words) == 1:
            # Para términos de una sola palabra, usar word boundary estricto
            pattern = r'\b' + re.escape(search_term_lower) + r'\b'
            return bool(re.search(pattern, message_lower))
        else:
            # Para frases multi-palabra, verificar que TODAS las palabras estén presentes
            # (no necesariamente consecutivas, permite flexibilidad)
            return all(
                re.search(r'\b' + re.escape(word) + r'\b', message_lower)
                for word in words
            )

# Instancia global
topic_analyzer = TopicAnalyzer()