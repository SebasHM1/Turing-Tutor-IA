# tutor_inteligente/users/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm as DjangoUserCreationForm
# No necesitamos importar AuthenticationForm si no lo estamos personalizando
from .models import CustomUser # UserRole y UserState no son necesarios aquí a menos que los uses explícitamente en el formulario

from django.contrib.auth.forms import PasswordResetForm

class CustomUserCreationForm(DjangoUserCreationForm):
    # Definimos explícitamente los campos que queremos en el formulario de registro
    # además de los que maneja UserCreationForm (email, password1, password2).
    
    name = forms.CharField(
        label="Nombre(s)",
        max_length=150,  # Coincidir con el max_length de User.first_name si es relevante, o TextField no tiene max_length
        required=True,
        help_text='Tu nombre o nombres.'
    )
    last_name = forms.CharField(
        label="Apellido(s)",
        max_length=150, # Coincidir con el max_length de User.last_name si es relevante
        required=True,
        help_text='Tus apellidos.'
    )
    cedula = forms.IntegerField( # O CharField si la cédula puede tener caracteres no numéricos
        label="Cédula",
        required=True,
        help_text='Tu número de cédula (sin puntos ni guiones).'
        # Podrías añadir validadores aquí si es necesario
    )
    university_code = forms.CharField(
        label="Código Universitario",
        max_length=50, # Ajusta según la longitud máxima esperada
        required=True,
        help_text='Tu código universitario único.'
    )
    user_group = forms.CharField(
        label="Grupo",
        max_length=50, # Ajusta según la longitud máxima esperada
        required=True,
        help_text='Tu grupo de clase.'
    )
    # El campo 'email' es manejado por UserCreationForm si es el USERNAME_FIELD.
    # Los campos 'password' (password1 y password2) también son manejados por UserCreationForm.

    # Opcional: Si quisieras permitir seleccionar rol y estado en el registro (generalmente no se hace)
    # role = forms.ChoiceField(choices=UserRole.choices, initial=UserRole.STUDENT, label="Rol")
    # state = forms.ChoiceField(choices=UserState.choices, initial=UserState.ACTIVE, label="Estado")

    def clean_cedula(self):
        cedula = self.cleaned_data.get('cedula')
        # Si la cédula es un CharField, la recibimos como string
        if cedula:
            # Elimina cualquier caracter que no sea un dígito
            return ''.join(filter(str.isdigit, str(cedula)))
        return cedula

    class Meta(DjangoUserCreationForm.Meta):
        model = CustomUser
        # Especificamos los campos que se mostrarán en el formulario y su orden.
        # 'email' se añade automáticamente por UserCreationForm si es USERNAME_FIELD.
        # 'password' (y su confirmación) también se añaden automáticamente.
        # Solo necesitamos listar los campos ADICIONALES que hemos definido arriba.
        fields = ('email', 'name', 'last_name', 'cedula', 'university_code', 'user_group')
        # Si también quisieras incluir 'role' y 'state' en el formulario:
        # fields = ('email', 'name', 'last_name', 'cedula', 'university_code', 'user_group', 'role', 'state')

# No es necesario un CustomAuthenticationForm si USERNAME_FIELD = 'email',
# ya que AuthenticationForm se adapta bien a esto.

class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        label="Email",
        max_length=254,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Ingresa tu correo electrónico'}),
        help_text='Ingresa el correo electrónico asociado a tu cuenta.'
    )