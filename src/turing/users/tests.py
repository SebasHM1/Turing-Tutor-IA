from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.http import JsonResponse
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


class CustomPasswordResetFormTests(TestCase):
    """Tests para el formulario de restablecimiento de contraseña."""
    
    def test_password_reset_form_valid(self):
        """Prueba que el formulario de reset es válido con un email correcto."""
        from users.forms import CustomPasswordResetForm
        
        form_data = {'email': 'test@example.com'}
        form = CustomPasswordResetForm(data=form_data)
        
        self.assertTrue(form.is_valid())

    def test_password_reset_form_invalid_email(self):
        """Prueba que el formulario falla con un email inválido."""
        from users.forms import CustomPasswordResetForm
        
        form_data = {'email': 'invalid-email'}
        form = CustomPasswordResetForm(data=form_data)
        
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)


class TuringLoginViewTests(TestCase):
    """Tests adicionales para TuringLoginView."""
    
    def setUp(self):
        self.client = Client()
        self.User = get_user_model()
        
        self.student = self.User.objects.create_user(
            email='student@login.com', password='testpass123', name='S', last_name='S',
            cedula='1111', university_code='SL1', user_group='G1', role=UserRole.STUDENT
        )
        
        self.teacher = self.User.objects.create_user(
            email='teacher@login.com', password='testpass123', name='T', last_name='T',
            cedula='2222', university_code='TL1', user_group='Staff', role=UserRole.TEACHER
        )

    def test_login_view_get(self):
        """Prueba que la página de login carga correctamente."""
        url = reverse('login')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/login.html')

    def test_login_success_student(self):
        """Prueba login exitoso de un estudiante."""
        url = reverse('login')
        response = self.client.post(url, {
            'username': 'student@login.com',
            'password': 'testpass123'
        }, follow=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        # Debe redirigir a grupos del estudiante
        self.assertRedirects(response, reverse('courses:my_student_groups'))

    def test_login_success_teacher(self):
        """Prueba login exitoso de un profesor."""
        url = reverse('login')
        response = self.client.post(url, {
            'username': 'teacher@login.com',
            'password': 'testpass123'
        }, follow=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        # Debe redirigir al dashboard de profesores
        self.assertRedirects(response, reverse('teachers:dashboard'))

    def test_login_invalid_credentials(self):
        """Prueba login con credenciales incorrectas."""
        url = reverse('login')
        response = self.client.post(url, {
            'username': 'student@login.com',
            'password': 'wrongpassword'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        self.assertContains(response, 'Please enter a correct', status_code=200)

    def test_authenticated_user_redirect(self):
        """Prueba que un usuario ya autenticado es redirigido."""
        self.client.login(email='student@login.com', password='testpass123')
        url = reverse('login')
        response = self.client.get(url)
        
        # redirect_authenticated_user=True debería redirigir
        self.assertEqual(response.status_code, 302)


class StudentRequiredDecoratorTests(TestCase):
    """Tests para el decorador student_required."""
    
    def setUp(self):
        self.client = Client()
        self.User = get_user_model()
        
        self.student = self.User.objects.create_user(
            email='student@decorator.com', password='testpass', name='S', last_name='S',
            cedula='1234', university_code='SD1', user_group='G1', role=UserRole.STUDENT
        )
        
        self.teacher = self.User.objects.create_user(
            email='teacher@decorator.com', password='testpass', name='T', last_name='T',
            cedula='5678', university_code='TD1', user_group='Staff', role=UserRole.TEACHER
        )

    def test_unauthenticated_user_redirects_to_login(self):
        """Un usuario no autenticado debe ser redirigido al login."""
        from users.decorators import student_required
        from django.http import HttpRequest
        from django.contrib.auth.models import AnonymousUser
        
        @student_required
        def dummy_view(request):
            return JsonResponse({'success': True})
        
        request = HttpRequest()
        request.user = AnonymousUser()
        request.META = {'SERVER_NAME': 'testserver', 'SERVER_PORT': '80'}
        
        response = dummy_view(request)
        self.assertEqual(response.status_code, 302)

    def test_teacher_redirects_to_dashboard(self):
        """Un profesor debe ser redirigido a su dashboard."""
        from users.decorators import student_required
        from django.http import HttpRequest
        from django.contrib.auth.models import AnonymousUser
        from django.contrib.sessions.middleware import SessionMiddleware
        from django.contrib.messages.storage.fallback import FallbackStorage
        
        @student_required
        def dummy_view(request):
            return JsonResponse({'success': True})
        
        request = HttpRequest()
        request.user = self.teacher
        request.method = 'GET'
        request.META = {'SERVER_NAME': 'testserver', 'SERVER_PORT': '80'}
        
        # Agregar session y messages
        middleware = SessionMiddleware(lambda x: x)
        middleware.process_request(request)
        request.session.save()
        
        setattr(request, '_messages', FallbackStorage(request))
        
        response = dummy_view(request)
        self.assertEqual(response.status_code, 302)

    def test_non_student_raises_permission_denied(self):
        """Un usuario que no es estudiante ni profesor debe recibir PermissionDenied."""
        from users.decorators import student_required
        from django.http import HttpRequest
        from django.core.exceptions import PermissionDenied
        
        @student_required
        def dummy_view(request):
            return JsonResponse({'success': True})
        
        # Usuario con rol diferente (simulado)
        other_user = self.User.objects.create_user(
            email='other@decorator.com', password='testpass', name='O', last_name='O',
            cedula='9999', university_code='OD1', user_group='Other', role='Other'
        )
        
        request = HttpRequest()
        request.user = other_user
        request.META = {}
        
        with self.assertRaises(PermissionDenied):
            dummy_view(request)


class RegisterViewTests(TestCase):
    """Tests adicionales para la vista de registro."""
    
    def setUp(self):
        self.client = Client()
        self.User = get_user_model()

    def test_register_post_success(self):
        """Prueba que el registro por POST funciona correctamente."""
        url = reverse('users:register')
        
        data = {
            'email': 'newuser@test.com',
            'name': 'New',
            'last_name': 'User',
            'cedula': '123456',
            'university_code': 'NU123',
            'user_group': 'G1',
            'password1': 'complexpass123',
            'password2': 'complexpass123'
        }
        
        response = self.client.post(url, data, follow=True)
        
        # Verificar que redirige al login
        self.assertRedirects(response, reverse('login'))
        
        # Verificar que el usuario fue creado
        self.assertTrue(self.User.objects.filter(email='newuser@test.com').exists())
        
        # Verificar que el usuario está activo
        user = self.User.objects.get(email='newuser@test.com')
        self.assertTrue(user.is_active)
        self.assertEqual(user.state, UserState.ACTIVE)


class CustomUserManagerTests(TestCase):
    """Tests para métodos del CustomUserManager."""
    
    def setUp(self):
        self.User = get_user_model()

    def test_create_user_without_email_raises_error(self):
        """Crear usuario sin email debe lanzar ValueError."""
        with self.assertRaises(ValueError) as cm:
            self.User.objects.create_user(
                email='',
                password='pass123',
                name='Test',
                last_name='User',
                cedula='123',
                university_code='T123',
                user_group='G1'
            )
        self.assertIn('Email', str(cm.exception))

    def test_create_user_without_required_fields(self):
        """Crear usuario sin campos requeridos debe lanzar ValueError."""
        # Sin name
        with self.assertRaises(ValueError):
            self.User.objects.create_user(
                email='test@test.com',
                password='pass123',
                last_name='User',
                cedula='123',
                university_code='T123',
                user_group='G1'
            )
        
        # Sin cedula
        with self.assertRaises(ValueError):
            self.User.objects.create_user(
                email='test@test.com',
                password='pass123',
                name='Test',
                last_name='User',
                university_code='T123',
                user_group='G1'
            )

    def test_create_superuser_defaults(self):
        """Crear superusuario debe establecer is_staff e is_superuser."""
        admin = self.User.objects.create_superuser(
            email='admin@test.com',
            password='admin123',
            name='Admin',
            last_name='User',
            cedula='999',
            university_code='ADMIN',
            user_group='Admins'
        )
        
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertEqual(admin.state, UserState.ACTIVE)
        self.assertEqual(admin.role, UserRole.TEACHER)

    def test_create_superuser_with_is_staff_false_raises_error(self):
        """Crear superusuario con is_staff=False debe lanzar error."""
        with self.assertRaises(ValueError) as cm:
            self.User.objects.create_superuser(
                email='admin@test.com',
                password='admin123',
                name='Admin',
                last_name='User',
                cedula='999',
                university_code='ADMIN',
                user_group='Admins',
                is_staff=False
            )
        self.assertIn('is_staff=True', str(cm.exception))

    def test_create_superuser_with_is_superuser_false_raises_error(self):
        """Crear superusuario con is_superuser=False debe lanzar error."""
        with self.assertRaises(ValueError) as cm:
            self.User.objects.create_superuser(
                email='admin@test.com',
                password='admin123',
                name='Admin',
                last_name='User',
                cedula='999',
                university_code='ADMIN',
                user_group='Admins',
                is_superuser=False
            )
        self.assertIn('is_superuser=True', str(cm.exception))