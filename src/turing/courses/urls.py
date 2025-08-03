from django.urls import path
from .views import (
    MateriaCreateView, MisMateriasView,
    UnirseMateriaView, SalirMateriaView
)

app_name = 'courses'

urlpatterns = [
    path('nueva/', MateriaCreateView.as_view(), name='crear'),
    path('mis/',   MisMateriasView.as_view(),   name='mis_materias'),
    path('<int:pk>/unirse/', UnirseMateriaView.as_view(), name='unirse'),
    path('<int:pk>/salir/',  SalirMateriaView.as_view(),  name='salir'),
]
