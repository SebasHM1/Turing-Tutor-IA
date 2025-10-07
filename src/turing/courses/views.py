from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, UpdateView, FormView, RedirectView
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied

from .models import Course, Group, Enrollment, CoursePrompt, KnowledgeBaseFile

from .forms import CoursePromptForm, KnowledgeBaseFileForm

from .rag_utils import rag_processor


class StudentsOnlyMixin(UserPassesTestMixin):
    """Asegura que solo los usuarios con el rol 'Student' puedan acceder."""
    def test_func(self):
        # Verificamos que el usuario esté autenticado y tenga el rol correcto
        return self.request.user.is_authenticated and self.request.user.role == 'Student'

class TeachersOnlyMixin(UserPassesTestMixin):
    """Asegura que solo los usuarios con el rol 'Teacher' puedan acceder."""
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == 'Teacher'

class MyStudentGroupsView(LoginRequiredMixin, StudentsOnlyMixin, ListView):
    """
    [VISTA MODIFICADA] Muestra la lista de GRUPOS en los que el estudiante está inscrito.
    Reemplaza a la antigua 'MyStudentCoursesView'.
    """
    # La nueva plantilla mostrará una lista de los grupos del estudiante
    template_name = 'my_student_groups.html' 
    # El objeto de contexto ahora son las inscripciones (enrollments)
    context_object_name = 'enrollments'

    def get_queryset(self):
        """
        La consulta es más eficiente. Obtenemos las inscripciones del estudiante
        y usamos `select_related` para traer la información del grupo y el curso
        en la misma consulta, evitando múltiples accesos a la base de datos.
        """
        return (Enrollment.objects
                .filter(student=self.request.user, group__isnull=False)
                .select_related('group', 'group__course', 'group__teacher')
                .order_by('group__course__name', 'group__name'))

class StudentGroupDetailView(LoginRequiredMixin, StudentsOnlyMixin, DetailView):
    """
    Muestra la página de detalles de un GRUPO específico, incluyendo
    información del curso y todos los grupos del mismo curso con sus monitorías.
    """
    model = Group
    template_name = 'student_group_detail.html'
    context_object_name = 'current_group'

    def get_queryset(self):
        """
        Aseguramos que un estudiante solo pueda acceder a los grupos
        en los que está formalmente inscrito.
        """
        return Group.objects.filter(
            enrollments__student=self.request.user
        ).select_related('course', 'teacher')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group = self.get_object()
        
        context['course'] = group.course
        
        context['groups'] = group.course.groups.all().select_related(
            'teacher'
        ).prefetch_related('tutoring_slots')
        
        return context

class CoursePromptEditView(LoginRequiredMixin, TeachersOnlyMixin, UpdateView):
    model = CoursePrompt
    form_class = CoursePromptForm
    template_name = 'course_prompt_edit.html'

    def get_object(self, queryset=None):
        course = get_object_or_404(Course, pk=self.kwargs['pk'])
        # Verificamos que el profesor tenga permiso sobre este curso (es el dueño o imparte un grupo)
        if not (course.owner == self.request.user or Group.objects.filter(course=course, teacher=self.request.user).exists()):
            raise PermissionDenied("No tienes permisos para editar el prompt de este curso.")
            
        obj, _ = CoursePrompt.objects.get_or_create(course=course)
        return obj

    def get_success_url(self):
        return reverse_lazy('courses:prompt_edit', kwargs={'pk': self.object.course.pk})

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "El prompt del curso ha sido actualizado.")
        return super().form_valid(form)


class KnowledgeBaseView(LoginRequiredMixin, TeachersOnlyMixin, FormView):
    template_name = 'knowledge_base.html'
    form_class = KnowledgeBaseFileForm

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.course = get_object_or_404(Course, pk=self.kwargs['pk'])
        # Verificación de permisos
        if not (self.course.owner == request.user or Group.objects.filter(course=self.course, teacher=request.user).exists()):
             raise PermissionDenied("No tienes permisos para gestionar la base de conocimiento de este curso.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.course
        context['files'] = KnowledgeBaseFile.objects.filter(course=self.course)
        context['active_page'] = 'knowledge_base'
        return context

    def form_valid(self, form):
        file_obj = form.save(commit=False)
        file_obj.course = self.course
        
        if not file_obj.name and file_obj.file:
            file_obj.name = file_obj.file.name
        
        file_obj.save()
        messages.info(self.request, "Archivo subido. El procesamiento para la base de conocimiento ha comenzado en segundo plano.")
        
        try:
            result = rag_processor.process_pdf_file(file_obj)
            if result['success']:
                messages.success(self.request, f"PDF procesado exitosamente: {result['chunks_count']} fragmentos creados.")
            else:
                messages.warning(self.request, f"PDF subido, pero hubo un error al procesarlo: {result['error']}")
        except Exception as e:
            file_obj.processing_error = str(e)
            file_obj.processed = False
            file_obj.save()
            messages.error(self.request, f"Ocurrió un error inesperado durante el procesamiento del PDF: {e}")
        
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy('courses:knowledge_base', kwargs={'pk': self.kwargs['pk']})


class KnowledgeBaseDeleteView(LoginRequiredMixin, TeachersOnlyMixin, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        return reverse_lazy('courses:knowledge_base', kwargs={'pk': kwargs['course_pk']})
    
    def post(self, request, *args, **kwargs):
        file_obj = get_object_or_404(KnowledgeBaseFile, pk=kwargs['file_pk'], course_id=kwargs['course_pk'])
        
        # Verificación de permisos
        if not (file_obj.course.owner == request.user or Group.objects.filter(course=file_obj.course, teacher=request.user).exists()):
            raise PermissionDenied("No tienes permisos para eliminar este archivo.")

        file_obj.delete()
        messages.success(request, "Archivo eliminado exitosamente de la base de conocimiento.")
        return super().post(request, *args, **kwargs)

class KnowledgeBaseReprocessView(LoginRequiredMixin, TeachersOnlyMixin, RedirectView):
    """Reprocess a knowledge base file for RAG."""
    
    def get_redirect_url(self, *args, **kwargs):
        return reverse_lazy('courses:knowledge_base', kwargs={'pk': kwargs['course_pk']})
    
    def post(self, request, *args, **kwargs):
        course_pk = kwargs['course_pk']
        file_pk = kwargs['file_pk']
        
        try:
            file_obj = get_object_or_404(
                KnowledgeBaseFile, 
                pk=file_pk, 
                course_id=course_pk
            )
            
            result = rag_processor.process_pdf_file(file_obj)
            if result['success']:
                messages.success(
                    request, 
                    f"Archivo reprocesado exitosamente. {result['chunks_count']} fragmentos de texto creados."
                )
            else:
                messages.error(request, f"Error al reprocesar el archivo: {result['error']}")
                
        except Exception as e:
            messages.error(request, f"Error al reprocesar el archivo: {str(e)}")
        
        return super().post(request, *args, **kwargs)