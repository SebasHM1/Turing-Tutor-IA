# courses/views.py
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, RedirectView, DetailView, UpdateView
from django.shortcuts import get_object_or_404
from .models import Course, Enrollment, CoursePrompt
from .forms import CoursePromptForm


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



class CourseDetailView(DetailView):
    model = Course
    template_name = 'course_detail.html'
    context_object_name = 'course'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_page'] = 'course_detail'
        return context


class TeachersOnlyMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.role == 'Teacher'

class CoursePromptEditView(LoginRequiredMixin, TeachersOnlyMixin, UpdateView):
    model = CoursePrompt
    form_class = CoursePromptForm
    template_name = 'course_prompt_edit.html'

    def get_object(self, queryset=None):
        course_id = self.kwargs['pk']
        course = Course.objects.get(pk=course_id)
        obj, _ = CoursePrompt.objects.get_or_create(course=course)
        return obj

    def get_success_url(self):
        return reverse_lazy('courses:prompt_edit', kwargs={'pk': self.object.course.pk})

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.updated_by = self.request.user
        obj.save()
        return super().form_valid(form)
