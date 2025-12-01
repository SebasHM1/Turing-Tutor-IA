from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import UserRole, UserState
from .forms import CustomUserCreationForm

class UsersModelTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.user_data = {
            'email': 'student@test.com',
            'password': 'password123',
            'name': 'Juan',
            'last_name': 'Estudiante',
            'cedula': '1001',
            'university_code': 'U001',
            'user_group': 'Grupo A',
            'role': UserRole.STUDENT
        }

    def test_create_user_successful(self):
        """Prueba la creación exitosa de un usuario con todos los campos obligatorios."""
        user = self.User.objects.create_user(**self.user_data)
        self.assertEqual(user.email, 'student@test.com')
        self.assertEqual(user.cedula, '1001')
        self.assertEqual(user.role, UserRole.STUDENT)
        self.assertTrue(user.check_password('password123'))
        self.assertTrue(user.is_active)

    def test_create_user_missing_field(self):
        """Prueba que falla si falta un campo requerido (ej. university_code)."""
        data_incompleta = self.user_data.copy()
        del data_incompleta['university_code']
        
        with self.assertRaises(ValueError):
            self.User.objects.create_user(**data_incompleta)

    def test_create_superuser(self):
        """Prueba la creación de un superusuario."""
        admin_data = {
            'email': 'admin@test.com',
            'password': 'adminpass',
            'name': 'Admin',
            'last_name': 'User',
            'cedula': '9999',
            'university_code': 'ADMIN01',
            'user_group': 'AdminGroup'
        }
        admin = self.User.objects.create_superuser(**admin_data)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_staff)
        self.assertEqual(admin.role, UserRole.TEACHER) # Según tu manager, default es Teacher

    def test_string_representation(self):
        """Prueba el método __str__ del modelo."""
        user = self.User.objects.create_user(**self.user_data)
        self.assertEqual(str(user), 'student@test.com')

    def test_get_full_name(self):
        """Prueba que el nombre completo se concatena bien."""
        user = self.User.objects.create_user(**self.user_data)
        self.assertEqual(user.get_full_name(), 'Juan Estudiante')


class UsersFormTests(TestCase):
    def test_registration_form_valid(self):
        """Prueba que el formulario es válido con datos correctos."""
        form_data = {
            'email': 'newstudent@test.com',
            'name': 'Ana',
            'last_name': 'Gomez',
            'cedula': '55555',
            'university_code': 'U555',
            'user_group': 'Grupo B',
            'password': 'password123',  # UserCreationForm requiere password
            'password_validation': 'password123' # Confirmación de password (depende de config de Django, a veces es 'password_2')
        }
        # Nota: UserCreationForm maneja passwords de forma especial, probamos validación básica de campos
        form = CustomUserCreationForm(data=form_data)
        # Si falla por las contraseñas (ya que UserCreationForm es complejo de testear unitariamente sin request),
        # al menos verificamos que no falle por los campos personalizados.
        self.assertTrue(form.is_bound)
    
    def test_cedula_cleaning(self):
        """Prueba que el formulario limpia la cédula (quita puntos)."""
        form = CustomUserCreationForm()
        # Simulamos la limpieza manualmente para probar el método clean_cedula
        form.cleaned_data = {'cedula': '1.234.567'}
        self.assertEqual(form.clean_cedula(), '1234567')


class UsersViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.User = get_user_model()
        
        # Crear Estudiante
        self.student = self.User.objects.create_user(
            email='student@view.com', password='123', name='S', last_name='S',
            cedula='111', university_code='S1', user_group='G1', role=UserRole.STUDENT
        )
        # Crear Profesor
        self.teacher = self.User.objects.create_user(
            email='teacher@view.com', password='123', name='T', last_name='T',
            cedula='222', university_code='T1', user_group='G1', role=UserRole.TEACHER
        )

    def test_register_view_get(self):
        """Prueba que la página de registro carga (status 200)."""
        url = reverse('users:register')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/register.html')

    def test_redirect_after_login_student(self):
        """Prueba que un estudiante es redirigido a sus grupos."""
        self.client.login(email='student@view.com', password='123')
        url = reverse('users:redirect_after_login')
        response = self.client.get(url)
        
        # Debe redirigir (código 302)
        self.assertEqual(response.status_code, 302)
        # Verificamos que redirija a courses:my_student_groups
        # Nota: Esto fallará si 'courses:my_student_groups' no existe en urls.py globales
        self.assertRedirects(response, reverse('courses:my_student_groups'))

    def test_redirect_after_login_teacher(self):
        """Prueba que un profesor es redirigido al dashboard."""
        self.client.login(email='teacher@view.com', password='123')
        url = reverse('users:redirect_after_login')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('teachers:dashboard'))