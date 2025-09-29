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


from courses.models import Course, TeacherCourse, TutoringSchedule, TutoringSlot 
from courses.forms import CourseForm, JoinByCodeTeacherForm, TutoringScheduleForm
from .models import PromptConfig
from .forms import PromptForm, TutoringSlotForm 


class TeachersOnlyMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.role == 'Teacher'

class TeacherDashboardView(LoginRequiredMixin, TeachersOnlyMixin, ListView):
    template_name = 'dashboard.html' 
    context_object_name = 'courses'

    def get_queryset(self):
        return (Course.objects
                .select_related('owner')
                .filter(teachers__teacher=self.request.user)
                .annotate(students_count=Count('enrollments'))
                .distinct())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        my_courses = context['courses']
        context['other_courses'] = (Course.objects
                                    .exclude(id__in=my_courses.values_list('id', flat=True))
                                    .annotate(students_count=Count('enrollments')))
        context['active_courses'] = my_courses.count()
        context['total_students'] = my_courses.aggregate(total=Sum('students_count'))['total'] or 0
        context['avg_attendance'] = None
        context['join_code_form'] = JoinByCodeTeacherForm()
        context['active_page'] = 'dashboard'
        return context

class CourseCreateView(LoginRequiredMixin, TeachersOnlyMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = 'course_form.html'   
    success_url = reverse_lazy('teachers:dashboard')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        response = super().form_valid(form)
        TeacherCourse.objects.get_or_create(teacher=self.request.user, course=self.object)
        return response

class JoinByCodeTeacherView(LoginRequiredMixin, TeachersOnlyMixin, FormView):
    form_class = JoinByCodeTeacherForm
    template_name = 'dashboard.html'   
    success_url = reverse_lazy('teachers:dashboard')

    def form_valid(self, form):
        code = form.cleaned_data['code'].strip().upper()
        course = Course.objects.filter(code=code).first()
        if course:
            _, created = TeacherCourse.objects.get_or_create(teacher=self.request.user, course=course)
            if created:
                messages.success(self.request, f"Te has unido exitosamente al curso '{course.name}'.")
            else:
                messages.info(self.request, f"Ya eras parte del curso '{course.name}'.")
        else:
            messages.error(self.request, f"El código '{code}' no corresponde a ningún curso existente.")
        return super().form_valid(form)

class JoinCourseTeacherView(LoginRequiredMixin, TeachersOnlyMixin, RedirectView):
    pattern_name = 'teachers:dashboard'
    def get_redirect_url(self, *args, **kwargs):
        course = Course.objects.get(pk=kwargs['pk'])
        TeacherCourse.objects.get_or_create(teacher=self.request.user, course=course)
        return reverse_lazy('teachers:dashboard')

class LeaveCourseTeacherView(LoginRequiredMixin, TeachersOnlyMixin, RedirectView):
    pattern_name = 'teachers:dashboard'

    def get_redirect_url(self, *args, **kwargs):
        tc = get_object_or_404(TeacherCourse,
                               teacher=self.request.user,
                               course_id=kwargs['pk'])
        try:
            from courses.models import TutoringSlot
            TutoringSlot.objects.filter(teacher_course=tc).delete()
        except Exception:
            with connection.cursor() as cur:
                cur.execute("DELETE FROM courses_tutoringslot WHERE teacher_course_id = %s", [tc.id])

        with transaction.atomic():
            tc.delete()

        messages.success(self.request, "Has salido del curso.")
        return reverse_lazy('teachers:dashboard')

class PromptEditView(LoginRequiredMixin, TeachersOnlyMixin, UpdateView):
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

class TutoringScheduleListView(LoginRequiredMixin, TeachersOnlyMixin, ListView):
    template_name = 'tutoring_schedule_list.html'
    context_object_name = 'courses'

    def get_queryset(self):
        # Obtenemos los cursos del profesor, y con prefetch_related, traemos
        # el horario de monitorías si existe en una sola consulta adicional.
        return (Course.objects
                .filter(teachers__teacher=self.request.user)
                .prefetch_related('tutoring_schedule')
                .distinct())

class TutoringScheduleUploadView(LoginRequiredMixin, TeachersOnlyMixin, UpdateView):
    model = TutoringSchedule
    form_class = TutoringScheduleForm
    template_name = 'tutoring_schedule_form.html'
    
    def get_success_url(self):
        return reverse('teachers:tutoring_schedules')

    def get_object(self, queryset=None):
        # Obtenemos el curso desde la URL
        self.course = get_object_or_404(Course, pk=self.kwargs['course_pk'])
        
        # Intentamos obtener el horario existente. Si no existe, lo creamos.
        # Esto nos permite usar UpdateView tanto para crear como para actualizar.
        schedule, created = TutoringSchedule.objects.get_or_create(course=self.course)
        return schedule

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.course
        return context

    def form_valid(self, form):
        # Obtenemos la instancia del modelo sin guardarla en la BBDD todavía
        schedule = form.save(commit=False)
        schedule.updated_by = self.request.user

        # --- INICIO DEL BLOQUE DE DEPURACIÓN DEFINITIVO ---
        # Accedemos al campo de archivo de nuestra instancia
        file_field = schedule.file
        # Y le preguntamos qué sistema de almacenamiento está gestionándolo
        storage_in_use = file_field.storage

        print("========================================================")
        print("!!! DIAGNÓSTICO DEL SISTEMA DE ALMACENAMIENTO !!!")
        print(f"!!! La clase de storage en uso es: {storage_in_use.__class__.__name__}")
        print(f"!!! Objeto de storage: {storage_in_use}")
        print("========================================================")
        # --- FIN DEL BLOQUE DE DEPURACIÓN ---

        # Ahora sí, intentamos guardar.
        schedule.save()
        
        messages.success(self.request, f"Horario de monitorías para el curso '{self.course.name}' actualizado correctamente.")
        return super().form_valid(form)

@login_required
@user_passes_test(lambda u: u.role == 'Teacher')
def manage_tutoring_slots(request, course_pk):
    teacher_course = get_object_or_404(
        TeacherCourse,
        course_id=course_pk,
        teacher=request.user
    )

    TutoringSlotFormSet = inlineformset_factory(
        TeacherCourse,
        TutoringSlot,
        form=TutoringSlotForm,
        extra=1,  # Muestra 1 formulario vacío extra para añadir nuevas filas
        can_delete=True # Permite eliminar filas existentes
    )

    if request.method == 'POST':

        formset = TutoringSlotFormSet(request.POST, instance=teacher_course)
        if formset.is_valid():
            formset.save()
            messages.success(request, "Horarios de monitoría actualizados exitosamente.")
            return redirect('teachers:dashboard')
    else:
        formset = TutoringSlotFormSet(instance=teacher_course)

    context = {
        'formset': formset,
        'course': teacher_course.course
    }
    return render(request, 'manage_tutoring.html', context)
    
class CourseDeleteView(LoginRequiredMixin, TeachersOnlyMixin, RedirectView):
    pattern_name = 'teachers:dashboard'

    def get_redirect_url(self, *args, **kwargs):
        course = get_object_or_404(Course, pk=kwargs['pk'], owner=self.request.user)
        from courses.models import TeacherCourse, Enrollment
        TeacherCourse.objects.filter(course=course).delete()
        Enrollment.objects.filter(course=course).delete()
        with connection.cursor() as cur:
            cur.execute("DELETE FROM courses_tutoringslot WHERE teacher_course_id IN (SELECT id FROM courses_profesor_materia WHERE materia_id=%s)", [course.id])
        course.delete()
        messages.success(self.request, "Curso eliminado.")
        return reverse_lazy('teachers:dashboard')
