from django.db.models import Count, Q
from datetime import date
from chatbot.models import TopicWeight
from .models import Enrollment, Group
from chatbot.models import TopicWeight

class TopicStatisticsService:
    
    def get_student_topic_percentages(self, student_id, course_id, start_date=None, end_date=None):
        """Porcentajes por estudiante - base para todo"""
        
        filters = Q(student_id=student_id, course_id=course_id)
        
        if start_date:
            filters &= Q(date__gte=start_date)
        if end_date:
            filters &= Q(date__lte=end_date)
        
        # Contar mensajes por tema
        topic_counts = TopicWeight.objects.filter(filters).values(
            'topic__name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Calcular total y porcentajes
        total = sum(t['count'] for t in topic_counts)
        
        if total == 0:
            return []
        
        return [{
            'topic': t['topic__name'],
            'count': t['count'],
            'percentage': (t['count'] / total) * 100
        } for t in topic_counts]
    
    def get_group_topic_percentages(self, group_id, start_date=None, end_date=None):
        
        # Obtener estudiantes del grupo
        enrollments = Enrollment.objects.filter(group_id=group_id).values_list('student_id', flat=True)
        
        if not enrollments:
            return []
        
        # Obtener curso del grupo
        group = Group.objects.select_related('course').get(id=group_id)
        course_id = group.course.id
        
        # Acumular porcentajes ponderados por estudiante
        topic_totals = {}
        total_weight = 0
        
        for student_id in enrollments:
            student_percentages = self.get_student_topic_percentages(
                student_id, course_id, start_date, end_date
            )
            
            if student_percentages:  # Solo si el estudiante tiene actividad
                student_weight = 10  # Peso fijo por estudiante
                total_weight += student_weight
                
                for topic_data in student_percentages:
                    topic = topic_data['topic']
                    # Aplicar el porcentaje del estudiante al peso fijo
                    weighted_value = (topic_data['percentage'] / 100) * student_weight
                    
                    if topic not in topic_totals:
                        topic_totals[topic] = 0
                    topic_totals[topic] += weighted_value
        
        if total_weight == 0:
            return []
        
        # Calcular porcentajes finales del grupo
        return [{
            'topic': topic,
            'weighted_total': weight,
            'percentage': (weight / total_weight) * 100
        } for topic, weight in sorted(topic_totals.items(), key=lambda x: x[1], reverse=True)]
    
    def get_course_topic_percentages(self, course_id, start_date=None, end_date=None):
        
        # Obtener todos los estudiantes matriculados en el curso
        enrollments = Enrollment.objects.filter(
            Q(group__course_id=course_id) | Q(legacy_course_id=course_id)
        ).values_list('student_id', flat=True).distinct()
        
        if not enrollments:
            return []
        
        # Acumular porcentajes ponderados por estudiante
        topic_totals = {}
        total_weight = 0
        
        for student_id in enrollments:
            student_percentages = self.get_student_topic_percentages(
                student_id, course_id, start_date, end_date
            )
            
            if student_percentages:  # Solo si el estudiante tiene actividad
                student_weight = 10  # Peso fijo por estudiante
                total_weight += student_weight
                
                for topic_data in student_percentages:
                    topic = topic_data['topic']
                    # Aplicar el porcentaje del estudiante al peso fijo
                    weighted_value = (topic_data['percentage'] / 100) * student_weight
                    
                    if topic not in topic_totals:
                        topic_totals[topic] = 0
                    topic_totals[topic] += weighted_value
        
        if total_weight == 0:
            return []
        
        # Calcular porcentajes finales del curso
        return [{
            'topic': topic,
            'weighted_total': weight,
            'percentage': (weight / total_weight) * 100
        } for topic, weight in sorted(topic_totals.items(), key=lambda x: x[1], reverse=True)]
    
    def get_activity_summary(self, course_id, start_date=None, end_date=None):
        
        filters = Q(course_id=course_id)
        if start_date:
            filters &= Q(date__gte=start_date)
        if end_date:
            filters &= Q(date__lte=end_date)
            
        stats = TopicWeight.objects.filter(filters).values('date').annotate(
            total_messages=Count('id'),
            unique_students=Count('student', distinct=True),
            unique_topics=Count('topic', distinct=True)
        ).order_by('date')
        
        return list(stats)
    
    def get_top_topics_by_date_range(self, course_id, start_date, end_date):
        
        filters = Q(course_id=course_id, date__range=[start_date, end_date])
        
        topic_stats = TopicWeight.objects.filter(filters).values(
            'topic__name'
        ).annotate(
            total_count=Count('id'),
            unique_students=Count('student', distinct=True)
        ).order_by('-total_count')
        
        return list(topic_stats)

# Instancia global
stats_service = TopicStatisticsService()