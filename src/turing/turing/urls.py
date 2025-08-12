from django.contrib import admin
from django.urls import path, include
from users.views import TuringLoginView
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('gestion-secreta-del-sitio/', admin.site.urls),

    path('', TuringLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    path('chatbot/', include('chatbot.urls')),
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='password_reset/form.html',
        email_template_name='password_reset/email.html',
        html_email_template_name='password_reset/email.html'
    ), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='password_reset/done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='password_reset/confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='password_reset/complete.html'), name='password_reset_complete'),

    path('courses/', include('courses.urls')),
    path('teachers/', include('teachers.urls')),
    path('users/', include('users.urls')),
]
