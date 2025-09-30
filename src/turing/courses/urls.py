# courses/urls.py
from django.urls import path
from .views import (
    MyStudentCoursesView, JoinCourseStudentView, LeaveCourseStudentView, 
    CourseDetailView, CoursePromptEditView, KnowledgeBaseView,
    KnowledgeBaseDeleteView, KnowledgeBaseReprocessView, StudentCourseDetailView
)

from .views_proxy import tutoring_schedule_proxy
app_name = 'courses'

urlpatterns = [
    path('student/my/',                 MyStudentCoursesView.as_view(),  name='my_student_courses'),
    path('<int:pk>/student/join/',     JoinCourseStudentView.as_view(),  name='student_join'),
    path('<int:pk>/student/leave/',    LeaveCourseStudentView.as_view(), name='student_leave'),
    path('<int:pk>/',                  CourseDetailView.as_view(),       name='detail'),
    path('<int:pk>/prompt/',           CoursePromptEditView.as_view(),   name='prompt_edit'),
    path('<int:pk>/knowledge/', KnowledgeBaseView.as_view(), name='knowledge_base'),
    path('<int:course_pk>/knowledge/<int:file_pk>/delete/', KnowledgeBaseDeleteView.as_view(), name='knowledge_base_delete'),
    path('<int:course_pk>/knowledge/<int:file_pk>/reprocess/', KnowledgeBaseReprocessView.as_view(), name='knowledge_base_reprocess'),
    path('my/',         MyStudentCoursesView.as_view(),  name='my_courses'),
    path('course/<int:pk>/', StudentCourseDetailView.as_view(), name='student_course_detail'),
    path( "courses/<int:pk>/tutoring_schedule_proxy/", tutoring_schedule_proxy, name="tutoring_schedule_proxy"),
]

