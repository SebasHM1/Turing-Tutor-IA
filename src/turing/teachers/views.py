import traceback
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy, reverse
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, ListView, RedirectView, DetailView, UpdateView
from django.forms import inlineformset_factory
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse

from courses.models import Course, Group, TutoringSchedule, TutoringSlot, Enrollment, CourseTopics, TopicKeyword
from chatbot.models import TopicWeight
from users.models import CustomUser
from courses.forms import CourseForm, TutoringScheduleForm
from .forms import TutoringSlotForm, GroupForm


class TeachersOnlyMixin(UserPassesTestMixin):
    """Asegura que solo los usuarios con el rol 'Teacher' puedan acceder."""
    def test_func(self):
        return self.request.user.role == 'Teacher'

class TeacherDashboardView(LoginRequiredMixin, TeachersOnlyMixin, ListView):
    """
    Dashboard principal del profesor.
    Muestra los GRUPOS que imparte el profesor (no los cursos).
    """
    template_name = 'teachers/dashboard.html'
    context_object_name = 'groups'

    def get_queryset(self):
        # Grupos donde el usuario logueado es el profesor asignado
        return (
            Group.objects
            .filter(teacher=self.request.user)
            .select_related('course', 'teacher')
            .annotate(
                students_count=Count('enrollments', distinct=True)
            )
            .order_by('course__name', 'name')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        groups = context['groups']  # ahora sí son Group instances

        # Cursos que el profe "dueño" puede gestionar (para crear grupos nuevos)
        context['manageable_courses'] = Course.objects.filter(owner=self.request.user)

        context['active_groups'] = groups.count()
        context['total_students'] = groups.aggregate(total=Sum('students_count'))['total'] or 0
        context['active_page'] = 'dashboard'
        return context


class CourseCreateView(LoginRequiredMixin, TeachersOnlyMixin, CreateView):
    """
    Crea una nueva materia (Course). La lógica no cambia mucho,
    pero el éxito debería llevar a crear un grupo.
    """
    model = Course
    form_class = CourseForm
    template_name = 'teachers/forms/course_form.html'

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
    template_name = 'teachers/forms/group_form.html'

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
    Gestiona los estudiantes inscritos en un grupo.
    Permite añadir o eliminar. Permisos:
    - teacher del grupo
    - owner del curso
    - superuser
    """
    # Obtén el grupo sin filtrar por permisos aún
    group = get_object_or_404(
        Group.objects.select_related('course', 'teacher'),
        pk=group_pk
    )

    user = request.user
    is_owner = getattr(group.course, 'owner_id', None) == user.id
    is_teacher = getattr(group, 'teacher_id', None) == user.id

    if not (is_owner or is_teacher or user.is_superuser):
        raise PermissionDenied("No tienes permiso para gestionar este grupo.")

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

    context = {
        'active_page': 'manage_enrollments',
        'group': group,
        'enrolled_students': CustomUser.objects.filter(id__in=enrolled_students_ids),
        'available_students': CustomUser.objects.filter(role='Student').exclude(id__in=enrolled_students_ids),
    }
    return render(request, 'teachers/enrollment/manage_enrollments.html', context)



class TutoringScheduleListView(LoginRequiredMixin, TeachersOnlyMixin, ListView):
    template_name = 'teachers/schedules/tutoring_schedule_list.html'
    context_object_name = 'courses'

    def get_queryset(self):
        course_ids = Group.objects.filter(teacher=self.request.user).values_list('course_id', flat=True)
        return (Course.objects
                .filter(id__in=course_ids)
                .select_related('tutoring_schedule')
                .distinct())

    def get_context_data(self, **kwargs):
        from courses.models import TutoringSchedule 
        context = super().get_context_data(**kwargs)
        context['active_page'] = 'tutoring_schedules'
        
        rows = []
        for c in context['courses']:
            try:
                schedule = c.tutoring_schedule
            except TutoringSchedule.DoesNotExist:
                schedule = None

            has_file = bool(schedule and getattr(schedule.file, 'name', ''))
            file_url = schedule.file.url if has_file else None

            rows.append({
                'course': c,
                'schedule': schedule,
                'has_file': has_file,
                'file_url': file_url,
            })
        context['course_rows'] = rows
        return context


class TutoringScheduleUploadView(LoginRequiredMixin, TeachersOnlyMixin, UpdateView):
    model = TutoringSchedule
    form_class = TutoringScheduleForm
    template_name = 'teachers/schedules/tutoring_schedule_form.html'

    def get_object(self, queryset=None):
        self.course = get_object_or_404(Course, pk=self.kwargs['course_pk'])
        # Asegurarnos que el profesor tenga permiso sobre este curso
        if not Group.objects.filter(course=self.course, teacher=self.request.user).exists():
            raise PermissionDenied("No tienes permiso para editar el horario de este curso.")
        
        schedule, _ = TutoringSchedule.objects.get_or_create(course=self.course)
        return schedule

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_page'] = 'upload_schedule'
        context['course'] = self.course
        # Obtener el primer grupo del profesor para este curso (para el sidebar contextual)
        context['group'] = Group.objects.filter(course=self.course, teacher=self.request.user).first()
        return context

    def form_valid(self, form):
        schedule = form.save(commit=False)
        schedule.updated_by = self.request.user
        schedule.save()
        messages.success(self.request, f"Horario de monitorías para el curso '{self.course.name}' actualizado correctamente.")
        return super().form_valid(form)

    def get_success_url(self):
        # Redirigir al grupo si hay uno disponible
        group = Group.objects.filter(course=self.course, teacher=self.request.user).first()
        if group:
            return reverse('teachers:group_details', kwargs={'group_pk': group.pk})
        return reverse('teachers:dashboard')


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
        'active_page': 'manage_tutoring',
        'formset': formset,
        'group': group,
        'course': group.course
    }
    return render(request, 'teachers/course_management/manage_tutoring.html', context)

class ManageCourseView(LoginRequiredMixin, TeachersOnlyMixin, DetailView):
    """
    NUEVA VISTA: Panel de control para una materia específica.
    Desde aquí se gestionan los grupos, el prompt y la base de conocimiento.
    """
    model = Course
    template_name = 'teachers/course_management/manage_course.html'
    context_object_name = 'course'

    def get_queryset(self):
        # Asegura que un profesor solo pueda gestionar los cursos que posee
        # o en los que imparte al menos un grupo.
        course_ids = Group.objects.filter(teacher=self.request.user).values_list('course_id', flat=True)
        return Course.objects.filter(Q(owner=self.request.user) | Q(id__in=course_ids)).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pasamos los grupos de este curso que son impartidos por el profesor actual
        context['teacher_groups'] = self.object.groups.filter(teacher=self.request.user)
        context['active_page'] = 'manage_course'
        # Obtener el primer grupo del profesor para este curso (para el sidebar contextual)
        context['group'] = self.object.groups.filter(teacher=self.request.user).first()
        return context


@login_required
@user_passes_test(lambda u: u.role == 'Teacher')
def group_details(request, group_pk):
    """
    Vista de detalles de un grupo específico.
    Muestra toda la información del grupo, botones de acción y analytics de keywords.
    """
    group = get_object_or_404(Group, pk=group_pk, teacher=request.user)

    # Obtener estadísticas del grupo
    enrollments = Enrollment.objects.filter(group=group).select_related('student')
    student_ids = enrollments.values_list('student_id', flat=True)

    # Analytics de keywords para este grupo
    weights_qs = TopicWeight.objects.filter(
        student_id__in=student_ids,
        course=group.course
    ).select_related('topic', 'keyword', 'student', 'course')

    total_keywords_detected = weights_qs.count()
    total_students = enrollments.count()
    total_topics = weights_qs.values('topic').distinct().count()

    # Top 10 keywords más mencionados
    top_keywords = (
        weights_qs
        .values('keyword__keyword', 'topic__name')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )

    # Keywords por tema
    keywords_by_topic = (
        weights_qs
        .values('topic__name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    # Actividad de estudiantes (top 10 estudiantes más activos)
    top_students = (
        weights_qs
        .values('student__name', 'student__last_name', 'student__email')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )

    context = {
        'active_page': 'group_details',
        'group': group,
        'course': group.course,
        'total_students': total_students,
        'total_keywords_detected': total_keywords_detected,
        'total_topics': total_topics,
        'top_keywords': top_keywords,
        'keywords_by_topic': keywords_by_topic,
        'top_students': top_students,
    }

    return render(request, 'teachers/group_management/group_details.html', context)


@login_required
@user_passes_test(lambda u: u.role == 'Teacher')
def group_analytics(request, group_pk):
    """
    Vista de analytics de keywords para un grupo específico.
    """
    group = get_object_or_404(Group, pk=group_pk, teacher=request.user)

    # Obtener estadísticas del grupo
    enrollments = Enrollment.objects.filter(group=group).select_related('student')
    student_ids = enrollments.values_list('student_id', flat=True)

    # Analytics de keywords para este grupo
    weights_qs = TopicWeight.objects.filter(
        student_id__in=student_ids,
        course=group.course
    ).select_related('topic', 'keyword', 'student', 'course')

    total_keywords_detected = weights_qs.count()
    total_students = enrollments.count()
    total_topics = weights_qs.values('topic').distinct().count()

    # Top 10 keywords más mencionados
    top_keywords = (
        weights_qs
        .values('keyword__keyword', 'topic__name')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )

    # Keywords por tema
    keywords_by_topic = (
        weights_qs
        .values('topic__name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    # Actividad de estudiantes (top 10 estudiantes más activos)
    top_students = (
        weights_qs
        .values('student__name', 'student__last_name', 'student__email')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )

    # Tasa de participación (estudiantes que han tenido al menos un keyword detectado)
    students_with_activity = weights_qs.values('student').distinct().count()
    participation_rate = round((students_with_activity / total_students * 100), 1) if total_students > 0 else 0

    # Promedio de keywords por estudiante activo
    avg_keywords_per_student = round(total_keywords_detected / students_with_activity, 1) if students_with_activity > 0 else 0

    # Distribución de engagement (cuántos keywords tiene cada estudiante)
    student_engagement = list(
        weights_qs
        .values('student__name', 'student__last_name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    # Actividad reciente (últimos 7 días)
    from datetime import timedelta
    from django.utils import timezone
    seven_days_ago = timezone.now() - timedelta(days=7)
    recent_activity = weights_qs.filter(date__gte=seven_days_ago).count()

    context = {
        'active_page': 'group_analytics',
        'group': group,
        'course': group.course,
        'total_students': total_students,
        'total_keywords_detected': total_keywords_detected,
        'total_topics': total_topics,
        'students_with_activity': students_with_activity,
        'participation_rate': participation_rate,
        'recent_activity': recent_activity,
        'top_keywords': top_keywords,
        'keywords_by_topic': keywords_by_topic,
        'top_students': top_students,
        'avg_keywords_per_student': avg_keywords_per_student,
        'student_engagement': student_engagement,
    }

    return render(request, 'teachers/group_management/group_analytics.html', context)


class GroupPromptEditView(LoginRequiredMixin, TeachersOnlyMixin, UpdateView):
    """Edita el prompt de IA específico para un grupo."""
    model = Group
    fields = ['ai_prompt']
    template_name = 'teachers/prompts/group_prompt_edit.html'
    pk_url_kwarg = 'group_pk'

    def get_queryset(self):
        return Group.objects.filter(teacher=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_page'] = 'group_prompt_edit'
        context['group'] = self.object
        context['course'] = self.object.course
        return context

    def form_valid(self, form):
        messages.success(self.request, f"Prompt de IA actualizado para {self.object.name}")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('teachers:group_details', kwargs={'group_pk': self.object.pk})

class CourseDeleteView(LoginRequiredMixin, TeachersOnlyMixin, RedirectView):
    """
    Elimina un CURSO COMPLETO. Solo el 'owner' del curso puede hacerlo.
    Esto eliminará todos los grupos, inscripciones y monitorías asociadas.
    """
    pattern_name = 'teachers:dashboard'

    def get_redirect_url(self, *args, **kwargs):
        return reverse('teachers:dashboard')

    def post(self, request, *args, **kwargs):
        course = get_object_or_404(Course, pk=kwargs['pk'], owner=self.request.user)
        course_name = course.name

        course.delete()

        messages.success(request, f"La materia '{course_name}' y todos sus grupos asociados han sido eliminados.")
        return redirect('teachers:dashboard')


@login_required
@user_passes_test(lambda u: u.role == 'Teacher')
def keywords_analytics(request):
    """
    Dashboard de análisis de keywords para profesores.
    Muestra estadísticas y gráficas de los keywords detectados en las conversaciones de los estudiantes.
    Filtrado por grupo específico.
    """
    # Obtener los grupos donde el profesor imparte
    teacher_groups = Group.objects.filter(teacher=request.user).select_related('course').order_by('course__name', 'name')

    # Filtro por grupo (opcional)
    selected_group_id = request.GET.get('group', None)
    if selected_group_id:
        try:
            selected_group = Group.objects.get(id=selected_group_id, teacher=request.user)
        except Group.DoesNotExist:
            selected_group = None
    else:
        selected_group = None

    # Construir el queryset base de TopicWeight
    # Filtrar por estudiantes que pertenecen a los grupos del profesor
    if selected_group:
        # Obtener IDs de estudiantes inscritos en el grupo seleccionado
        student_ids = Enrollment.objects.filter(group=selected_group).values_list('student_id', flat=True)
        weights_qs = TopicWeight.objects.filter(
            student_id__in=student_ids,
            course=selected_group.course
        ).select_related('topic', 'keyword', 'student', 'course')
    else:
        # Obtener IDs de estudiantes inscritos en todos los grupos del profesor
        student_ids = Enrollment.objects.filter(
            group__in=teacher_groups
        ).values_list('student_id', flat=True).distinct()
        course_ids = teacher_groups.values_list('course_id', flat=True).distinct()
        weights_qs = TopicWeight.objects.filter(
            student_id__in=student_ids,
            course_id__in=course_ids
        ).select_related('topic', 'keyword', 'student', 'course')

    # Estadísticas generales
    total_keywords_detected = weights_qs.count()
    total_students = weights_qs.values('student').distinct().count()
    total_topics = weights_qs.values('topic').distinct().count()

    # Top 10 keywords más mencionados
    top_keywords = (
        weights_qs
        .values('keyword__keyword', 'topic__name')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )

    # Keywords por tema
    keywords_by_topic = (
        weights_qs
        .values('topic__name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    # Actividad de estudiantes (top 10 estudiantes más activos)
    top_students = (
        weights_qs
        .values('student__name', 'student__last_name', 'student__email')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )

    # Actividad por día (últimos 30 días)
    from django.utils import timezone
    from datetime import timedelta
    thirty_days_ago = timezone.now().date() - timedelta(days=30)

    activity_by_date = (
        weights_qs
        .filter(date__gte=thirty_days_ago)
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )

    context = {
        'active_page': 'keywords_analytics',
        'teacher_groups': teacher_groups,
        'selected_group': selected_group,
        'total_keywords_detected': total_keywords_detected,
        'total_students': total_students,
        'total_topics': total_topics,
        'top_keywords': top_keywords,
        'keywords_by_topic': keywords_by_topic,
        'top_students': top_students,
        'activity_by_date': list(activity_by_date),
    }

    return render(request, 'teachers/analytics/keywords_analytics.html', context) 