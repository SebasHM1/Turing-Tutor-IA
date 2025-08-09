# tutor_inteligente/turing/urls.py
from django.contrib import admin
from django.urls import path, include # Asegúrate de que include esté
from django.contrib.auth import views as auth_views
from users import views as user_views # <--- IMPORTANTE: Importa tus vistas de la app 'users'

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', auth_views.LoginView.as_view(
                template_name='registration/login.html',
                redirect_authenticated_user=False
            ), name='login'),

    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

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

    path('courses/', include('courses.urls', namespace='courses')),

    # INCLUYE LAS URLS DE LA NUEVA APP DE PROFESORES
    path('teachers/', include('teachers.urls', namespace='teachers')),

    # INCLUYE LA URL DE REDIRECCIÓN DE LA APP USERS
    path('users/', include('users.urls', namespace='users')),

    #path('users/', include('django.contrib.auth.urls')), <--- También puedes eliminar esto si has definido login, logout, etc. explícitamente
]