import shutil
import tempfile
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, MagicMock
from users.models import UserRole
from .models import Course, Group, Enrollment, CoursePrompt, KnowledgeBaseFile
from .forms import CourseForm

# Creamos una ruta temporal para guardar los archivos durante los tests
TEMP_MEDIA_ROOT = tempfile.mkdtemp()

class CourseModelTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.teacher = self.User.objects.create_user(
            email='teacher@test.com', 
            password='123', 
            name='Profe', 
            last_name='Test',
            cedula='123', university_code='P1', user_group='Staff',
            role=UserRole.TEACHER
        )

    def test_course_creation_generates_code(self):
        """Prueba que al crear un curso sin código, se genera uno automáticamente."""
        course = Course.objects.create(
            name="Física I",
            description="Curso de prueba",
            level="1",
            owner=self.teacher
        )
        self.assertIsNotNone(course.code)
        self.assertTrue(len(course.code) > 0)
        self.assertEqual(str(course), "Física I")

    def test_group_creation(self):
        """Prueba la creación de un grupo asociado a un curso."""
        course = Course.objects.create(name="Química", owner=self.teacher, level="2")
        group = Group.objects.create(
            course=course,
            teacher=self.teacher,
            name="Grupo 01",
            schedule="Lun-Mie 10am"
        )
        self.assertEqual(group.course, course)
        self.assertEqual(str(group), "Química - Grupo 01")


class CourseFormTests(TestCase):
    def test_course_form_valid(self):
        """Prueba que el formulario de curso es válido con datos correctos."""
        form_data = {
            'name': 'Cálculo II',
            'description': 'Integrales',
            'level': '3',
            'schedule': 'Viernes 8am'
        }
        form = CourseForm(data=form_data)
        self.assertTrue(form.is_bound)
        self.assertTrue(form.is_valid())


# SOBREESCRIBIMOS LA RUTA DE MEDIA PARA QUE NO ENSUCIE EL PROYECTO
@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CourseViewTests(TestCase):
    
    @classmethod
    def tearDownClass(cls):
        """Se ejecuta al final de todos los tests de esta clase para borrar la carpeta temporal."""
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client = Client()
        self.User = get_user_model()
        
        # 1. Crear Profesor
        self.teacher = self.User.objects.create_user(
            email='teacher@courses.com', password='123', name='T', last_name='T',
            cedula='999', university_code='TP1', user_group='T',
            role=UserRole.TEACHER
        )
        
        # 2. Crear Estudiante
        self.student = self.User.objects.create_user(
            email='student@courses.com', password='123', name='S', last_name='S',
            cedula='888', university_code='SP1', user_group='S',
            role=UserRole.STUDENT
        )
        
        # 3. Crear Estudiante NO inscrito
        self.student_outsider = self.User.objects.create_user(
            email='outsider@courses.com', password='123', name='O', last_name='O',
            cedula='777', university_code='OP1', user_group='S',
            role=UserRole.STUDENT
        )

        # 4. Datos: Curso y Grupo
        self.course = Course.objects.create(name="IA Básica", owner=self.teacher, level="5")
        self.group = Group.objects.create(course=self.course, name="G1", teacher=self.teacher)
        
        # 5. Inscribir al estudiante
        Enrollment.objects.create(student=self.student, group=self.group)

    def test_my_student_groups_view(self):
        """El estudiante debe ver sus grupos inscritos."""
        self.client.login(email='student@courses.com', password='123')
        
        url = reverse('courses:my_student_groups')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "IA Básica")
        self.assertContains(response, "G1")
        self.assertIn('enrollments', response.context)
        self.assertEqual(len(response.context['enrollments']), 1)

    def test_student_group_detail_access(self):
        """El estudiante inscrito puede ver el detalle del grupo."""
        self.client.login(email='student@courses.com', password='123')
        url = reverse('courses:student_group_detail', kwargs={'pk': self.group.pk})
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_group'], self.group)

    def test_outsider_cannot_access_group_detail(self):
        """Un estudiante NO inscrito recibe 404 al intentar ver el grupo."""
        self.client.login(email='outsider@courses.com', password='123')
        url = reverse('courses:student_group_detail', kwargs={'pk': self.group.pk})
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_student_cannot_access_prompt_edit(self):
        """Un estudiante NO debe poder entrar a editar el prompt del curso (403 Forbidden)."""
        self.client.login(email='student@courses.com', password='123')
        url = reverse('courses:prompt_edit', kwargs={'pk': self.course.pk})
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_teacher_can_access_prompt_edit(self):
        """El profesor dueño del curso SÍ puede editar el prompt."""
        self.client.login(email='teacher@courses.com', password='123')
        CoursePrompt.objects.create(course=self.course)
        
        url = reverse('courses:prompt_edit', kwargs={'pk': self.course.pk})
        response = self.client.get(url)
        
        # Verificar que no es 403 (prohibido)
        self.assertNotEqual(response.status_code, 403)
        # Verificar que recibimos una respuesta exitosa
        self.assertIn(response.status_code, [200, 201])

    @patch('courses.views.rag_processor')
    def test_knowledge_base_upload(self, mock_rag):
        """
        Prueba la subida de un archivo a la base de conocimiento.
        """
        self.client.login(email='teacher@courses.com', password='123')
        
        mock_rag.process_pdf_file.return_value = {
            'success': True, 
            'chunks_count': 5, 
            'text_length': 100
        }

        url = reverse('courses:knowledge_base', kwargs={'pk': self.course.pk})
        
        pdf_content = b'%PDF-1.4 mock content'
        pdf_file = SimpleUploadedFile("test_doc.pdf", pdf_content, content_type="application/pdf")

        response = self.client.post(url, {
            'file': pdf_file,
            'name': 'Documento Test'
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        
        # Verificar que se creó el objeto
        self.assertTrue(KnowledgeBaseFile.objects.filter(course=self.course, name='Documento Test').exists())
        
        # Verificar que el mock fue llamado
        self.assertTrue(mock_rag.process_pdf_file.called)

    def test_knowledge_base_delete(self):
        """Prueba la eliminación de un archivo de la base de conocimiento."""
        self.client.login(email='teacher@courses.com', password='123')
        
        # Crear un archivo en la base de conocimiento
        kb_file = KnowledgeBaseFile.objects.create(
            course=self.course,
            name='Archivo para eliminar',
            file='knowledge_base/test.pdf'
        )
        
        url = reverse('courses:knowledge_base_delete', kwargs={
            'course_pk': self.course.pk,
            'file_pk': kb_file.pk
        })
        
        response = self.client.post(url, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Verificar que el archivo fue eliminado
        self.assertFalse(KnowledgeBaseFile.objects.filter(pk=kb_file.pk).exists())

    @patch('courses.views.rag_processor')
    def test_knowledge_base_reprocess(self, mock_rag):
        """Prueba el reprocesamiento de un archivo de la base de conocimiento."""
        self.client.login(email='teacher@courses.com', password='123')
        
        mock_rag.process_pdf_file.return_value = {
            'success': True, 
            'chunks_count': 10, 
            'text_length': 200
        }
        
        # Crear un archivo en la base de conocimiento
        kb_file = KnowledgeBaseFile.objects.create(
            course=self.course,
            name='Archivo para reprocesar',
            file='knowledge_base/test.pdf'
        )
        
        url = reverse('courses:knowledge_base_reprocess', kwargs={
            'course_pk': self.course.pk,
            'file_pk': kb_file.pk
        })
        
        response = self.client.post(url, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Verificar que el mock fue llamado
        self.assertTrue(mock_rag.process_pdf_file.called)

    def test_student_group_detail_full_context(self):
        """Prueba que StudentGroupDetailView devuelve el contexto completo."""
        self.client.login(email='student@courses.com', password='123')
        
        # Crear otro grupo para el mismo curso
        group2 = Group.objects.create(course=self.course, name="G2", teacher=self.teacher)
        
        url = reverse('courses:student_group_detail', kwargs={'pk': self.group.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_group'], self.group)
        self.assertEqual(response.context['course'], self.course)
        
        # Verificar que todos los grupos del curso están en el contexto
        groups_in_context = list(response.context['groups'])
        self.assertIn(self.group, groups_in_context)
        self.assertIn(group2, groups_in_context)


class CourseTopicsTests(TestCase):
    """Tests para CourseTopics, TopicKeyword y KeywordVariation."""
    
    def setUp(self):
        self.User = get_user_model()
        self.teacher = self.User.objects.create_user(
            email='teacher@topics.com', password='123', name='T', last_name='T',
            cedula='555', university_code='TT1', user_group='T',
            role=UserRole.TEACHER
        )
        self.course = Course.objects.create(name="Matemáticas", owner=self.teacher, level="1")

    def test_create_course_topic(self):
        """Prueba la creación de un tema de curso."""
        from courses.models import CourseTopics
        topic = CourseTopics.objects.create(
            course=self.course,
            name="Álgebra",
            description="Ecuaciones y sistemas",
            is_active=True
        )
        self.assertEqual(str(topic), "Matemáticas - Álgebra")
        self.assertTrue(topic.is_active)

    def test_create_topic_keyword(self):
        """Prueba la creación de palabras clave para un tema."""
        from courses.models import CourseTopics, TopicKeyword
        topic = CourseTopics.objects.create(
            course=self.course,
            name="Geometría",
            is_active=True
        )
        keyword = TopicKeyword.objects.create(
            topic=topic,
            keyword="triángulo"
        )
        self.assertEqual(str(keyword), "Geometría - triángulo")

    def test_create_keyword_variation(self):
        """Prueba la creación de variaciones de palabras clave."""
        from courses.models import CourseTopics, TopicKeyword, KeywordVariation
        topic = CourseTopics.objects.create(
            course=self.course,
            name="Geometría",
            is_active=True
        )
        keyword = TopicKeyword.objects.create(
            topic=topic,
            keyword="triángulo"
        )
        variation = KeywordVariation.objects.create(
            keyword=keyword,
            variation="triangulo"
        )
        self.assertEqual(str(variation), "triángulo → triangulo")

    def test_topic_unique_together(self):
        """Prueba que no se pueden crear temas duplicados para el mismo curso."""
        from courses.models import CourseTopics
        CourseTopics.objects.create(
            course=self.course,
            name="Álgebra",
            is_active=True
        )
        
        # Intentar crear otro tema con el mismo nombre debería fallar
        with self.assertRaises(Exception):
            CourseTopics.objects.create(
                course=self.course,
                name="Álgebra",
                is_active=True
            )


class CoursePromptEditViewTests(TestCase):
    """Tests para CoursePromptEditView."""
    
    def setUp(self):
        self.client = Client()
        self.User = get_user_model()
        
        self.teacher = self.User.objects.create_user(
            email='teacher@prompt.com', password='123', name='T', last_name='T',
            cedula='1234', university_code='TP1', user_group='Staff',
            role=UserRole.TEACHER
        )
        
        self.other_teacher = self.User.objects.create_user(
            email='other@prompt.com', password='123', name='O', last_name='O',
            cedula='5678', university_code='OP1', user_group='Staff',
            role=UserRole.TEACHER
        )
        
        self.course = Course.objects.create(name='Test Course', owner=self.teacher, level='1')

    def test_unauthorized_teacher_cannot_edit_prompt(self):
        """Un profesor que no es dueño ni imparte el curso no puede editar el prompt."""
        self.client.login(email='other@prompt.com', password='123')
        
        url = reverse('courses:prompt_edit', kwargs={'pk': self.course.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 403)

    def test_teacher_of_group_can_edit_prompt(self):
        """Un profesor que imparte un grupo del curso puede editar el prompt."""
        # Crear un grupo donde el otro profesor es el teacher
        group = Group.objects.create(
            course=self.course,
            teacher=self.other_teacher,
            name='Test Group'
        )
        
        self.client.login(email='other@prompt.com', password='123')
        
        url = reverse('courses:prompt_edit', kwargs={'pk': self.course.pk})
        response = self.client.get(url)
        
        # Verificar que no es 403 (prohibido)
        self.assertNotEqual(response.status_code, 403)
        # Verificar que recibimos una respuesta exitosa
        self.assertIn(response.status_code, [200, 201])


class KnowledgeBaseViewTests(TestCase):
    """Tests para vistas de Knowledge Base."""
    
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client = Client()
        self.User = get_user_model()
        
        self.teacher = self.User.objects.create_user(
            email='teacher@kb.com', password='123', name='T', last_name='T',
            cedula='1111', university_code='TK1', user_group='Staff',
            role=UserRole.TEACHER
        )
        
        self.other_teacher = self.User.objects.create_user(
            email='other@kb.com', password='123', name='O', last_name='O',
            cedula='2222', university_code='OK1', user_group='Staff',
            role=UserRole.TEACHER
        )
        
        self.course = Course.objects.create(name='KB Course', owner=self.teacher, level='1')

    def test_unauthorized_teacher_cannot_access_knowledge_base(self):
        """Un profesor no autorizado no puede acceder a la base de conocimiento."""
        self.client.login(email='other@kb.com', password='123')
        
        url = reverse('courses:knowledge_base', kwargs={'pk': self.course.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 403)

    @override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
    @patch('courses.views.rag_processor')
    def test_knowledge_base_upload_failure(self, mock_rag):
        """Prueba la subida cuando el procesamiento falla."""
        self.client.login(email='teacher@kb.com', password='123')
        
        mock_rag.process_pdf_file.return_value = {
            'success': False,
            'error': 'Processing error'
        }
        
        url = reverse('courses:knowledge_base', kwargs={'pk': self.course.pk})
        
        pdf = SimpleUploadedFile("error.pdf", b"content", content_type="application/pdf")
        
        response = self.client.post(url, {'file': pdf, 'name': 'Error Doc'}, follow=False)
        # Verificar que hay redirect después del error
        self.assertEqual(response.status_code, 302)

    @override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
    @patch('courses.views.rag_processor')
    def test_knowledge_base_upload_exception(self, mock_rag):
        """Prueba la subida cuando hay una excepción."""
        self.client.login(email='teacher@kb.com', password='123')
        
        mock_rag.process_pdf_file.side_effect = Exception('Unexpected error')
        
        url = reverse('courses:knowledge_base', kwargs={'pk': self.course.pk})
        
        pdf = SimpleUploadedFile("exception.pdf", b"content", content_type="application/pdf")
        
        response = self.client.post(url, {'file': pdf, 'name': 'Exception Doc'}, follow=False)
        # Verificar que hay redirect después de la excepción
        self.assertEqual(response.status_code, 302)
        
        # Verificar que el archivo fue creado pero marcado con error
        kb_file = KnowledgeBaseFile.objects.get(name='Exception Doc')
        self.assertFalse(kb_file.processed)
        self.assertIn('Unexpected error', kb_file.processing_error)


class RAGProcessorTests(TestCase):
    """Tests para RAGProcessor."""
    
    def setUp(self):
        from courses.rag_utils import RAGProcessor
        self.processor = RAGProcessor()
        self.User = get_user_model()
        
        self.teacher = self.User.objects.create_user(
            email='teacher@rag.com', password='123', name='T', last_name='T',
            cedula='1234', university_code='TR1', user_group='Staff',
            role=UserRole.TEACHER
        )
        
        self.course = Course.objects.create(name='RAG Course', owner=self.teacher, level='1')

    def test_clean_text(self):
        """Prueba la limpieza de texto."""
        dirty_text = "Hello   World!\n\n  Multiple    spaces"
        cleaned = self.processor.clean_text(dirty_text)
        
        self.assertNotIn('\n\n', cleaned)
        self.assertIn('Hello', cleaned)
        self.assertIn('World', cleaned)

    def test_chunk_text_empty(self):
        """Prueba chunking con texto vacío."""
        chunks = self.processor.chunk_text("")
        self.assertEqual(chunks, [])

    def test_chunk_text_small(self):
        """Prueba chunking con texto pequeño."""
        small_text = "This is a small text."
        chunks = self.processor.chunk_text(small_text)
        
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], small_text)

    def test_chunk_text_large(self):
        """Prueba chunking con texto grande."""
        # Crear texto mayor al chunk_size
        large_text = "Sentence. " * 150  # ~1350 caracteres
        chunks = self.processor.chunk_text(large_text)
        
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), self.processor.chunk_size + 100)

    def test_get_embeddings_tfidf(self):
        """Prueba embeddings con TF-IDF."""
        texts = ["Hello world", "Python programming", "Machine learning"]
        embeddings = self.processor.get_embeddings_tfidf(texts)
        
        self.assertEqual(len(embeddings), 3)
        self.assertIsInstance(embeddings[0], list)
        self.assertGreater(len(embeddings[0]), 0)

    @patch('courses.rag_utils.OpenAI')
    def test_get_embeddings_openai_success(self, mock_openai):
        """Prueba embeddings con OpenAI."""
        mock_client = mock_openai.return_value
        mock_response = type('Response', (), {
            'data': [
                type('Embedding', (), {'embedding': [0.1, 0.2, 0.3]})(),
                type('Embedding', (), {'embedding': [0.4, 0.5, 0.6]})()
            ]
        })()
        
        mock_client.embeddings.create.return_value = mock_response
        
        texts = ["Text 1", "Text 2"]
        embeddings = self.processor.get_embeddings_openai(texts)
        
        self.assertEqual(len(embeddings), 2)
        self.assertEqual(embeddings[0], [0.1, 0.2, 0.3])

    @patch('courses.rag_utils.OpenAI')
    def test_get_embeddings_openai_fallback(self, mock_openai):
        """Prueba fallback a TF-IDF cuando OpenAI falla."""
        mock_openai.side_effect = Exception('OpenAI error')
        
        texts = ["Hello", "World"]
        embeddings = self.processor.get_embeddings_openai(texts)
        
        self.assertEqual(len(embeddings), 2)
        self.assertIsInstance(embeddings[0], list)

    @patch('courses.rag_utils.PyPDF2.PdfReader')
    def test_extract_text_from_pdf_error(self, mock_reader):
        """Prueba manejo de error al extraer texto."""
        mock_reader.side_effect = Exception('PDF error')
        
        pdf = SimpleUploadedFile("test.pdf", b"content", content_type="application/pdf")
        
        with self.assertRaises(Exception) as cm:
            self.processor.extract_text_from_pdf(pdf)
        
        self.assertIn('Error extracting text', str(cm.exception))

    @override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
    @patch('courses.rag_utils.PyPDF2.PdfReader')
    def test_process_pdf_file_success(self, mock_reader):
        """Prueba procesamiento exitoso de PDF."""
        # Mock del reader
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Test content for PDF extraction."
        
        mock_pdf_reader = MagicMock()
        mock_pdf_reader.pages = [mock_page]
        mock_reader.return_value = mock_pdf_reader
        
        # Crear archivo
        pdf = SimpleUploadedFile("test.pdf", b"content", content_type="application/pdf")
        kb_file = KnowledgeBaseFile.objects.create(
            course=self.course,
            name='Test File',
            file=pdf
        )
        
        with patch.object(self.processor, 'get_embeddings_openai', return_value=[[0.1, 0.2, 0.3]]):
            result = self.processor.process_pdf_file(kb_file)
        
        self.assertTrue(result['success'])
        self.assertIn('chunks_count', result)
        
        kb_file.refresh_from_db()
        self.assertTrue(kb_file.processed)

    @override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
    def test_process_pdf_file_no_text(self):
        """Prueba procesamiento cuando no se extrae texto."""
        pdf = SimpleUploadedFile("empty.pdf", b"content", content_type="application/pdf")
        kb_file = KnowledgeBaseFile.objects.create(
            course=self.course,
            name='Empty File',
            file=pdf
        )
        
        with patch.object(self.processor, 'extract_text_from_pdf', return_value=''):
            result = self.processor.process_pdf_file(kb_file)
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)

    @override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
    @patch('courses.rag_utils.OpenAI')
    def test_find_relevant_chunks_with_file(self, mock_openai):
        """Prueba búsqueda de chunks con archivo procesado."""
        # Mock OpenAI
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        # Crear archivo con chunks
        pdf = SimpleUploadedFile("test.pdf", b"content", content_type="application/pdf")
        kb_file = KnowledgeBaseFile.objects.create(
            course=self.course,
            name='Test File',
            file=pdf,
            processed=True,
            text_chunks=['chunk 1', 'chunk 2'],
            embeddings=[[0.1, 0.2, 0.3], [0.2, 0.3, 0.4]]
        )
        
        chunks = self.processor.find_relevant_chunks("test query", self.course.id, limit=2)
        
        self.assertGreater(len(chunks), 0)
        self.assertIsInstance(chunks[0], tuple)
        self.assertEqual(len(chunks[0]), 2)  # (chunk, similarity)

    @patch('courses.rag_utils.OpenAI')
    def test_create_rag_context_with_chunks(self, mock_openai):
        """Prueba creación de contexto con chunks."""
        # Mock find_relevant_chunks para devolver datos
        with patch.object(self.processor, 'find_relevant_chunks', return_value=[
            ('Chunk 1 content', 0.9),
            ('Chunk 2 content', 0.8)
        ]):
            context = self.processor.create_rag_context("test query", self.course.id)
        
        self.assertNotEqual(context, "")
        self.assertIn('Fuente 1', context)
        self.assertIn('Chunk 1 content', context)
        self.assertIn('test query', context)
        """Prueba fallback a TF-IDF cuando OpenAI falla."""
        mock_openai.side_effect = Exception("API Error")
        
        texts = ["Text 1", "Text 2"]
        embeddings = self.processor.get_embeddings_openai(texts)
        
        # Debería usar TF-IDF como fallback
        self.assertEqual(len(embeddings), 2)
        self.assertIsInstance(embeddings[0], list)

    def test_find_relevant_chunks_no_files(self):
        """Prueba búsqueda de chunks cuando no hay archivos."""
        chunks = self.processor.find_relevant_chunks("query", self.course.id)
        self.assertEqual(chunks, [])

    @patch('courses.rag_utils.OpenAI')
    def test_find_relevant_chunks_with_file(self, mock_openai):
        """Prueba búsqueda de chunks con archivo procesado."""
        # Crear archivo con chunks y embeddings
        kb_file = KnowledgeBaseFile.objects.create(
            course=self.course,
            name='Test File',
            processed=True,
            text_chunks=['Chunk 1', 'Chunk 2'],
            embeddings=[[0.1, 0.2], [0.3, 0.4]]
        )
        
        # Mock OpenAI para query embedding
        mock_client = mock_openai.return_value
        mock_response = type('Response', (), {
            'data': [type('Embedding', (), {'embedding': [0.2, 0.3]})()]
        })()
        mock_client.embeddings.create.return_value = mock_response
        
        chunks = self.processor.find_relevant_chunks("test query", self.course.id, limit=2)
        
        self.assertLessEqual(len(chunks), 2)

    def test_create_rag_context_empty(self):
        """Prueba creación de contexto sin chunks relevantes."""
        context = self.processor.create_rag_context("query", self.course.id)
        self.assertEqual(context, "")


class TopicStatisticsServiceTests(TestCase):
    """Tests para TopicStatisticsService."""
    
    def setUp(self):
        from courses.topic_statistics import TopicStatisticsService
        from courses.models import CourseTopics, TopicKeyword
        from chatbot.models import TopicWeight
        from datetime import date
        
        self.service = TopicStatisticsService()
        self.User = get_user_model()
        
        self.teacher = self.User.objects.create_user(
            email='teacher@stats.com', password='123', name='T', last_name='T',
            cedula='5555', university_code='TS1', user_group='Staff',
            role=UserRole.TEACHER
        )
        
        self.student = self.User.objects.create_user(
            email='student@stats.com', password='123', name='S', last_name='S',
            cedula='6666', university_code='SS1', user_group='G1',
            role=UserRole.STUDENT
        )
        
        self.course = Course.objects.create(name='Stats Course', owner=self.teacher, level='1')
        self.group = Group.objects.create(course=self.course, teacher=self.teacher, name='Group 1')
        Enrollment.objects.create(student=self.student, group=self.group)
        
        # Crear tema y keyword
        self.topic = CourseTopics.objects.create(
            course=self.course,
            name='Test Topic',
            is_active=True
        )
        
        self.keyword = TopicKeyword.objects.create(
            topic=self.topic,
            keyword='test'
        )

    def test_get_student_topic_percentages_no_data(self):
        """Prueba obtener porcentajes sin datos."""
        percentages = self.service.get_student_topic_percentages(
            self.student.id, 
            self.course.id
        )
        
        self.assertEqual(percentages, [])

    def test_get_student_topic_percentages_with_data(self):
        """Prueba obtener porcentajes con datos."""
        from chatbot.models import ChatSession, ChatMessage, TopicWeight
        from datetime import date
        
        # Crear sesión y mensaje
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
        
        # Crear peso de tema
        TopicWeight.objects.create(
            message=message,
            student=self.student,
            course=self.course,
            topic=self.topic,
            keyword=self.keyword,
            date=date.today()
        )
        
        percentages = self.service.get_student_topic_percentages(
            self.student.id,
            self.course.id
        )
        
        self.assertEqual(len(percentages), 1)
        self.assertEqual(percentages[0]['topic'], 'Test Topic')
        self.assertEqual(percentages[0]['percentage'], 100.0)

    def test_get_student_keyword_breakdown_no_data(self):
        """Prueba desglose de keywords sin datos."""
        breakdown = self.service.get_student_keyword_breakdown(
            self.student.id,
            self.course.id
        )
        
        self.assertEqual(breakdown, [])

    def test_get_student_keyword_breakdown_with_data(self):
        """Prueba desglose de keywords con datos."""
        from chatbot.models import ChatSession, ChatMessage, TopicWeight
        from datetime import date
        
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
        
        TopicWeight.objects.create(
            message=message,
            student=self.student,
            course=self.course,
            topic=self.topic,
            keyword=self.keyword,
            date=date.today()
        )
        
        breakdown = self.service.get_student_keyword_breakdown(
            self.student.id,
            self.course.id
        )
        
        self.assertEqual(len(breakdown), 1)
        self.assertEqual(breakdown[0]['keyword'], 'test')

    def test_get_group_topic_percentages_no_data(self):
        """Prueba porcentajes de grupo sin datos."""
        percentages = self.service.get_group_topic_percentages(self.group.id)
        self.assertEqual(percentages, [])

    def test_get_group_topic_percentages_with_data(self):
        """Prueba obtener porcentajes de grupo con datos."""
        from chatbot.models import ChatSession, ChatMessage, TopicWeight
        from datetime import date
        
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
        
        TopicWeight.objects.create(
            message=message,
            student=self.student,
            course=self.course,
            topic=self.topic,
            keyword=self.keyword,
            date=date.today()
        )
        
        percentages = self.service.get_group_topic_percentages(self.group.id)
        
        self.assertEqual(len(percentages), 1)
        self.assertEqual(percentages[0]['topic'], 'Test Topic')
        self.assertGreater(percentages[0]['percentage'], 0)

    def test_get_group_keyword_breakdown_no_data(self):
        """Prueba desglose de keywords de grupo sin datos."""
        breakdown = self.service.get_group_keyword_breakdown(self.group.id)
        self.assertEqual(breakdown, [])

    def test_get_group_keyword_breakdown_with_data(self):
        """Prueba desglose de keywords de grupo con datos."""
        from chatbot.models import ChatSession, ChatMessage, TopicWeight
        from datetime import date
        
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
        
        TopicWeight.objects.create(
            message=message,
            student=self.student,
            course=self.course,
            topic=self.topic,
            keyword=self.keyword,
            date=date.today()
        )
        
        breakdown = self.service.get_group_keyword_breakdown(self.group.id)
        
        self.assertEqual(len(breakdown), 1)
        self.assertEqual(breakdown[0]['keyword'], 'test')
        self.assertEqual(breakdown[0]['topic'], 'Test Topic')

    def test_get_course_topic_percentages_no_data(self):
        """Prueba porcentajes de curso sin datos."""
        percentages = self.service.get_course_topic_percentages(self.course.id)
        self.assertEqual(percentages, [])

    def test_get_course_topic_percentages_with_data(self):
        """Prueba obtener porcentajes de curso con datos."""
        from chatbot.models import ChatSession, ChatMessage, TopicWeight
        from datetime import date
        
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
        
        TopicWeight.objects.create(
            message=message,
            student=self.student,
            course=self.course,
            topic=self.topic,
            keyword=self.keyword,
            date=date.today()
        )
        
        percentages = self.service.get_course_topic_percentages(self.course.id)
        
        self.assertEqual(len(percentages), 1)
        self.assertEqual(percentages[0]['topic'], 'Test Topic')
        self.assertGreater(percentages[0]['percentage'], 0)

    def test_get_course_keyword_breakdown_no_data(self):
        """Prueba desglose de keywords de curso sin datos."""
        breakdown = self.service.get_course_keyword_breakdown(self.course.id)
        self.assertEqual(breakdown, [])

    def test_get_course_keyword_breakdown_with_data(self):
        """Prueba desglose de keywords de curso con datos."""
        from chatbot.models import ChatSession, ChatMessage, TopicWeight
        from datetime import date
        
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
        
        TopicWeight.objects.create(
            message=message,
            student=self.student,
            course=self.course,
            topic=self.topic,
            keyword=self.keyword,
            date=date.today()
        )
        
        breakdown = self.service.get_course_keyword_breakdown(self.course.id)
        
        self.assertEqual(len(breakdown), 1)
        self.assertEqual(breakdown[0]['keyword'], 'test')
        self.assertEqual(breakdown[0]['topic'], 'Test Topic')

    def test_get_activity_summary_no_data(self):
        """Prueba resumen de actividad sin datos."""
        summary = self.service.get_activity_summary(self.course.id)
        self.assertEqual(list(summary), [])

    def test_get_activity_summary_with_data(self):
        """Prueba resumen de actividad con datos."""
        from chatbot.models import ChatSession, ChatMessage, TopicWeight
        from datetime import date
        
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
        
        TopicWeight.objects.create(
            message=message,
            student=self.student,
            course=self.course,
            topic=self.topic,
            keyword=self.keyword,
            date=date.today()
        )
        
        summary = self.service.get_activity_summary(self.course.id)
        
        self.assertGreater(len(summary), 0)
        self.assertIn('total_keywords', summary[0])
        self.assertIn('unique_students', summary[0])

    def test_get_top_topics_by_date_range(self):
        """Prueba obtener top topics por rango de fechas."""
        from chatbot.models import ChatSession, ChatMessage, TopicWeight
        from datetime import date, timedelta
        
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
        
        TopicWeight.objects.create(
            message=message,
            student=self.student,
            course=self.course,
            topic=self.topic,
            keyword=self.keyword,
            date=date.today()
        )
        
        start = date.today() - timedelta(days=7)
        end = date.today()
        
        top_topics = self.service.get_top_topics_by_date_range(
            self.course.id,
            start,
            end
        )
        
        self.assertGreater(len(top_topics), 0)
        self.assertIn('topic__name', top_topics[0].keys())

    def test_get_student_topic_percentages_with_date_range(self):
        """Prueba obtener porcentajes de estudiante con rango de fechas."""
        from chatbot.models import ChatSession, ChatMessage, TopicWeight
        from datetime import date, timedelta
        
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
        
        today = date.today()
        TopicWeight.objects.create(
            message=message,
            student=self.student,
            course=self.course,
            topic=self.topic,
            keyword=self.keyword,
            date=today
        )
        
        start = today - timedelta(days=7)
        end = today
        
        percentages = self.service.get_student_topic_percentages(
            self.student.id,
            self.course.id,
            start_date=start,
            end_date=end
        )
        
        self.assertEqual(len(percentages), 1)
        self.assertEqual(percentages[0]['topic'], 'Test Topic')

    def test_get_student_keyword_breakdown_with_filters(self):
        """Prueba desglose de keywords con filtros de tema y fecha."""
        from chatbot.models import ChatSession, ChatMessage, TopicWeight
        from datetime import date, timedelta
        
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
        
        today = date.today()
        TopicWeight.objects.create(
            message=message,
            student=self.student,
            course=self.course,
            topic=self.topic,
            keyword=self.keyword,
            date=today
        )
        
        start = today - timedelta(days=7)
        end = today
        
        breakdown = self.service.get_student_keyword_breakdown(
            self.student.id,
            self.course.id,
            topic_id=self.topic.id,
            start_date=start,
            end_date=end
        )
        
        self.assertEqual(len(breakdown), 1)
        self.assertEqual(breakdown[0]['keyword'], 'test')

    def test_get_group_keyword_breakdown_with_filters(self):
        """Prueba desglose de keywords de grupo con filtros."""
        from chatbot.models import ChatSession, ChatMessage, TopicWeight
        from datetime import date, timedelta
        
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
        
        today = date.today()
        TopicWeight.objects.create(
            message=message,
            student=self.student,
            course=self.course,
            topic=self.topic,
            keyword=self.keyword,
            date=today
        )
        
        start = today - timedelta(days=7)
        end = today
        
        breakdown = self.service.get_group_keyword_breakdown(
            self.group.id,
            topic_id=self.topic.id,
            start_date=start,
            end_date=end
        )
        
        self.assertEqual(len(breakdown), 1)
        self.assertEqual(breakdown[0]['keyword'], 'test')

    def test_get_course_keyword_breakdown_with_filters(self):
        """Prueba desglose de keywords de curso con filtros."""
        from chatbot.models import ChatSession, ChatMessage, TopicWeight
        from datetime import date, timedelta
        
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
        
        today = date.today()
        TopicWeight.objects.create(
            message=message,
            student=self.student,
            course=self.course,
            topic=self.topic,
            keyword=self.keyword,
            date=today
        )
        
        start = today - timedelta(days=7)
        end = today
        
        breakdown = self.service.get_course_keyword_breakdown(
            self.course.id,
            topic_id=self.topic.id,
            start_date=start,
            end_date=end
        )
        
        self.assertEqual(len(breakdown), 1)
        self.assertEqual(breakdown[0]['keyword'], 'test')


class ViewsProxyTests(TestCase):
    """Tests para views_proxy.py."""
    
    def setUp(self):
        self.client = Client()
        self.User = get_user_model()
        
        self.teacher = self.User.objects.create_user(
            email='teacher@proxy.com', password='123', name='T', last_name='T',
            cedula='7777', university_code='TP1', user_group='Staff',
            role=UserRole.TEACHER
        )
        
        self.student = self.User.objects.create_user(
            email='student@proxy.com', password='123', name='S', last_name='S',
            cedula='8888', university_code='SP1', user_group='G1',
            role=UserRole.STUDENT
        )
        
        self.course = Course.objects.create(name='Proxy Course', owner=self.teacher, level='1')
        self.group = Group.objects.create(course=self.course, teacher=self.teacher, name='Group 1')
        Enrollment.objects.create(student=self.student, group=self.group)

    def test_tutoring_schedule_proxy_no_authentication(self):
        """Usuario no autenticado debe ser redirigido."""
        url = reverse('courses:tutoring_schedule_proxy', kwargs={'pk': self.course.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_tutoring_schedule_proxy_not_enrolled(self):
        """Usuario no inscrito debe recibir 403."""
        other_student = self.User.objects.create_user(
            email='other@proxy.com', password='123', name='O', last_name='O',
            cedula='9999', university_code='OP1', user_group='G2',
            role=UserRole.STUDENT
        )
        
        self.client.force_login(other_student)
        url = reverse('courses:tutoring_schedule_proxy', kwargs={'pk': self.course.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 403)

    def test_tutoring_schedule_proxy_no_file(self):
        """Sin archivo debe devolver 404."""
        self.client.force_login(self.student)
        url = reverse('courses:tutoring_schedule_proxy', kwargs={'pk': self.course.pk})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)

    @patch('courses.views_proxy.requests.get')
    def test_tutoring_schedule_proxy_success(self, mock_get):
        """Proxy exitoso con archivo."""
        from courses.models import TutoringSchedule
        from courses.views_proxy import SUPABASE_ALLOWED_HOST
        from unittest.mock import PropertyMock
        
        # Crear horario sin archivo
        schedule = TutoringSchedule(course=self.course)
        
        # Mockear la URL del archivo para que contenga el host de Supabase
        mock_url = f'https://{SUPABASE_ALLOWED_HOST}/storage/v1/object/public/schedules/test.pdf'
        with patch.object(type(schedule.file), 'url', new_callable=PropertyMock, return_value=mock_url):
            schedule.save()
            
            # Mock de requests.get
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {
                'Content-Type': 'application/pdf',
                'Content-Length': '100',
                'Last-Modified': 'Mon, 01 Jan 2024 00:00:00 GMT',
                'ETag': '"abc123"'
            }
            mock_response.iter_content = MagicMock(return_value=[b'chunk1', b'chunk2'])
            mock_get.return_value = mock_response
            
            self.client.force_login(self.student)
            url = reverse('courses:tutoring_schedule_proxy', kwargs={'pk': self.course.pk})
            
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'application/pdf')

    @patch('courses.views_proxy.requests.get')
    def test_tutoring_schedule_proxy_304(self, mock_get):
        """Proxy debe devolver 304 si no hay modificaciones."""
        from courses.models import TutoringSchedule
        from courses.views_proxy import SUPABASE_ALLOWED_HOST
        from unittest.mock import PropertyMock
        
        # Crear horario
        schedule = TutoringSchedule(course=self.course)
        
        # Mockear la URL del archivo
        mock_url = f'https://{SUPABASE_ALLOWED_HOST}/storage/v1/object/public/schedules/test.pdf'
        with patch.object(type(schedule.file), 'url', new_callable=PropertyMock, return_value=mock_url):
            schedule.save()
            
            mock_response = MagicMock()
            mock_response.status_code = 304
            mock_get.return_value = mock_response
            
            self.client.force_login(self.student)
            url = reverse('courses:tutoring_schedule_proxy', kwargs={'pk': self.course.pk})
            
            response = self.client.get(url, HTTP_IF_MODIFIED_SINCE='Mon, 01 Jan 2024 00:00:00 GMT')
            
            self.assertEqual(response.status_code, 304)

    @patch('courses.views_proxy.requests.get')
    def test_tutoring_schedule_proxy_upstream_error(self, mock_get):
        """Proxy debe manejar errores de upstream."""
        from courses.models import TutoringSchedule
        from courses.views_proxy import SUPABASE_ALLOWED_HOST
        from unittest.mock import PropertyMock
        import requests
        
        # Crear horario
        schedule = TutoringSchedule(course=self.course)
        
        # Mockear la URL del archivo
        mock_url = f'https://{SUPABASE_ALLOWED_HOST}/storage/v1/object/public/schedules/test.pdf'
        with patch.object(type(schedule.file), 'url', new_callable=PropertyMock, return_value=mock_url):
            schedule.save()
            
            mock_get.side_effect = requests.RequestException('Connection error')
            
            self.client.force_login(self.student)
            url = reverse('courses:tutoring_schedule_proxy', kwargs={'pk': self.course.pk})
            
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, 502)

    @patch('courses.views_proxy.requests.get')
    def test_tutoring_schedule_proxy_upstream_404(self, mock_get):
        """Proxy debe devolver el status code de upstream si no es 200."""
        from courses.models import TutoringSchedule
        from courses.views_proxy import SUPABASE_ALLOWED_HOST
        from unittest.mock import PropertyMock
        
        # Crear horario
        schedule = TutoringSchedule(course=self.course)
        
        # Mockear la URL del archivo
        mock_url = f'https://{SUPABASE_ALLOWED_HOST}/storage/v1/object/public/schedules/test.pdf'
        with patch.object(type(schedule.file), 'url', new_callable=PropertyMock, return_value=mock_url):
            schedule.save()
            
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response
            
            self.client.force_login(self.student)
            url = reverse('courses:tutoring_schedule_proxy', kwargs={'pk': self.course.pk})
            
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, 404)