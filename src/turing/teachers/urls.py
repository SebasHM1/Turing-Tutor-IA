# teachers/urls.py
from django.urls import path
from .views import (
    CourseDeleteView, TeacherDashboardView, CourseCreateView,
    JoinCourseTeacherView, LeaveCourseTeacherView, JoinByCodeTeacherView, PromptEditView
)

app_name = 'teachers'

urlpatterns = [
    path('dashboard/',                TeacherDashboardView.as_view(), name='dashboard'),
    path('courses/new/',              CourseCreateView.as_view(),     name='create'),
    path('courses/<int:pk>/join/',    JoinCourseTeacherView.as_view(),  name='join'),
    path('courses/<int:pk>/leave/',   LeaveCourseTeacherView.as_view(), name='leave'),
    path('courses/join-by-code/',     JoinByCodeTeacherView.as_view(),  name='join_by_code'),
    path('prompt/',                   PromptEditView.as_view(),         name='prompt_edit'),
    path('courses/<int:pk>/delete/', CourseDeleteView.as_view(), name='delete'),
]
