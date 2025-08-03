from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, RedirectView

from .models import Course, TeacherCourse, Enrollment
from .forms import CourseForm

class TeachersOnlyMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.role == 'Teacher'

class StudentsOnlyMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.role == 'Student'


class CourseCreateView(LoginRequiredMixin, TeachersOnlyMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = 'course_form.html'
    success_url = reverse_lazy('courses:my_courses')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        response = super().form_valid(form)
        TeacherCourse.objects.get_or_create(
            teacher=self.request.user,
            course=self.object
        )
        return response


class MyCoursesView(LoginRequiredMixin, TeachersOnlyMixin, ListView):
    template_name = 'my_courses.html'
    context_object_name = 'courses'

    def get_queryset(self):
        return Course.objects.filter(teachers__teacher=self.request.user).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        enrolled_ids = self.get_queryset().values_list('id', flat=True)
        context['other_courses'] = Course.objects.exclude(id__in=enrolled_ids)
        return context


class JoinCourseTeacherView(LoginRequiredMixin, TeachersOnlyMixin, RedirectView):
    pattern_name = 'courses:my_courses'

    def get_redirect_url(self, *args, **kwargs):
        course = Course.objects.get(pk=kwargs['pk'])
        TeacherCourse.objects.get_or_create(teacher=self.request.user, course=course)
        return reverse_lazy('courses:my_courses') 


class LeaveCourseTeacherView(LoginRequiredMixin, TeachersOnlyMixin, RedirectView):
    pattern_name = 'courses:my_courses'

    def get_redirect_url(self, *args, **kwargs):
        TeacherCourse.objects.filter(
            teacher=self.request.user, course_id=kwargs['pk']
        ).delete()
        return reverse_lazy('courses:my_courses')   


class MyStudentCoursesView(LoginRequiredMixin, StudentsOnlyMixin, ListView):
    template_name = 'my_student_courses.html'
    context_object_name = 'courses'

    def get_queryset(self):
        # Materias en las que el estudiante YA está inscrito
        return Course.objects.filter(
            enrollments__student=self.request.user
        ).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        enrolled_ids = context['courses'].values_list('id', flat=True)
        # Materias disponibles para unirse
        context['other_courses'] = Course.objects.exclude(id__in=enrolled_ids)
        return context



class JoinCourseStudentView(LoginRequiredMixin, StudentsOnlyMixin, RedirectView):
    pattern_name = 'courses:my_student_courses'

    def get_redirect_url(self, *args, **kwargs):
        course = Course.objects.get(pk=kwargs['pk'])
        Enrollment.objects.get_or_create(student=self.request.user, course=course)
        return reverse_lazy('courses:my_student_courses')


class LeaveCourseStudentView(LoginRequiredMixin, StudentsOnlyMixin, RedirectView):
    pattern_name = 'courses:my_student_courses'

    def get_redirect_url(self, *args, **kwargs):
        Enrollment.objects.filter(
            student=self.request.user, course_id=kwargs['pk']
        ).delete()
        return reverse_lazy('courses:my_student_courses')