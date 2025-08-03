# courses/urls.py
from django.urls import path
from .views import (
    CourseCreateView, MyCoursesView,
    JoinCourseTeacherView, LeaveCourseTeacherView,
    MyStudentCoursesView, JoinCourseStudentView, LeaveCourseStudentView
)

app_name = 'courses'

urlpatterns = [
    # Profesores
    path('new/',    CourseCreateView.as_view(),        name='create'),
    path('my/',     MyCoursesView.as_view(),           name='my_courses'),
    path('<int:pk>/join/',  JoinCourseTeacherView.as_view(),  name='join'),
    path('<int:pk>/leave/', LeaveCourseTeacherView.as_view(), name='leave'),

    # Estudiantes
    path('student/my/',         MyStudentCoursesView.as_view(),   name='my_student_courses'),
    path('<int:pk>/student/join/',  JoinCourseStudentView.as_view(),  name='student_join'),
    path('<int:pk>/student/leave/', LeaveCourseStudentView.as_view(), name='student_leave'),
]
