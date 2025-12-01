import shutil
import tempfile
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from users.models import UserRole
from courses.models import Course, Group, Enrollment, TutoringSchedule, TutoringSlot
from .forms import TutoringSlotForm

# Carpeta temporal para simular subida de archivos (Monitorías PDF)
TEMP_MEDIA_ROOT = tempfile.mkdtemp()

@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class TeacherDashboardTests(TestCase):
    
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client = Client()
        self.User = get_user_model()
        
        # 1. Crear Profesor
        self.teacher = self.User.objects.create_user(
            email='profesor@test.com', password='123', name='Profe', last_name='P',
            cedula='123', university_code='T1', user_group='Staff', role=UserRole.TEACHER
        )
        
        # 2. Crear Estudiante
        self.student = self.User.objects.create_user(
            email='alumno@test.com', password='123', name='Alumno', last_name='A',
            cedula='456', university_code='S1', user_group='G1', role=UserRole.STUDENT
        )
        
        # 3. Crear Curso y Grupo
        self.course = Course.objects.create(name="Matemáticas", owner=self.teacher, level="1")
        self.group = Group.objects.create(course=self.course, teacher=self.teacher, name="Grupo A")

    def test_dashboard_access_teacher(self):
        """El profesor debe poder entrar al dashboard y ver sus grupos."""
        self.client.login(email='profesor@test.com', password='123')
        url = reverse('teachers:dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Matemáticas")
        self.assertContains(response, "Grupo A")

    def test_dashboard_access_student_forbidden(self):
        """Un estudiante debe recibir 403 Forbidden al intentar entrar al dashboard de profesores."""
        self.client.login(email='alumno@test.com', password='123')
        url = reverse('teachers:dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_create_course_view(self):
        """Prueba que un profesor puede crear un curso."""
        self.client.login(email='profesor@test.com', password='123')
        url = reverse('teachers:course_create')
        
        data = {
            'name': 'Física II',
            'description': 'Curso avanzado',
            'level': '3',
            'schedule': 'Mañanas'
        }
        
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Verificar que se creó en la base de datos
        self.assertTrue(Course.objects.filter(name='Física II').exists())
        # Verificar que el profesor es el dueño
        course = Course.objects.get(name='Física II')
        self.assertEqual(course.owner, self.teacher)

    def test_manage_enrollments_add_student(self):
        """Prueba agregar un estudiante a un grupo."""
        self.client.login(email='profesor@test.com', password='123')
        url = reverse('teachers:manage_enrollments', kwargs={'group_pk': self.group.pk})
        
        data = {
            'student_id': self.student.id,
            'action': 'add'
        }
        
        response = self.client.post(url, data, follow=True)
        
        # Verificar redirección y mensaje de éxito
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Enrollment.objects.filter(student=self.student, group=self.group).exists())

    def test_manage_enrollments_remove_student(self):
        """Prueba eliminar un estudiante de un grupo."""
        Enrollment.objects.create(student=self.student, group=self.group)
        
        self.client.login(email='profesor@test.com', password='123')
        url = reverse('teachers:manage_enrollments', kwargs={'group_pk': self.group.pk})
        
        data = {
            'student_id': self.student.id,
            'action': 'remove'
        }
        
        self.client.post(url, data, follow=True)
        
        # Verificar que ya no existe la inscripción
        self.assertFalse(Enrollment.objects.filter(student=self.student, group=self.group).exists())

    def test_upload_tutoring_schedule_pdf(self):
        """Prueba la subida de un horario de monitoría (PDF)."""
        self.client.login(email='profesor@test.com', password='123')
        url = reverse('teachers:upload_schedule', kwargs={'course_pk': self.course.pk})
        
        # Crear PDF falso en memoria
        pdf = SimpleUploadedFile("horario.pdf", b"contenido_dummy", content_type="application/pdf")
        
        response = self.client.post(url, {'file': pdf}, follow=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(TutoringSchedule.objects.filter(course=self.course).exists())

    def test_delete_course(self):
        """Prueba que el dueño puede borrar su curso."""
        self.client.login(email='profesor@test.com', password='123')
        url = reverse('teachers:course_delete', kwargs={'pk': self.course.pk})
        
        response = self.client.post(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Course.objects.filter(pk=self.course.pk).exists())


class TeacherFormsTests(TestCase):
    def test_tutoring_slot_form_valid(self):
        """Valida que el formulario de monitoría (slot) acepte datos correctos."""
        form_data = {
            'day': 'MON',
            'start_time': '10:00',
            'end_time': '12:00',
            'location': 'Sala 303'
        }
        form = TutoringSlotForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_tutoring_slot_form_invalid(self):
        """Valida que falle si falta un campo requerido (ej. ubicación)."""
        form_data = {
            'day': 'MON',
            'start_time': '10:00',
            'end_time': '12:00',
            # Falta location
        }
        form = TutoringSlotForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('location', form.errors)