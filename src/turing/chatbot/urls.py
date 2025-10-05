from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    path('', views.chatbot_view, name='chatbot'),
    path('course/<int:course_id>/', views.chatbot_view, name='course_chat'),
    path('course/<int:course_id>/create_session/', views.create_session_course, name='create_session_course'),
    path('chat/<int:session_id>/', views.chatbot_view, name='chat_detail'),
    path('send_message/', views.send_message, name='send_message'),
    path('delete_session/<int:session_id>/', views.delete_session, name='delete_session'),
    path('session/<int:pk>/rename/', views.rename_session, name='rename_session'),
    path('poll_messages/', views.poll_messages, name='poll_messages'),
]
