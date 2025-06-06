from django.urls import path
from . import views 

app_name = 'chatbot' 

urlpatterns = [
    path('', views.chatbot_view, name='chat_interface'),
    # Vamos aponer mas urls en un futuro
]