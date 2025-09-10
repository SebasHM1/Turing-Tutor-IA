from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Sum
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, ListView, RedirectView, FormView, UpdateView
from courses.models import Course, TeacherCourse
from courses.forms import CourseForm, JoinByCodeTeacherForm
from .models import PromptConfig
from .forms import PromptForm


class TeachersOnlyMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.role == 'Teacher'

class TeacherDashboardView(LoginRequiredMixin, TeachersOnlyMixin, ListView):
    template_name = 'dashboard.html'   # <-- aquí el cambio
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
    template_name = 'course_form.html'   # reutilizamos tu template existente
    success_url = reverse_lazy('teachers:dashboard')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        response = super().form_valid(form)
        TeacherCourse.objects.get_or_create(teacher=self.request.user, course=self.object)
        return response

class JoinByCodeTeacherView(LoginRequiredMixin, TeachersOnlyMixin, FormView):
    form_class = JoinByCodeTeacherForm
    template_name = 'dashboard.html'   # mismo dashboard tras enviar el código
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
        TeacherCourse.objects.filter(teacher=self.request.user, course_id=kwargs['pk']).delete()
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