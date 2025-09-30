# courses/views.py
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, RedirectView, DetailView, UpdateView, FormView
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from .models import Course, Enrollment, CoursePrompt, KnowledgeBaseFile, TeacherCourse
from .forms import CoursePromptForm, KnowledgeBaseFileForm
from .rag_utils import rag_processor

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.get_object()
        
        teacher_assignments = (TeacherCourse.objects
                                  .filter(course=course)
                                  .select_related('teacher')
                                  .prefetch_related('tutoring_slots'))
        
        context['teacher_assignments'] = teacher_assignments
        return context 



class CourseDetailView(LoginRequiredMixin, DetailView):
    model = Course
    template_name = 'course_detail.html'
    context_object_name = 'course'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_page'] = 'course_detail'
        
        # Verificar si el usuario es profesor del curso
        if self.request.user.role == 'Teacher':
            try:
                TeacherCourse.objects.get(
                    course=self.object,
                    teacher=self.request.user
                )
                context['is_teacher'] = True
            except TeacherCourse.DoesNotExist:
                context['is_teacher'] = False
        else:
            context['is_teacher'] = False
            
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


class KnowledgeBaseView(LoginRequiredMixin, TeachersOnlyMixin, FormView):
    template_name = 'knowledge_base.html'
    form_class = KnowledgeBaseFileForm

    def post(self, request, *args, **kwargs):
        print(f"DEBUG: POST method called for course {self.kwargs['pk']}")
        print(f"DEBUG: Request FILES: {request.FILES}")
        print(f"DEBUG: Request POST data: {request.POST}")
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        print(f"DEBUG: form_valid called - Form is valid!")
        course = Course.objects.get(pk=self.kwargs['pk'])
        file_obj = form.save(commit=False)
        file_obj.course = course
        print(f"DEBUG: Saving file - Course: {course.id}, File: {file_obj.file.name if file_obj.file else 'NO FILE'}")
        
        # Asignar nombre si no se proporcionó
        if not file_obj.name and file_obj.file:
            file_obj.name = file_obj.file.name
        
        try:
            # Guardar primero el archivo sin procesar
            file_obj.save()
            print(f"DEBUG: File saved successfully with ID: {file_obj.id}")
            
            # Verificar que se guardó consultando la base de datos
            saved_file = KnowledgeBaseFile.objects.get(id=file_obj.id)
            print(f"DEBUG: Verification - File exists in DB: ID={saved_file.id}, Course={saved_file.course_id}")
            
        except Exception as e:
            print(f"DEBUG: Error saving file: {str(e)}")
            messages.error(self.request, f"Error al guardar el archivo: {str(e)}")
            return self.form_invalid(form)
        
        # REACTIVAMOS EL PROCESAMIENTO RAG
        try:
            print(f"DEBUG: Starting RAG processing for file ID: {file_obj.id}")
            result = rag_processor.process_pdf_file(file_obj)
            if result['success']:
                print(f"DEBUG: RAG processing successful: {result['chunks_count']} chunks")
                messages.success(
                    self.request, 
                    f"PDF subido y procesado exitosamente. {result['chunks_count']} fragmentos de texto creados."
                )
            else:
                print(f"DEBUG: RAG processing failed: {result['error']}")
                messages.warning(
                    self.request,
                    f"PDF subido pero hubo un error al procesarlo: {result['error']}"
                )
        except Exception as e:
            print(f"DEBUG: Exception during RAG processing: {str(e)}")
            # Asegurémonos de que el archivo se marque como no procesado
            file_obj.processing_error = str(e)
            file_obj.processed = False
            file_obj.save()
            messages.warning(
                self.request,
                f"PDF subido correctamente, pero hubo un error al procesarlo: {str(e)}"
            )
        
        return super().form_valid(form)

    def form_invalid(self, form):
        print(f"DEBUG: form_invalid called - Form has errors!")
        print(f"DEBUG: Form errors: {form.errors}")
        print(f"DEBUG: Form non_field_errors: {form.non_field_errors()}")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = Course.objects.get(pk=self.kwargs['pk'])
        files = KnowledgeBaseFile.objects.filter(course_id=self.kwargs['pk'])
        print(f"DEBUG: Course ID: {self.kwargs['pk']}")
        print(f"DEBUG: Files found: {files.count()}")
        for f in files:
            print(f"DEBUG: File - ID: {f.id}, Name: {f.name}, Course: {f.course_id}")
        context['files'] = files
        context['active_page'] = 'knowledge_base'
        return context

    def form_valid(self, form):
        course = Course.objects.get(pk=self.kwargs['pk'])
        file_obj = form.save(commit=False)
        file_obj.course = course
        print(f"DEBUG: Saving file - Course: {course.id}, File: {file_obj.file.name}")
        
        # Guardar primero el archivo sin procesar
        file_obj.save()
        print(f"DEBUG: File saved with ID: {file_obj.id}")
        
        # Luego intentar procesarlo para RAG (esto no debería afectar el guardado)
        try:
            print(f"DEBUG: Starting RAG processing for file ID: {file_obj.id}")
            result = rag_processor.process_pdf_file(file_obj)
            if result['success']:
                print(f"DEBUG: RAG processing successful: {result['chunks_count']} chunks")
                messages.success(
                    self.request, 
                    f"PDF subido y procesado exitosamente. {result['chunks_count']} fragmentos de texto creados."
                )
            else:
                print(f"DEBUG: RAG processing failed: {result['error']}")
                messages.warning(
                    self.request,
                    f"PDF subido pero hubo un error al procesarlo: {result['error']}"
                )
        except Exception as e:
            print(f"DEBUG: Exception during RAG processing: {str(e)}")
            # Asegurémonos de que el archivo se marque como no procesado
            file_obj.processing_error = str(e)
            file_obj.processed = False
            file_obj.save()
            messages.warning(
                self.request,
                f"PDF subido correctamente, pero hubo un error al procesarlo: {str(e)}"
            )
        
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('courses:knowledge_base', kwargs={'pk': self.kwargs['pk']})


class KnowledgeBaseDeleteView(LoginRequiredMixin, TeachersOnlyMixin, RedirectView):
    """Delete a knowledge base file."""
    
    def get_redirect_url(self, *args, **kwargs):
        return reverse_lazy('courses:knowledge_base', kwargs={'pk': kwargs['course_pk']})
    
    def post(self, request, *args, **kwargs):
        course_pk = kwargs['course_pk']
        file_pk = kwargs['file_pk']
        
        try:
            file_obj = get_object_or_404(
                KnowledgeBaseFile, 
                pk=file_pk, 
                course_id=course_pk
            )
            file_obj.delete()
            messages.success(request, "Archivo eliminado exitosamente.")
        except Exception as e:
            messages.error(request, f"Error al eliminar el archivo: {str(e)}")
        
        return super().post(request, *args, **kwargs)


class KnowledgeBaseReprocessView(LoginRequiredMixin, TeachersOnlyMixin, RedirectView):
    """Reprocess a knowledge base file for RAG."""
    
    def get_redirect_url(self, *args, **kwargs):
        return reverse_lazy('courses:knowledge_base', kwargs={'pk': kwargs['course_pk']})
    
    def post(self, request, *args, **kwargs):
        course_pk = kwargs['course_pk']
        file_pk = kwargs['file_pk']
        
        try:
            file_obj = get_object_or_404(
                KnowledgeBaseFile, 
                pk=file_pk, 
                course_id=course_pk
            )
            
            result = rag_processor.process_pdf_file(file_obj)
            if result['success']:
                messages.success(
                    request, 
                    f"Archivo reprocesado exitosamente. {result['chunks_count']} fragmentos de texto creados."
                )
            else:
                messages.error(request, f"Error al reprocesar el archivo: {result['error']}")
                
        except Exception as e:
            messages.error(request, f"Error al reprocesar el archivo: {str(e)}")
        
        return super().post(request, *args, **kwargs)