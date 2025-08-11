# tutor_inteligente/turing/urls.py
from django.contrib import admin
from django.urls import path, include # Asegúrate de que include esté
from django.contrib.auth import views as auth_views
from users import views as user_views # <--- IMPORTANTE: Importa tus vistas de la app 'users'

urlpatterns = [
    # URL para el panel de administración - TODO: Cambia la URL si es necesario
    path('gestion-secreta-del-sitio/', admin.site.urls),

    path('', auth_views.LoginView.as_view(
                template_name='registration/login.html',
                redirect_authenticated_user=True
            ), name='login'),

    # TODO - Queda definida la url de logout pero falta la vista
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # URL para el Dashboard
    path('chatbot/', include('chatbot.urls')), # <-- INCLUYE LAS URLS DE CHATBOT AQUÍ

    # URL para el Registro
    path('register/', user_views.register_view, name='register'), # <--- NUEVA URL DE REGISTRO


    #URLS A IMPLEMENTAR CON RESETEO DE CONTRASENA
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='password_reset/form.html', 
        email_template_name='password_reset/email.html',
        html_email_template_name='password_reset/email.html'
        ), 
        name='password_reset'),

    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='password_reset/done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='password_reset/confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset/complete.html'), name='password_reset_complete'),

    path('courses/', include('courses.urls')),

    path('teachers/', include('teachers.urls')),

    path('users/', include('users.urls')),

]