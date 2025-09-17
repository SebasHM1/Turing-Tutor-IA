# courses/urls.py
from django.urls import path
from .views import (
    MyStudentCoursesView, JoinCourseStudentView, LeaveCourseStudentView, CourseDetailView, CoursePromptEditView, KnowledgeBaseView
)


app_name = 'courses'

urlpatterns = [
    path('student/my/',                 MyStudentCoursesView.as_view(),  name='my_student_courses'),
    path('<int:pk>/student/join/',     JoinCourseStudentView.as_view(),  name='student_join'),
    path('<int:pk>/student/leave/',    LeaveCourseStudentView.as_view(), name='student_leave'),
    path('<int:pk>/',                  CourseDetailView.as_view(),       name='detail'),
    path('<int:pk>/prompt/',           CoursePromptEditView.as_view(),   name='prompt_edit'),
    path('<int:pk>/knowledge/', KnowledgeBaseView.as_view(), name='knowledge_base'),
]
