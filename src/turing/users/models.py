
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone

class UserRole(models.TextChoices):
    STUDENT = 'Student', 'Estudiante' 
    TEACHER = 'Teacher', 'Profesor'

class UserState(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Activo'
    INACTIVE = 'INACTIVE', 'Inactivo'

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        """
        Crea y guarda un Usuario con el email y contraseña dados,
        y campos adicionales.
        """
        if not email:
            raise ValueError('El campo Email es obligatorio.')
        email = self.normalize_email(email)

        # Validar que los campos NOT NULL que no tienen default en el modelo Django
        # se proporcionen o lanzar un error.
        required_db_fields = ['name', 'last_name', 'cedula', 'university_code', 'user_group']
        for field_name in required_db_fields:
            model_field_name = field_name if field_name != 'group' else 'user_group'
            if model_field_name not in extra_fields or extra_fields[model_field_name] is None:
                raise ValueError(f'El campo "{model_field_name}" es obligatorio para crear un usuario.')

        user = self.model(email=email, **extra_fields)
        user.set_password(password) # Hashea la contraseña
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Crea y guarda un Superusuario con el email y contraseña dados.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('state', UserState.ACTIVE) # Superusuarios deben estar activos
        extra_fields.setdefault('role', UserRole.TEACHER)  # O un rol de administrador si lo tienes

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser debe tener is_superuser=True.')

        # Para createsuperuser, los campos en REQUIRED_FIELDS serán solicitados por consola.
        # Otros campos NOT NULL deben tener un valor por defecto aquí si no están en REQUIRED_FIELDS.
        # 'user_group' (columna 'group') es NOT NULL. Si no está en REQUIRED_FIELDS, necesita un default.
        # Si 'user_group' ESTÁ en REQUIRED_FIELDS (como recomendamos), la consola lo pedirá.
        # Si decidieras quitarlo de REQUIRED_FIELDS, necesitarías algo como:
        # extra_fields.setdefault('user_group', 'AdminGroup')

        return self.create_user(email, password, **extra_fields)


# Modelo de Usuario Personalizado
class CustomUser(AbstractBaseUser, PermissionsMixin):
    # Campos de tu tabla 'public.usuarios'
    cedula = models.CharField(max_length=20, unique=True, help_text="Cédula de identidad del usuario (única).")
    name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    university_code = models.CharField(max_length=50, unique=True, help_text="...")
    user_group = models.CharField(max_length=50, db_column='group', help_text="...")
    email = models.EmailField(unique=True, help_text="Dirección de correo electrónico (única).")

    user_group = models.TextField(db_column='group', help_text="Grupo de clase del usuario.")

    role = models.CharField(
        max_length=10, # 'Student' y 'Teacher' caben
        choices=UserRole.choices,
        default=UserRole.STUDENT,
    )
    state = models.CharField(
        max_length=10, # 'ACTIVE' e 'INACTIVE' caben
        choices=UserState.choices,
        default=UserState.ACTIVE,
    )

    # Campos requeridos por el sistema de autenticación de Django.
    # Django intentará añadir estas columnas a tu tabla 'public.usuarios' si no existen.
    is_active = models.BooleanField(
        default=True,
        help_text='Designa si este usuario debe ser tratado como activo. Desmarcar esto en lugar de borrar la cuenta.'
    )
    is_staff = models.BooleanField(
        default=False,
        help_text='Designa si el usuario puede iniciar sesión en el sitio de administración.'
    )
    # is_superuser es heredado de PermissionsMixin

    date_joined = models.DateTimeField(
        default=timezone.now,
        help_text='La fecha en que el usuario se unió.'
    )
    # password y last_login son manejados por AbstractBaseUser

    # Manager personalizado
    objects = CustomUserManager()

    # Campo usado para el login
    USERNAME_FIELD = 'email'

    # Campos requeridos al crear un usuario vía 'createsuperuser'
    # Todos estos campos son NOT NULL en tu BD (o deberían tener un default si no lo son).
    REQUIRED_FIELDS = ['name', 'last_name', 'cedula', 'university_code', 'user_group']

    class Meta:
        db_table = 'usuarios' # Le dice a Django que use esta tabla existente
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f"{self.name} {self.last_name}".strip()

    def get_short_name(self):
        return self.name
