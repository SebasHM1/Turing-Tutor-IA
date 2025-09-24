# courses/views.py
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, RedirectView, DetailView
from django.shortcuts import get_object_or_404
from .models import Course, Enrollment, TeacherCourse, TutoringSlot

class StudentsOnlyMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.role == 'Student'

class MyStudentCoursesView(LoginRequiredMixin, StudentsOnlyMixin, ListView):
    template_name = 'my_student_courses.html'
    context_object_name = 'courses'

    def get_queryset(self):
        return Course.objects.filter(enrollments__student=self.request.user).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        enrolled_ids = context['courses'].values_list('id', flat=True)
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
        Enrollment.objects.filter(student=self.request.user, course_id=kwargs['pk']).delete()
        return reverse_lazy('courses:my_student_courses')

class StudentCourseDetailView(LoginRequiredMixin, StudentsOnlyMixin, DetailView):
    model = Course
    template_name = 'student_course_detail.html'
    context_object_name = 'course' 
