from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date
from chatbot.models import ChatSession, ChatMessage, TopicWeight
from courses.models import Course, CourseTopics, TopicKeyword, KeywordVariation
from chatbot.topic_analyzer import TopicAnalyzer
from django.test import Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
from courses.models import Group, Enrollment
from users.models import UserRole

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

class ChatbotViewTests(TestCase):
    """Test suite para las Vistas e Interacción del Chat (Mocking OpenAI)"""

    def setUp(self):
        self.client = Client()
        self.User = get_user_model()
        
        # 1. Crear Usuarios
        self.teacher = self.User.objects.create_user(
            email='profesor@chat.com', password='123', role=UserRole.TEACHER,
            name='Profe', last_name='T', cedula='555', university_code='TP1', user_group='Staff'
        )
        self.student = self.User.objects.create_user(
            email='alumno@chat.com', password='123', role=UserRole.STUDENT,
            name='Alumno', last_name='S', cedula='666', university_code='ST1', user_group='A'
        )
        
        # 2. Crear Curso, Grupo e Inscripción (Vital para acceder al chat)
        self.course = Course.objects.create(name="Inteligencia Artificial", owner=self.teacher, level="1")
        self.group = Group.objects.create(course=self.course, teacher=self.teacher, name="G1")
        Enrollment.objects.create(student=self.student, group=self.group)
        
        # 3. Crear sesión existente
        self.session = ChatSession.objects.create(user=self.student, course=self.course, name="Chat de Prueba")

    def test_view_access_enrolled_student(self):
        """Un estudiante inscrito puede acceder a la vista del chat."""
        self.client.login(email='alumno@chat.com', password='123')
        url = reverse('chatbot:course_chat', kwargs={'course_id': self.course.pk})
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chat de Prueba")

    def test_view_access_forbidden_not_enrolled(self):
        """Un estudiante NO inscrito debe ser redirigido."""
        # Curso extra sin inscripción
        course2 = Course.objects.create(name="Física", owner=self.teacher, level="1")
        
        self.client.login(email='alumno@chat.com', password='123')
        url = reverse('chatbot:course_chat', kwargs={'course_id': course2.pk})
        
        response = self.client.get(url)
        # Redirección a mis grupos (302)
        self.assertEqual(response.status_code, 302)

    @patch('chatbot.views.OpenAI')       # Mock de la clase OpenAI
    @patch('chatbot.views.rag_processor') # Mock del RAG
    def test_send_message_success(self, mock_rag, mock_openai):
        """
        Prueba el flujo completo de enviar mensaje POST.
        Simula la respuesta de OpenAI para no usar API real.
        """
        self.client.login(email='alumno@chat.com', password='123')

        # Configurar Mock de OpenAI
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_completion = MagicMock()
        # Simulamos la estructura JSON que devuelve OpenAI
        mock_completion.model_dump_json.return_value = '{"choices": [{"message": {"content": "Respuesta simulada del bot"}}]}'
        mock_client.chat.completions.create.return_value = mock_completion

        # Configurar Mock de RAG (para que no falle buscando PDFs)
        mock_rag.create_rag_context.return_value = ""

        # Enviar mensaje
        url = reverse('chatbot:send_message')
        data = {'session_id': self.session.id, 'message': 'Hola Bot'}
        
        response = self.client.post(url, data)
        
        # Validaciones
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'bot_message': '<p>Respuesta simulada del bot</p>'})
        
        # Verificar BD
        self.assertEqual(ChatMessage.objects.filter(session=self.session).count(), 2) # User + Bot
        self.assertTrue(ChatMessage.objects.filter(message='Hola Bot', sender='user').exists())

    def test_create_new_session(self):
        """Prueba crear una nueva sesión desde el botón."""
        self.client.login(email='alumno@chat.com', password='123')
        url = reverse('chatbot:create_session_course', kwargs={'course_id': self.course.pk})
        
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Debe haber 2 sesiones ahora (la del setUp y la nueva)
        self.assertEqual(ChatSession.objects.filter(user=self.student, course=self.course).count(), 2)

    def test_rename_session(self):
        """Prueba renombrar una sesión vía AJAX."""
        self.client.login(email='alumno@chat.com', password='123')
        url = reverse('chatbot:rename_session', kwargs={'pk': self.session.pk})
        
        # Simulamos petición AJAX
        response = self.client.post(url, {'name': 'Nuevo Nombre'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200)
        self.session.refresh_from_db()
        self.assertEqual(self.session.name, 'Nuevo Nombre')

    def test_delete_session(self):
        """Prueba eliminar una sesión."""
        self.client.login(email='alumno@chat.com', password='123')
        url = reverse('chatbot:delete_session', kwargs={'session_id': self.session.pk})
        
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        
        self.assertFalse(ChatSession.objects.filter(pk=self.session.pk).exists())


class ChatbotHelperTests(TestCase):
    """Tests para funciones helper del chatbot."""
    
    def setUp(self):
        self.User = get_user_model()
        
        self.teacher = self.User.objects.create_user(
            email='teacher@helpers.com', password='123', name='T', last_name='T',
            cedula='777', university_code='TH1', user_group='Teachers',
            role=UserRole.TEACHER
        )
        
        self.student = self.User.objects.create_user(
            email='student@helpers.com', password='123', name='S', last_name='S',
            cedula='888', university_code='SH1', user_group='Group A',
            role=UserRole.STUDENT
        )
        
        self.course = Course.objects.create(name='Test Course', owner=self.teacher, level='1')
        self.group = Group.objects.create(
            course=self.course, 
            teacher=self.teacher, 
            name='Test Group',
            ai_prompt='Test prompt for group'
        )
        Enrollment.objects.create(student=self.student, group=self.group)
        
        self.session = ChatSession.objects.create(
            user=self.student,
            course=self.course,
            name='Test Session'
        )

    def test_get_student_group(self):
        """Prueba que get_student_group devuelva el grupo correcto."""
        from chatbot.views import get_student_group
        
        group = get_student_group(self.student, self.course.id)
        self.assertEqual(group, self.group)

    def test_get_student_group_not_enrolled(self):
        """Prueba que get_student_group devuelva None si no está inscrito."""
        from chatbot.views import get_student_group
        
        other_student = self.User.objects.create_user(
            email='other@test.com', password='123', name='O', last_name='O',
            cedula='999', university_code='OS1', user_group='Group B',
            role=UserRole.STUDENT
        )
        
        group = get_student_group(other_student, self.course.id)
        self.assertIsNone(group)

    def test_get_chat_context_with_group_prompt(self):
        """Prueba que get_chat_context incluya el prompt del grupo."""
        from chatbot.views import get_chat_context
        
        # Crear algunos mensajes
        ChatMessage.objects.create(session=self.session, sender='user', message='Hola')
        ChatMessage.objects.create(session=self.session, sender='bot', message='Hola, ¿en qué puedo ayudarte?')
        
        context = get_chat_context(self.student, self.session, limit=5)
        
        # Verificar que hay mensajes en el contexto
        self.assertIsInstance(context, list)
        self.assertGreater(len(context), 0)
        
        # Verificar que el prompt del grupo está incluido
        system_messages = [msg for msg in context if msg.get('role') == 'system']
        self.assertTrue(any('Test prompt for group' in msg.get('content', '') for msg in system_messages))

    def test_get_chat_context_without_course(self):
        """Prueba get_chat_context con sesión sin curso."""
        from chatbot.views import get_chat_context
        
        session_no_course = ChatSession.objects.create(
            user=self.student,
            name='Session without course'
        )
        
        ChatMessage.objects.create(session=session_no_course, sender='user', message='Test')
        
        context = get_chat_context(self.student, session_no_course, limit=5)
        
        # No debería incluir prompt de grupo
        system_messages = [msg for msg in context if msg.get('role') == 'system']
        self.assertFalse(any('Test prompt for group' in msg.get('content', '') for msg in system_messages))

    def test_poll_messages(self):
        """Prueba el endpoint poll_messages."""
        self.client = Client()
        self.client.login(email='student@helpers.com', password='123')
        
        # Crear mensajes
        msg1 = ChatMessage.objects.create(session=self.session, sender='user', message='Mensaje 1')
        msg2 = ChatMessage.objects.create(session=self.session, sender='bot', message='Respuesta 1')
        
        url = reverse('chatbot:poll_messages')
        response = self.client.get(url, {
            'session_id': self.session.id,
            'after_id': msg1.id
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('messages', data)
        
        # Solo debería devolver mensajes después de msg1
        messages = data['messages']
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]['id'], msg2.id)

    def test_poll_messages_no_session_id(self):
        """Prueba poll_messages sin session_id."""
        self.client = Client()
        self.client.login(email='student@helpers.com', password='123')
        
        url = reverse('chatbot:poll_messages')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)

    def test_poll_messages_invalid_session(self):
        """Prueba poll_messages con ID de sesión inválido."""
        self.client.login(email='student@helpers.com', password='123')
        
        url = reverse('chatbot:poll_messages')
        response = self.client.get(url, {'session_id': '99999'})
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn('error', data)


class ChatbotViewEdgeCasesTests(TestCase):
    """Tests adicionales para cubrir casos edge en chatbot/views.py."""
    
    def setUp(self):
        self.client = Client()
        self.User = get_user_model()
        
        self.teacher = self.User.objects.create_user(
            email='teacher@edge.com', password='123', name='T', last_name='T',
            cedula='1111', university_code='TE1', user_group='Staff',
            role=UserRole.TEACHER
        )
        
        self.student = self.User.objects.create_user(
            email='student@edge.com', password='123', name='S', last_name='S',
            cedula='2222', university_code='SE1', user_group='G1',
            role=UserRole.STUDENT
        )
        
        self.course = Course.objects.create(name='Edge Course', owner=self.teacher, level='1')
        self.group = Group.objects.create(course=self.course, teacher=self.teacher, name='Edge Group')
        Enrollment.objects.create(student=self.student, group=self.group)

    def test_chatbot_view_with_invalid_session_id(self):
        """Prueba acceso con un session_id inválido."""
        self.client.login(email='student@edge.com', password='123')
        
        url = reverse('chatbot:chat_detail', kwargs={'session_id': 99999})
        response = self.client.get(url)
        
        # Debe redirigir a mis grupos
        self.assertEqual(response.status_code, 302)

    @patch('chatbot.views.OpenAI')
    @patch('chatbot.views.rag_processor')
    def test_send_message_with_rag_exception(self, mock_rag, mock_openai):
        """Prueba send_message cuando RAG falla."""
        self.client.login(email='student@edge.com', password='123')
        
        session = ChatSession.objects.create(
            user=self.student,
            course=self.course,
            name='RAG Error Session'
        )
        
        # Configurar mock de RAG para lanzar excepción
        mock_rag.create_rag_context.side_effect = Exception('RAG Error')
        
        # Configurar mock de OpenAI
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_completion = MagicMock()
        mock_completion.model_dump_json.return_value = '{"choices": [{"message": {"content": "Response"}}]}'
        mock_client.chat.completions.create.return_value = mock_completion
        
        url = reverse('chatbot:send_message')
        response = self.client.post(url, {
            'message': 'Test message',
            'session_id': session.id
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('bot_message', data)

    @patch('chatbot.views.OpenAI')
    def test_send_message_openai_exception(self, mock_openai):
        """Prueba send_message cuando OpenAI falla."""
        self.client.login(email='student@edge.com', password='123')
        
        session = ChatSession.objects.create(
            user=self.student,
            course=self.course,
            name='OpenAI Error Session'
        )
        
        # Configurar mock de OpenAI para lanzar excepción
        mock_openai.side_effect = Exception('OpenAI Error')
        
        url = reverse('chatbot:send_message')
        response = self.client.post(url, {
            'message': 'Test message',
            'session_id': session.id
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('Sorry, there was an error', data['bot_message'])

    def test_send_message_invalid_session(self):
        """Prueba send_message con sesión inválida."""
        self.client.login(email='student@edge.com', password='123')
        
        url = reverse('chatbot:send_message')
        response = self.client.post(url, {
            'message': 'Test message',
            'session_id': 99999
        })
        
        self.assertEqual(response.status_code, 404)

    def test_send_message_get_request(self):
        """Prueba send_message con GET request (debería fallar)."""
        self.client.login(email='student@edge.com', password='123')
        
        url = reverse('chatbot:send_message')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 400)

    def test_rename_session_not_ajax(self):
        """Prueba rename_session sin AJAX."""
        self.client.login(email='student@edge.com', password='123')
        
        session = ChatSession.objects.create(
            user=self.student,
            course=self.course,
            name='Old Name'
        )
        
        url = reverse('chatbot:rename_session', kwargs={'pk': session.pk})
        response = self.client.post(url, {'name': 'New Name'}, follow=True)
        
        # Debería redirigir a chat_detail (usando session_id)
        self.assertEqual(response.status_code, 200)
        session.refresh_from_db()
        self.assertEqual(session.name, 'New Name')

    def test_chatbot_view_with_course_creates_session(self):
        """Prueba que al acceder por course_id se crea una sesión si no existe."""
        self.client.login(email='student@edge.com', password='123')
        
        url = reverse('chatbot:course_chat', kwargs={'course_id': self.course.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Debe haber creado una sesión para este curso
        self.assertTrue(ChatSession.objects.filter(user=self.student, course=self.course).exists())


class ChatbotModelsTests(TestCase):
    """Tests para los métodos __str__ y propiedades de modelos."""
    
    def setUp(self):
        self.User = get_user_model()
        
        self.teacher = self.User.objects.create_user(
            email='teacher@models.com', password='123', name='T', last_name='T',
            cedula='1111', university_code='TM1', user_group='Staff',
            role=UserRole.TEACHER
        )
        
        self.student = self.User.objects.create_user(
            email='student@models.com', password='123', name='S', last_name='S',
            cedula='2222', university_code='SM1', user_group='G1',
            role=UserRole.STUDENT
        )
        
        self.course = Course.objects.create(name='Models Course', owner=self.teacher, level='1')

    def test_chat_session_str(self):
        """Prueba el método __str__ de ChatSession."""
        session = ChatSession.objects.create(
            user=self.student,
            course=self.course,
            name='Test Session'
        )
        
        # El __str__ debería contener información útil
        str_representation = str(session)
        self.assertIsInstance(str_representation, str)
        self.assertGreater(len(str_representation), 0)

    def test_chat_message_str(self):
        """Prueba el método __str__ de ChatMessage."""
        session = ChatSession.objects.create(
            user=self.student,
            course=self.course,
            name='Test Session'
        )
        
        message = ChatMessage.objects.create(
            session=session,
            sender='user',
            message='Test message'
        )
        
        str_representation = str(message)
        self.assertIsInstance(str_representation, str)

    def test_topic_weight_creation(self):
        """Prueba la creación de TopicWeight."""
        from courses.models import CourseTopics, TopicKeyword
        
        topic = CourseTopics.objects.create(
            course=self.course,
            name='Test Topic',
            is_active=True
        )
        
        keyword = TopicKeyword.objects.create(
            topic=topic,
            keyword='test'
        )
        
        session = ChatSession.objects.create(
            user=self.student,
            course=self.course,
            name='Test Session'
        )
        
        message = ChatMessage.objects.create(
            session=session,
            sender='user',
            message='test message'
        )
        
        weight = TopicWeight.objects.create(
            message=message,
            student=self.student,
            course=self.course,
            topic=topic,
            keyword=keyword,
            date=date.today()
        )
        
        self.assertEqual(weight.student, self.student)
        self.assertEqual(weight.keyword, keyword)