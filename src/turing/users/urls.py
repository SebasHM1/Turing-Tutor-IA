from django.urls import path
from .views import register_view, redirect_after_login

app_name = 'users'

urlpatterns = [
    path('redirect_after_login/', redirect_after_login, name='redirect_after_login'),
    path('register/', register_view, name='register'),
]
