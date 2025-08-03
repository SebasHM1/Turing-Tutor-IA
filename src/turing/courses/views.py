from django.shortcuts import render

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic import (CreateView, ListView, RedirectView)

from .models import Materia, ProfesorMateria
from .forms import MateriaForm


class SoloProfesoresMixin(UserPassesTestMixin):
    def test_func(self):
        return hasattr(self.request.user, 'role') and self.request.user.role == 'Teacher'


class MateriaCreateView(LoginRequiredMixin, SoloProfesoresMixin, CreateView):
    model = Materia
    form_class = MateriaForm
    # CAMBIO: Se elimina 'courses/'
    template_name = 'materia_form.html'
    success_url = reverse_lazy('courses:mis_materias')

    def form_valid(self, form):
        # Asigna el profesor responsable automáticamente
        form.instance.responsable = self.request.user
        response = super().form_valid(form)
        # El profesor queda vinculado a la materia que acaba de crear
        ProfesorMateria.objects.create(
            profesor=self.request.user,
            materia=self.object
        )
        return response


class MisMateriasView(LoginRequiredMixin, SoloProfesoresMixin, ListView):
    template_name = 'mis_materias.html'
    context_object_name = 'materias'

    def get_queryset(self):
        # Este es el queryset de las materias en las que el profesor está inscrito.
        return Materia.objects.filter(profesores__profesor=self.request.user).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Aquí obtenemos las materias en las que el profesor NO está inscrito.
        # Esta consulta es la que probablemente tenías en tu plantilla.
        materias_inscritas_ids = self.get_queryset().values_list('id', flat=True)
        context['otras_materias'] = Materia.objects.exclude(id__in=materias_inscritas_ids)
        return context


class UnirseMateriaView(LoginRequiredMixin, SoloProfesoresMixin, RedirectView):
    pattern_name = 'courses:mis_materias'

    def get_redirect_url(self, *args, **kwargs):
        materia = Materia.objects.get(pk=kwargs['pk'])
        ProfesorMateria.objects.get_or_create(profesor=self.request.user, materia=materia)
        return super().get_redirect_url(*args, **kwargs)


class SalirMateriaView(LoginRequiredMixin, SoloProfesoresMixin, RedirectView):
    pattern_name = 'courses:mis_materias'

    def get_redirect_url(self, *args, **kwargs):
        ProfesorMateria.objects.filter(
            profesor=self.request.user, materia_id=kwargs['pk']
        ).delete()
        return super().get_redirect_url(*args, **kwargs)