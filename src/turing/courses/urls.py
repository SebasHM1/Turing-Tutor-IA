# courses/urls.py
from django.urls import path
from .views import (
    MyStudentCoursesView, JoinCourseStudentView, LeaveCourseStudentView
)

app_name = 'courses'

urlpatterns = [
    path('student/my/', MyStudentCoursesView.as_view(),  name='my_student_courses'),
    path('my/',         MyStudentCoursesView.as_view(),  name='my_courses'),
    path('<int:pk>/student/join/',  JoinCourseStudentView.as_view(),  name='student_join'),
    path('<int:pk>/student/leave/', LeaveCourseStudentView.as_view(), name='student_leave'),
]

