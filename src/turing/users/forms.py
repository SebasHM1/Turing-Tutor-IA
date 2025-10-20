from django import forms
from django.contrib.auth.forms import UserCreationForm as DjangoUserCreationForm
from .models import CustomUser
from django.contrib.auth.forms import PasswordResetForm

class CustomUserCreationForm(DjangoUserCreationForm):
    name = forms.CharField(
        label="Nombre(s)",
        max_length=150,
        required=True,
        help_text='Tu nombre o nombres.'
    )
    last_name = forms.CharField(
        label="Apellido(s)",
        max_length=150,
        required=True,
        help_text='Tus apellidos.'
    )
    cedula = forms.IntegerField(
        label="Cédula",
        required=True,
        help_text='Tu número de cédula (sin puntos ni guiones).'
    )
    university_code = forms.CharField(
        label="Código de estudiante",
        max_length=50,
        required=True,
        help_text='Tu código único de estudiante.'
    )
    user_group = forms.CharField(
        label="Grupo",
        max_length=50,
        required=True,
        help_text='Tu grupo de clase.'
    )

    def clean_cedula(self):
        cedula = self.cleaned_data.get('cedula')
        if cedula:
            return ''.join(filter(str.isdigit, str(cedula)))
        return cedula

    class Meta(DjangoUserCreationForm.Meta):
        model = CustomUser
        fields = ('email', 'name', 'last_name', 'cedula', 'university_code', 'user_group')

class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        label="Email",
        max_length=254,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Ingresa tu correo electrónico'}),
        help_text='Ingresa el correo electrónico asociado a tu cuenta.'
    )
