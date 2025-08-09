# tutor_inteligente/usuarios/urls.py
from django.urls import path
from . import views # Importaremos vistas personalizadas aquí más tarde
from .views import redirect_after_login, teacher_dashboard

app_name = 'usuarios' # Namespace para las URLs de esta app

urlpatterns = [
    #path('', views.registro_view, name='registro')

    path('redirect_after_login/', redirect_after_login, name='redirect_after_login'),

    # URL para el nuevo dashboard del profesor
    path('teacher/dashboard/', teacher_dashboard, name='teacher_dashboard'),

]