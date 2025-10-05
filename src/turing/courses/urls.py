# courses/urls.py
from django.urls import path
from .views import (
    MyStudentGroupsView,
    StudentGroupDetailView,

    CoursePromptEditView,
    KnowledgeBaseView,
    KnowledgeBaseDeleteView,
    KnowledgeBaseReprocessView,
)

from .views_proxy import tutoring_schedule_proxy

app_name = 'courses'

urlpatterns = [

    path('my-groups/', MyStudentGroupsView.as_view(), name='my_student_groups'),

    path('group/<int:pk>/', StudentGroupDetailView.as_view(), name='student_group_detail'),

    path('course/<int:pk>/prompt/', CoursePromptEditView.as_view(), name='prompt_edit'),

    path('course/<int:pk>/knowledge/', KnowledgeBaseView.as_view(), name='knowledge_base'),
    
    path('course/<int:course_pk>/knowledge/<int:file_pk>/delete/', 
         KnowledgeBaseDeleteView.as_view(), name='knowledge_base_delete'),

    path('course/<int:course_pk>/knowledge/<int:file_pk>/reprocess/', 
         KnowledgeBaseReprocessView.as_view(), name='knowledge_base_reprocess'),

    path("course/<int:pk>/tutoring-schedule-proxy/", 
         tutoring_schedule_proxy, name="tutoring_schedule_proxy"),
]