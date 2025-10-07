# teachers/urls.py
from django.urls import path
from .views import (
    # Vistas principales y de gestión de cursos
    TeacherDashboardView,
    CourseCreateView,
    CourseDeleteView,
    ManageCourseView,
    
    # Vistas para la gestión de grupos y estudiantes
    GroupCreateView,
    manage_group_enrollments,

    # Vistas para la gestión de monitorías (actualizadas)
    TutoringScheduleListView,
    TutoringScheduleUploadView,
    manage_tutoring_slots,
    GroupPromptEditView,
)

app_name = 'teachers'

urlpatterns = [
    path('dashboard/', TeacherDashboardView.as_view(), name='dashboard'),
    path('courses/new/', CourseCreateView.as_view(), name='course_create'),
    path('courses/<int:pk>/delete/', CourseDeleteView.as_view(), name='course_delete'),
    path('courses/<int:course_pk>/groups/new/', GroupCreateView.as_view(), name='group_create'),
    path('groups/<int:group_pk>/students/', manage_group_enrollments, name='manage_enrollments'),
    path('groups/<int:group_pk>/prompt/', GroupPromptEditView.as_view(), name='group_prompt_edit'),
    path('tutoring-schedules/', TutoringScheduleListView.as_view(), name='tutoring_schedules'),
    path('courses/<int:course_pk>/upload-schedule/', TutoringScheduleUploadView.as_view(), name='upload_schedule'),
    path('groups/<int:group_pk>/manage-tutoring/', manage_tutoring_slots, name='manage_tutoring'),
]