from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    path('', views.chatbot_view, name='chatbot'),
    path('chat/<int:session_id>/', views.chatbot_view, name='chat_detail'),
    path('send_message/', views.send_message, name='send_message'),
    path('create_session/', views.create_session, name='create_session'),
    path('delete_session/<int:session_id>/', views.delete_session, name='delete_session'),
]