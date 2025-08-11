# courses/views.py
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.views.generic import CreateView, ListView, RedirectView, FormView
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404
from django import forms

from .models import Course, TeacherCourse, Enrollment
from .forms import CourseForm, JoinByCodeTeacherForm

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
        context['avg_attendance'] = None  # cuando tengamos asistencias calculamos aquí
        context['join_code_form'] = JoinByCodeTeacherForm()
        context['profile_url'] = reverse('courses:my_courses')
        return context

class JoinByCodeTeacherView(LoginRequiredMixin, TeachersOnlyMixin, FormView):
    form_class = JoinByCodeTeacherForm
    template_name = 'my_courses.html'
    success_url = reverse_lazy('courses:my_courses')

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
            # Dar feedback si el código es inválido
            messages.error(self.request, f"El código '{code}' no corresponde a ningún curso existente.")
        
        return super().form_valid(form)

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
        course = get_object_or_404(Course, pk=kwargs['pk']) 
        Enrollment.objects.get_or_create(student=self.request.user, course=course)
        return reverse_lazy('courses:my_student_courses')


class LeaveCourseStudentView(LoginRequiredMixin, StudentsOnlyMixin, RedirectView):
    pattern_name = 'courses:my_student_courses'

    def get_redirect_url(self, *args, **kwargs):
        Enrollment.objects.filter(
            student=self.request.user, course_id=kwargs['pk']
        ).delete()
        return reverse_lazy('courses:my_student_courses')