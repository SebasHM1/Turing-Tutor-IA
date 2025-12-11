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


class GroupManagementTests(TestCase):
    """Tests para creación y gestión de grupos."""
    
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client = Client()
        self.User = get_user_model()
        
        self.teacher = self.User.objects.create_user(
            email='teacher@groups.com', password='123', name='T', last_name='T',
            cedula='333', university_code='TG1', user_group='Staff',
            role=UserRole.TEACHER
        )
        
        self.course = Course.objects.create(name="Física", owner=self.teacher, level="2")

    def test_group_create_view(self):
        """Prueba la creación de un grupo dentro de un curso."""
        self.client.login(email='teacher@groups.com', password='123')
        url = reverse('teachers:group_create', kwargs={'course_pk': self.course.pk})
        
        data = {
            'name': 'Grupo A',
            'schedule': 'Lunes 8-10am'
        }
        
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Verificar que se creó el grupo
        self.assertTrue(Group.objects.filter(course=self.course, name='Grupo A').exists())
        group = Group.objects.get(course=self.course, name='Grupo A')
        self.assertEqual(group.teacher, self.teacher)

    def test_manage_course_view(self):
        """Prueba la vista de gestión de curso."""
        self.client.login(email='teacher@groups.com', password='123')
        group = Group.objects.create(course=self.course, teacher=self.teacher, name="Grupo 1")
        
        url = reverse('teachers:manage_course', kwargs={'pk': self.course.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['course'], self.course)
        self.assertIn(group, response.context['teacher_groups'])

    def test_group_prompt_edit_view(self):
        """Prueba la edición del prompt de IA específico de un grupo."""
        self.client.login(email='teacher@groups.com', password='123')
        group = Group.objects.create(course=self.course, teacher=self.teacher, name="Grupo 1")
        
        url = reverse('teachers:group_prompt_edit', kwargs={'group_pk': group.pk})
        
        data = {
            'ai_prompt': 'Instrucciones específicas para este grupo'
        }
        
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Verificar que el prompt fue actualizado
        group.refresh_from_db()
        self.assertEqual(group.ai_prompt, 'Instrucciones específicas para este grupo')


class TutoringManagementTests(TestCase):
    """Tests para gestión de monitorías."""
    
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client = Client()
        self.User = get_user_model()
        
        self.teacher = self.User.objects.create_user(
            email='teacher@tutoring.com', password='123', name='T', last_name='T',
            cedula='444', university_code='TU1', user_group='Staff',
            role=UserRole.TEACHER
        )
        
        self.course = Course.objects.create(name="Química", owner=self.teacher, level="3")
        self.group = Group.objects.create(course=self.course, teacher=self.teacher, name="Grupo A")

    def test_tutoring_schedule_list_view(self):
        """Prueba la vista de lista de horarios de monitoría."""
        self.client.login(email='teacher@tutoring.com', password='123')
        
        url = reverse('teachers:tutoring_schedules')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('course_rows', response.context)

    @override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
    def test_tutoring_schedule_upload_view(self):
        """Prueba la subida de un horario de monitoría."""
        self.client.login(email='teacher@tutoring.com', password='123')
        
        url = reverse('teachers:upload_schedule', kwargs={'course_pk': self.course.pk})
        
        pdf = SimpleUploadedFile("horario_monitoria.pdf", b"contenido_pdf", content_type="application/pdf")
        
        response = self.client.post(url, {'file': pdf}, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Verificar que se creó el horario
        self.assertTrue(TutoringSchedule.objects.filter(course=self.course).exists())

    def test_manage_tutoring_slots_get(self):
        """Prueba la vista GET de gestión de slots de monitoría."""
        self.client.login(email='teacher@tutoring.com', password='123')
        
        url = reverse('teachers:manage_tutoring', kwargs={'group_pk': self.group.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('formset', response.context)
        self.assertEqual(response.context['group'], self.group)

    def test_manage_tutoring_slots_post(self):
        """Prueba la creación de slots de monitoría vía POST."""
        self.client.login(email='teacher@tutoring.com', password='123')
        
        url = reverse('teachers:manage_tutoring', kwargs={'group_pk': self.group.pk})
        
        # Datos del formset (Django inline formset requiere datos específicos)
        data = {
            'tutoring_slots-TOTAL_FORMS': '1',
            'tutoring_slots-INITIAL_FORMS': '0',
            'tutoring_slots-MIN_NUM_FORMS': '0',
            'tutoring_slots-MAX_NUM_FORMS': '1000',
            'tutoring_slots-0-day': 'MON',
            'tutoring_slots-0-start_time': '10:00',
            'tutoring_slots-0-end_time': '12:00',
            'tutoring_slots-0-location': 'Sala 101',
        }
        
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Verificar que se creó el slot
        self.assertTrue(TutoringSlot.objects.filter(group=self.group).exists())


class TeacherPermissionTests(TestCase):
    """Tests para verificar permisos en vistas de profesores."""
    
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client = Client()
        self.User = get_user_model()
        
        self.teacher = self.User.objects.create_user(
            email='teacher@perm.com', password='123', name='T', last_name='T',
            cedula='1111', university_code='TP1', user_group='Staff',
            role=UserRole.TEACHER
        )
        
        self.other_teacher = self.User.objects.create_user(
            email='other@perm.com', password='123', name='O', last_name='O',
            cedula='2222', university_code='OP1', user_group='Staff',
            role=UserRole.TEACHER
        )
        
        self.course = Course.objects.create(name='Perm Course', owner=self.teacher, level='1')
        self.group = Group.objects.create(course=self.course, teacher=self.teacher, name='Perm Group')

    def test_teacher_of_group_can_manage_enrollments(self):
        """El profesor del grupo puede gestionar inscripciones."""
        self.client.login(email='teacher@perm.com', password='123')
        
        student = self.User.objects.create_user(
            email='student@perm.com', password='123', name='S', last_name='S',
            cedula='3333', university_code='SP1', user_group='G1',
            role=UserRole.STUDENT
        )
        
        url = reverse('teachers:manage_enrollments', kwargs={'group_pk': self.group.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)

    def test_course_owner_can_manage_enrollments(self):
        """El dueño del curso puede gestionar inscripciones aunque no sea el teacher del grupo."""
        # Crear un grupo con otro profesor
        other_group = Group.objects.create(
            course=self.course,
            teacher=self.other_teacher,
            name='Other Group'
        )
        
        # El dueño del curso (self.teacher) debería poder gestionar el grupo del otro profesor
        self.client.login(email='teacher@perm.com', password='123')
        
        url = reverse('teachers:manage_enrollments', kwargs={'group_pk': other_group.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)

    def test_unauthorized_teacher_cannot_manage_enrollments(self):
        """Un profesor no autorizado no puede gestionar inscripciones."""
        # Crear un curso de otro profesor
        other_course = Course.objects.create(
            name='Other Course',
            owner=self.other_teacher,
            level='1'
        )
        other_group = Group.objects.create(
            course=other_course,
            teacher=self.other_teacher,
            name='Other Group'
        )
        
        self.client.login(email='teacher@perm.com', password='123')
        
        url = reverse('teachers:manage_enrollments', kwargs={'group_pk': other_group.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 403)

    def test_manage_enrollments_invalid_post(self):
        """Prueba POST inválido en manage_enrollments."""
        self.client.login(email='teacher@perm.com', password='123')
        
        url = reverse('teachers:manage_enrollments', kwargs={'group_pk': self.group.pk})
        
        # POST sin student_id ni action
        response = self.client.post(url, {})
        
        self.assertEqual(response.status_code, 302)  # Redirige con error


class TeacherDashboardContextTests(TestCase):
    """Tests para verificar el contexto del dashboard."""
    
    def setUp(self):
        self.client = Client()
        self.User = get_user_model()
        
        self.teacher = self.User.objects.create_user(
            email='teacher@context.com', password='123', name='T', last_name='T',
            cedula='4444', university_code='TC1', user_group='Staff',
            role=UserRole.TEACHER
        )
        
        self.course1 = Course.objects.create(name='Course 1', owner=self.teacher, level='1')
        self.course2 = Course.objects.create(name='Course 2', owner=self.teacher, level='2')
        
        self.group1 = Group.objects.create(course=self.course1, teacher=self.teacher, name='Group 1')
        self.group2 = Group.objects.create(course=self.course2, teacher=self.teacher, name='Group 2')

    def test_dashboard_shows_manageable_courses(self):
        """El dashboard debe mostrar los cursos que el profesor puede gestionar."""
        self.client.login(email='teacher@context.com', password='123')
        
        url = reverse('teachers:dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('manageable_courses', response.context)
        
        manageable = list(response.context['manageable_courses'])
        self.assertIn(self.course1, manageable)
        self.assertIn(self.course2, manageable)

    def test_dashboard_shows_correct_counts(self):
        """El dashboard debe mostrar conteos correctos."""
        self.client.login(email='teacher@context.com', password='123')
        
        # Agregar algunos estudiantes
        student1 = self.User.objects.create_user(
            email='s1@context.com', password='123', name='S1', last_name='S1',
            cedula='5555', university_code='SC1', user_group='G1',
            role=UserRole.STUDENT
        )
        student2 = self.User.objects.create_user(
            email='s2@context.com', password='123', name='S2', last_name='S2',
            cedula='6666', university_code='SC2', user_group='G1',
            role=UserRole.STUDENT
        )
        
        Enrollment.objects.create(student=student1, group=self.group1)
        Enrollment.objects.create(student=student2, group=self.group1)
        Enrollment.objects.create(student=student1, group=self.group2)
        
        url = reverse('teachers:dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['active_groups'], 2)
        self.assertEqual(response.context['total_students'], 3)  # 2 en group1, 1 en group2


class TeacherModelsTests(TestCase):
    """Tests para modelos de teachers."""
    
    def setUp(self):
        self.User = get_user_model()
        
        self.teacher = self.User.objects.create_user(
            email='teacher@modtest.com', password='123', name='T', last_name='T',
            cedula='9999', university_code='TMT1', user_group='Staff',
            role=UserRole.TEACHER
        )

    def test_prompt_config_str(self):
        """Prueba el método __str__ de PromptConfig."""
        from teachers.models import PromptConfig
        
        prompt = PromptConfig.objects.create(
            key='test_key',
            content='Test content',
            updated_by=self.teacher
        )
        
        str_representation = str(prompt)
        self.assertIn('test_key', str_representation)
        self.assertIsInstance(str_representation, str)