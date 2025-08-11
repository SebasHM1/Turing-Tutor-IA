# tutor_inteligente/users/models.py

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone

# Definición de los ENUMs como TextChoices para Django
class UserRole(models.TextChoices):
    STUDENT = 'Student', 'Estudiante' # El segundo valor es el 'human-readable'
    TEACHER = 'Teacher', 'Profesor'

class UserState(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Activo'
    INACTIVE = 'INACTIVE', 'Inactivo'

# Manager para el modelo de Usuario Personalizado
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
            # 'user_group' es el nombre en el modelo, no 'group'
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
    # Django usará automáticamente la columna 'id' (BIGSERIAL/SERIAL PK) de tu tabla.
    # No es necesario definir 'id = models.BigAutoField(primary_key=True)' aquí.

    # Campos de tu tabla 'public.usuarios'
    cedula = models.BigIntegerField(unique=True, help_text="Cédula de identidad del usuario (única).")
    name = models.TextField()
    last_name = models.TextField()
    email = models.EmailField(unique=True, help_text="Dirección de correo electrónico (única).")
    university_code = models.TextField(unique=True, help_text="Código universitario (único).")
    
    # Mapeo de la columna 'group' de la BD al campo 'user_group' en el modelo
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
        # Un método comúnmente esperado
        return f"{self.name} {self.last_name}".strip()

    def get_short_name(self):
        # Un método comúnmente esperado
        return self.name

    # Los métodos has_perm y has_module_perms son proporcionados por PermissionsMixin
    # si se usa el sistema de permisos estándar de Django.