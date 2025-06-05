# tutor_inteligente/usuarios/urls.py
from django.urls import path
from . import views # Importaremos vistas personalizadas aquí más tarde

app_name = 'usuarios' # Namespace para las URLs de esta app

urlpatterns = [
    path('', views.registro_view, name='registro')
]