import shutil
import tempfile
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch
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
        
        self.assertEqual(response.status_code, 200)

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