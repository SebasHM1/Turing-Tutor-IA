import traceback
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy, reverse
from django.db import transaction, connection
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, ListView, RedirectView, FormView, UpdateView
from django.forms import inlineformset_factory
from django.core.exceptions import PermissionDenied

# --- Models ---
from courses.models import Course, Group, TutoringSchedule, TutoringSlot, Enrollment
from .models import PromptConfig
from users.models import CustomUser  # Asegúrate que este es tu modelo de usuario

# --- Forms ---
from courses.forms import CourseForm, TutoringScheduleForm
from .forms import PromptForm, TutoringSlotForm, GroupForm  # Asumimos que crearás un GroupForm

class TeachersOnlyMixin(UserPassesTestMixin):
    """Asegura que solo los usuarios con el rol 'Teacher' puedan acceder."""
    def test_func(self):
        return self.request.user.role == 'Teacher'

class TeacherDashboardView(LoginRequiredMixin, TeachersOnlyMixin, ListView):
    """
    Dashboard principal del profesor.
    Ahora muestra los GRUPOS que imparte, no los cursos.
    """
    template_name = 'dashboard.html' 
    context_object_name = 'groups'  # El objeto principal ahora son los grupos

    def get_queryset(self):
        # La consulta ahora es más simple: obtenemos los grupos asignados al profesor.
        return (Group.objects
                .filter(teacher=self.request.user)
                .select_related('course') # Optimizamos para obtener el curso relacionado
                .annotate(students_count=Count('enrollments')) # Contamos los estudiantes por grupo
                .distinct())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        my_groups = context['groups']
        
        # Opcional: Mostrar cursos donde el profesor podría crear nuevos grupos
        context['manageable_courses'] = Course.objects.filter(owner=self.request.user)
        
        context['active_groups'] = my_groups.count()
        context['total_students'] = my_groups.aggregate(total=Sum('students_count'))['total'] or 0
        context['active_page'] = 'dashboard'
        return context

class CourseCreateView(LoginRequiredMixin, TeachersOnlyMixin, CreateView):
    """
    Crea una nueva materia (Course). La lógica no cambia mucho,
    pero el éxito debería llevar a crear un grupo.
    """
    model = Course
    form_class = CourseForm
    template_name = 'course_form.html'

    def form_valid(self, form):
        # Asignamos al profesor actual como el 'owner' de la materia
        form.instance.owner = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        # Después de crear el curso, lo lógico es ir a crear el primer grupo
        messages.success(self.request, f"Materia '{self.object.name}' creada. Ahora, crea el primer grupo.")
        return reverse('teachers:group_create', kwargs={'course_pk': self.object.pk})

class GroupCreateView(LoginRequiredMixin, TeachersOnlyMixin, CreateView):
    """
    NUEVA VISTA: Para crear un nuevo grupo dentro de un curso existente.
    """
    model = Group
    form_class = GroupForm # Necesitarás crear este formulario
    template_name = 'group_form.html'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.course = get_object_or_404(Course, pk=self.kwargs['course_pk'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.course
        return context

    def form_valid(self, form):
        form.instance.course = self.course
        # Asignamos al profesor actual como el profesor del grupo
        form.instance.teacher = self.request.user
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('teachers:dashboard')

@login_required
@user_passes_test(lambda u: u.role == 'Teacher')
def manage_group_enrollments(request, group_pk):
    """
    NUEVA VISTA: Gestiona los estudiantes inscritos en un grupo específico.
    Permite añadir o eliminar estudiantes de la lista.
    """
    group = get_object_or_404(Group, pk=group_pk, teacher=request.user)
    
    enrolled_students_ids = Enrollment.objects.filter(group=group).values_list('student_id', flat=True)
    
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        action = request.POST.get('action')

        if not student_id or not action:
            messages.error(request, "Petición inválida.")
            return redirect('teachers:manage_enrollments', group_pk=group.pk)
            
        student = get_object_or_404(CustomUser, id=student_id, role='Student')

        if action == 'add':
            Enrollment.objects.get_or_create(student=student, group=group)
            messages.success(request, f"{student.get_full_name()} ha sido añadido al grupo.")
        elif action == 'remove':
            Enrollment.objects.filter(student=student, group=group).delete()
            messages.success(request, f"{student.get_full_name()} ha sido eliminado del grupo.")
        
        return redirect('teachers:manage_enrollments', group_pk=group.pk)

    # Preparamos el contexto para la plantilla
    context = {
        'group': group,
        'enrolled_students': CustomUser.objects.filter(id__in=enrolled_students_ids),
        'available_students': CustomUser.objects.filter(role='Student').exclude(id__in=enrolled_students_ids),
    }
    return render(request, 'manage_enrollments.html', context)


class TutoringScheduleListView(LoginRequiredMixin, TeachersOnlyMixin, ListView):
    """
    Muestra los CURSOS donde el profesor puede subir el PDF general de monitorías.
    Esta lógica puede mantenerse a nivel de curso si el PDF es general.
    """
    template_name = 'tutoring_schedule_list.html'
    context_object_name = 'courses'

    def get_queryset(self):
        # Muestra los cursos donde el profesor imparte al menos un grupo.
        course_ids = Group.objects.filter(teacher=self.request.user).values_list('course_id', flat=True)
        return (Course.objects
                .filter(id__in=course_ids)
                .prefetch_related('tutoring_schedule')
                .distinct())

class TutoringScheduleUploadView(LoginRequiredMixin, TeachersOnlyMixin, UpdateView):
    model = TutoringSchedule
    form_class = TutoringScheduleForm
    template_name = 'tutoring_schedule_form.html'
    
    def get_success_url(self):
        return reverse('teachers:tutoring_schedules')

    def get_object(self, queryset=None):
        self.course = get_object_or_404(Course, pk=self.kwargs['course_pk'])
        # Asegurarnos que el profesor tenga permiso sobre este curso
        if not Group.objects.filter(course=self.course, teacher=self.request.user).exists():
            raise PermissionDenied("No tienes permiso para editar el horario de este curso.")
        
        schedule, _ = TutoringSchedule.objects.get_or_create(course=self.course)
        return schedule

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.course
        return context

    def form_valid(self, form):
        schedule = form.save(commit=False)
        schedule.updated_by = self.request.user
        schedule.save()
        messages.success(self.request, f"Horario de monitorías para el curso '{self.course.name}' actualizado correctamente.")
        return super().form_valid(form)


@login_required
@user_passes_test(lambda u: u.role == 'Teacher')
def manage_tutoring_slots(request, group_pk):
    """
    Gestiona las monitorías personalizadas de un GRUPO.
    Ahora recibe group_pk en lugar de course_pk.
    """
    group = get_object_or_404(Group, pk=group_pk, teacher=request.user)

    TutoringSlotFormSet = inlineformset_factory(
        Group,  # El modelo padre ahora es Group
        TutoringSlot,
        form=TutoringSlotForm,
        extra=1,
        can_delete=True
    )

    if request.method == 'POST':
        formset = TutoringSlotFormSet(request.POST, instance=group)
        if formset.is_valid():
            formset.save()
            messages.success(request, "Horarios de monitoría actualizados exitosamente.")
            return redirect('teachers:dashboard') # O a una página de detalle del grupo
        else:
            messages.error(request, "Por favor corrige los errores en el formulario.")
    else:
        formset = TutoringSlotFormSet(instance=group)

    context = {
        'formset': formset,
        'group': group,
        'course': group.course
    }
    return render(request, 'manage_tutoring.html', context)


class PromptEditView(LoginRequiredMixin, TeachersOnlyMixin, UpdateView):
    # Sin cambios, ya que opera a nivel global
    model = PromptConfig
    form_class = PromptForm
    template_name = 'prompt_edit.html'
    success_url = reverse_lazy('teachers:prompt_edit')

    def get_object(self, queryset=None):
        obj, _ = PromptConfig.objects.get_or_create(key="global")
        return obj

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.updated_by = self.request.user
        obj.save()
        messages.success(self.request, _("¡Prompt actualizado!"))
        return super().form_valid(form)

class CourseDeleteView(LoginRequiredMixin, TeachersOnlyMixin, RedirectView):
    """
    Elimina un CURSO COMPLETO. Solo el 'owner' del curso puede hacerlo.
    Esto eliminará todos los grupos, inscripciones y monitorías asociadas.
    """
    pattern_name = 'teachers:dashboard'

    def post(self, request, *args, **kwargs):
        # Obtenemos el curso y verificamos que el usuario es el propietario
        course = get_object_or_404(Course, pk=kwargs['pk'], owner=self.request.user)
        course_name = course.name
        
        course.delete()
        
        messages.success(request, f"La materia '{course_name}' y todos sus grupos asociados han sido eliminados.")
        return redirect(self.get_redirect_url(*args, **kwargs))