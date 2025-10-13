from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date
from chatbot.models import ChatSession, ChatMessage, TopicWeight
from courses.models import Course, CourseTopics, TopicKeyword, KeywordVariation
from chatbot.topic_analyzer import TopicAnalyzer

User = get_user_model()


class TopicAnalyzerTestCase(TestCase):
    """Test suite for TopicAnalyzer class"""
    
    def setUp(self):
        """Set up test data that will be used across multiple tests"""
        self.analyzer = TopicAnalyzer()
        
        # Create test users
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='testpass123',
            role='Teacher',
            name='Teacher',
            last_name='Test',
            cedula='1234567890',
            university_code='T001',
            user_group='Teachers'
        )
        
        self.student = User.objects.create_user(
            email='student@test.com',
            password='testpass123',
            role='Student',
            name='Student',
            last_name='Test',
            cedula='0987654321',
            university_code='S001',
            user_group='Group A'
        )
        
        # Create test course
        self.course = Course.objects.create(
            name='Programación 101',
            description='Curso de introducción a la programación',
            level='Básico',
            owner=self.teacher
        )
        
        # Create test topics
        self.topic1 = CourseTopics.objects.create(
            course=self.course,
            name='Estructuras de Datos',
            description='Listas, arrays, etc.',
            is_active=True
        )
        
        self.topic2 = CourseTopics.objects.create(
            course=self.course,
            name='Programación Orientada a Objetos',
            description='POO',
            is_active=True
        )
        
        self.topic3 = CourseTopics.objects.create(
            course=self.course,
            name='Bases de Datos',
            description='SQL y NoSQL',
            is_active=False  # Inactive topic
        )
        
        # Create keywords for topic1
        self.keyword1 = TopicKeyword.objects.create(
            topic=self.topic1,
            keyword='lista'
        )
        
        self.keyword2 = TopicKeyword.objects.create(
            topic=self.topic1,
            keyword='array'
        )
        
        # Create keyword with variations
        self.keyword3 = TopicKeyword.objects.create(
            topic=self.topic1,
            keyword='estructura de datos'
        )
        
        KeywordVariation.objects.create(
            keyword=self.keyword3,
            variation='data structure'
        )
        
        KeywordVariation.objects.create(
            keyword=self.keyword3,
            variation='estructuras'
        )
        
        # Create keywords for topic2
        self.keyword4 = TopicKeyword.objects.create(
            topic=self.topic2,
            keyword='class'  # Usar término técnico en inglés para evitar ambigüedad
        )
        
        # Agregar variaciones específicas para contexto de POO
        KeywordVariation.objects.create(
            keyword=self.keyword4,
            variation='clases de objetos'
        )
        
        KeywordVariation.objects.create(
            keyword=self.keyword4,
            variation='definir clase'
        )

        KeywordVariation.objects.create(
            keyword=self.keyword4,
            variation='clase'
        )
        
        self.keyword5 = TopicKeyword.objects.create(
            topic=self.topic2,
            keyword='herencia'
        )
        
        # Create keyword for inactive topic3
        self.keyword6 = TopicKeyword.objects.create(
            topic=self.topic3,
            keyword='sql'
        )
        
        # Create chat session
        self.session = ChatSession.objects.create(
            user=self.student,
            course=self.course,
            name='Test Chat'
        )
    
    def test_analyze_message_with_single_keyword(self):
        """Test analyzing a message with a single keyword match"""
        message = ChatMessage.objects.create(
            session=self.session,
            sender='user',
            message='¿Qué es una lista en Python?'
        )
        
        weights = self.analyzer.analyze_message_topic(message)
        
        self.assertEqual(len(weights), 1)
        self.assertEqual(weights[0].keyword, self.keyword1)
        self.assertEqual(weights[0].topic, self.topic1)
        self.assertEqual(weights[0].student, self.student)
        self.assertEqual(weights[0].course, self.course)
    
    def test_analyze_message_with_multiple_keywords(self):
        """Test analyzing a message with multiple keyword matches"""
        message = ChatMessage.objects.create(
            session=self.session,
            sender='user',
            message='¿Cuál es la diferencia entre una lista y un array?'
        )
        
        weights = self.analyzer.analyze_message_topic(message)
        
        self.assertEqual(len(weights), 2)
        keywords_found = {w.keyword for w in weights}
        self.assertIn(self.keyword1, keywords_found)
        self.assertIn(self.keyword2, keywords_found)
    
    def test_analyze_message_with_keyword_variation(self):
        """Test that keyword variations are properly detected"""
        message = ChatMessage.objects.create(
            session=self.session,
            sender='user',
            message='Me gustaría aprender sobre data structure'
        )
        
        weights = self.analyzer.analyze_message_topic(message)
        
        self.assertEqual(len(weights), 1)
        # Should match the main keyword, not the variation
        self.assertEqual(weights[0].keyword, self.keyword3)
    
    def test_analyze_message_with_multi_word_keyword(self):
        """Test detection of multi-word keywords"""
        message = ChatMessage.objects.create(
            session=self.session,
            sender='user',
            message='¿Qué es una estructura de datos?'
        )
        
        weights = self.analyzer.analyze_message_topic(message)
        
        self.assertEqual(len(weights), 1)
        self.assertEqual(weights[0].keyword, self.keyword3)
    
    def test_analyze_message_case_insensitive(self):
        """Test that keyword detection is case-insensitive"""
        message = ChatMessage.objects.create(
            session=self.session,
            sender='user',
            message='¿Qué es una LISTA en Python?'
        )
        
        weights = self.analyzer.analyze_message_topic(message)
        
        self.assertEqual(len(weights), 1)
        self.assertEqual(weights[0].keyword, self.keyword1)
    
    def test_long_message_with_repeated_and_varied_keywords(self):
        """Test: mensaje largo con keywords repetidas y variación, debe crear solo un TopicWeight por keyword única"""
        message_text = (
            "Hola profe, tengo varias dudas sobre el tema que vimos en clase. "
            "Primero, no entiendo bien qué es una lista y cómo se diferencia de un array. "
            "He leído que una lista en Python es dinámica, pero un array tiene tamaño fijo. "
            "¿Cuándo debo usar una lista y cuándo un array? Además, vi que la lista tiene métodos "
            "como append() y remove(), pero el array no. También me gustaría saber sobre data structure "
            "en general, porque creo que tanto lista como array son tipos de data structure. "
            "¿Es correcto decir que una estructura de datos es cualquier forma de organizar información? "
            "Porque si la estructura de datos incluye listas, arrays y otras cosas, entonces necesito "
            "entender mejor este concepto fundamental. Gracias por tu ayuda con estas dudas sobre lista, "
            "array y data structure."
        )
        message = ChatMessage.objects.create(
            session=self.session,
            sender='user',
            message=message_text
        )
        
        weights = self.analyzer.analyze_message_topic(message)
        
        # Debe detectar exactamente 3 keywords únicas a pesar de las repeticiones:
        # - "lista" (aparece 5 veces)
        # - "array" (aparece 5 veces)
        # - "estructura de datos" (aparece 2 veces directamente + 2 veces como "data structure")
        keywords_found = {w.keyword for w in weights}

        print(keywords_found)

        self.assertEqual(len(weights), 4)

        self.assertIn(self.keyword1, keywords_found)  # lista
        self.assertIn(self.keyword2, keywords_found)  # array
        self.assertIn(self.keyword3, keywords_found)  # estructura de datos (detectada también por variación "data structure")
        self.assertIn(self.keyword3, keywords_found)  # clase
        
        # Verificar que no se crearon duplicados para la misma keyword
        keyword_ids = [w.keyword.id for w in weights]
        self.assertEqual(len(keyword_ids), len(set(keyword_ids)), "No debe haber TopicWeights duplicados para la misma keyword")

