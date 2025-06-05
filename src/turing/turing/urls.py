# tutor_inteligente/turing/urls.py
from django.contrib import admin
from django.urls import path, include # Asegúrate de que include esté
from django.contrib.auth import views as auth_views
from users import views as user_views # <--- IMPORTANTE: Importa tus vistas de la app 'users'

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', auth_views.LoginView.as_view(
                template_name='registration/login.html',
                redirect_authenticated_user=True
            ), name='login'),

    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # URL para el Dashboard
    path('dashboard/', user_views.dashboard_view, name='dashboard'), # <--- AÑADIDA/CONFIRMADA

    # URL para el Registro
    path('register/', user_views.register_view, name='register'), # <--- NUEVA URL DE REGISTRO

    # ... (URLs de reseteo de contraseña si las tienes)
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),


    # path('users/', include('users.urls')), <--- Puedes eliminar esto si defines las URLs de users directamente aquí
    # path('users/', include('django.contrib.auth.urls')), <--- También puedes eliminar esto si has definido login, logout, etc. explícitamente
]