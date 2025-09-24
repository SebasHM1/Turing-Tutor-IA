# courses/urls.py
from django.urls import path
from .views import (
    MyStudentCoursesView, JoinCourseStudentView, LeaveCourseStudentView, StudentCourseDetailView
)
from .views_proxy import tutoring_schedule_proxy
app_name = 'courses'

urlpatterns = [
    path('student/my/', MyStudentCoursesView.as_view(),  name='my_student_courses'),
    path('my/',         MyStudentCoursesView.as_view(),  name='my_courses'),
    path('<int:pk>/student/join/',  JoinCourseStudentView.as_view(),  name='student_join'),
    path('<int:pk>/student/leave/', LeaveCourseStudentView.as_view(), name='student_leave'),
    path('course/<int:pk>/', StudentCourseDetailView.as_view(), name='student_course_detail'),
    path( "courses/<int:pk>/tutoring_schedule_proxy/", tutoring_schedule_proxy, name="tutoring_schedule_proxy",
    ),
]

