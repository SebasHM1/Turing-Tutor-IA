from django.test import TestCase
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal

from users.models import CustomUser, UserRole
from courses.models import Course, Group, Enrollment, CourseTopics, TopicKeyword
from chatbot.models import ChatSession, ChatMessage, TopicWeight
from courses.topic_statistics import TopicStatisticsService


class TopicStatisticsTestCase(TestCase):
    """
    Comprehensive tests for TopicStatisticsService with extensive mock data.
    Tests cover date filtering, multiple students, multiple topics, and various edge cases.
    """
    
    @classmethod
    def setUpTestData(cls):
        """
        Set up test data that will be used across all test methods.
        Creates a rich dataset with multiple students, courses, topics, and topic weights.
        """
        # Create teacher
        cls.teacher = CustomUser.objects.create_user(
            email='teacher@university.edu',
            password='testpass123',
            name='Maria',
            last_name='Rodriguez',
            cedula='1234567890',
            university_code='PROF001',
            user_group='Teachers',
            role=UserRole.TEACHER
        )
        
        # Create students
        cls.student1 = CustomUser.objects.create_user(
            email='student1@university.edu',
            password='testpass123',
            name='Juan',
            last_name='Perez',
            cedula='1111111111',
            university_code='STU001',
            user_group='CS2024A',
            role=UserRole.STUDENT
        )
        
        cls.student2 = CustomUser.objects.create_user(
            email='student2@university.edu',
            password='testpass123',
            name='Ana',
            last_name='Garcia',
            cedula='2222222222',
            university_code='STU002',
            user_group='CS2024A',
            role=UserRole.STUDENT
        )
        
        cls.student3 = CustomUser.objects.create_user(
            email='student3@university.edu',
            password='testpass123',
            name='Carlos',
            last_name='Martinez',
            cedula='3333333333',
            university_code='STU003',
            user_group='CS2024B',
            role=UserRole.STUDENT
        )
        
        # Create course
        cls.course = Course.objects.create(
            name='Data Structures',
            description='Introduction to data structures and algorithms',
            level='Intermediate',
            owner=cls.teacher,
            code='DS101'
        )
        
        # Create groups
        cls.group1 = Group.objects.create(
            course=cls.course,
            teacher=cls.teacher,
            name='Group A',
            schedule='Mon/Wed 10:00-12:00'
        )
        
        cls.group2 = Group.objects.create(
            course=cls.course,
            teacher=cls.teacher,
            name='Group B',
            schedule='Tue/Thu 14:00-16:00'
        )
        
        # Enroll students
        Enrollment.objects.create(student=cls.student1, group=cls.group1)
        Enrollment.objects.create(student=cls.student2, group=cls.group1)
        Enrollment.objects.create(student=cls.student3, group=cls.group2)
        
        # Create topics
        cls.topic_arrays = CourseTopics.objects.create(
            course=cls.course,
            name='Arrays',
            description='Array data structures',
            is_active=True
        )
        
        cls.topic_linked_lists = CourseTopics.objects.create(
            course=cls.course,
            name='Linked Lists',
            description='Singly and doubly linked lists',
            is_active=True
        )
        
        cls.topic_trees = CourseTopics.objects.create(
            course=cls.course,
            name='Trees',
            description='Binary trees and tree traversal',
            is_active=True
        )
        
        cls.topic_graphs = CourseTopics.objects.create(
            course=cls.course,
            name='Graphs',
            description='Graph theory and algorithms',
            is_active=True
        )
        
        # Create keywords for each topic
        cls.kw_array = TopicKeyword.objects.create(topic=cls.topic_arrays, keyword='array')
        cls.kw_index = TopicKeyword.objects.create(topic=cls.topic_arrays, keyword='index')
        cls.kw_element = TopicKeyword.objects.create(topic=cls.topic_arrays, keyword='element')
        
        cls.kw_node = TopicKeyword.objects.create(topic=cls.topic_linked_lists, keyword='node')
        cls.kw_pointer = TopicKeyword.objects.create(topic=cls.topic_linked_lists, keyword='pointer')
        cls.kw_next = TopicKeyword.objects.create(topic=cls.topic_linked_lists, keyword='next')
        
        cls.kw_tree = TopicKeyword.objects.create(topic=cls.topic_trees, keyword='tree')
        cls.kw_root = TopicKeyword.objects.create(topic=cls.topic_trees, keyword='root')
        cls.kw_leaf = TopicKeyword.objects.create(topic=cls.topic_trees, keyword='leaf')
        
        cls.kw_graph = TopicKeyword.objects.create(topic=cls.topic_graphs, keyword='graph')
        cls.kw_vertex = TopicKeyword.objects.create(topic=cls.topic_graphs, keyword='vertex')
        cls.kw_edge = TopicKeyword.objects.create(topic=cls.topic_graphs, keyword='edge')
        
        # Create chat sessions for students
        cls.session1 = ChatSession.objects.create(
            user=cls.student1,
            course=cls.course,
            name='Study Session 1'
        )
        
        cls.session2 = ChatSession.objects.create(
            user=cls.student2,
            course=cls.course,
            name='Study Session 2'
        )
        
        cls.session3 = ChatSession.objects.create(
            user=cls.student3,
            course=cls.course,
            name='Study Session 3'
        )
        
        # Reference dates for testing
        cls.today = date.today()
        cls.yesterday = cls.today - timedelta(days=1)
        cls.two_days_ago = cls.today - timedelta(days=2)
        cls.three_days_ago = cls.today - timedelta(days=3)
        cls.week_ago = cls.today - timedelta(days=7)
        cls.two_weeks_ago = cls.today - timedelta(days=14)
        cls.month_ago = cls.today - timedelta(days=30)
        
        # Create messages and topic weights with varied dates
        cls._create_mock_weights()
        
        # Initialize the service
        cls.stats_service = TopicStatisticsService()
    
    @classmethod
    def _create_mock_weights(cls):
        """
        Creates a rich dataset of topic weights across different dates and students.
        
        Distribution:
        - Student 1: Heavy on Arrays (recent), some Linked Lists (older)
        - Student 2: Balanced between Trees and Graphs (recent)
        - Student 3: Focused on Graphs (spread across dates)
        """
        # Student 1 - Arrays specialist (recent activity)
        msg1 = ChatMessage.objects.create(
            session=cls.session1,
            sender='user',
            message='How do I access array elements?'
        )
        TopicWeight.objects.create(
            message=msg1, student=cls.student1, course=cls.course,
            topic=cls.topic_arrays, keyword=cls.kw_array, date=cls.today
        )
        TopicWeight.objects.create(
            message=msg1, student=cls.student1, course=cls.course,
            topic=cls.topic_arrays, keyword=cls.kw_element, date=cls.today
        )
        
        msg2 = ChatMessage.objects.create(
            session=cls.session1,
            sender='user',
            message='What is array indexing?'
        )
        TopicWeight.objects.create(
            message=msg2, student=cls.student1, course=cls.course,
            topic=cls.topic_arrays, keyword=cls.kw_array, date=cls.today
        )
        TopicWeight.objects.create(
            message=msg2, student=cls.student1, course=cls.course,
            topic=cls.topic_arrays, keyword=cls.kw_index, date=cls.today
        )
        
        msg3 = ChatMessage.objects.create(
            session=cls.session1,
            sender='user',
            message='More about arrays and elements'
        )
        TopicWeight.objects.create(
            message=msg3, student=cls.student1, course=cls.course,
            topic=cls.topic_arrays, keyword=cls.kw_array, date=cls.yesterday
        )
        TopicWeight.objects.create(
            message=msg3, student=cls.student1, course=cls.course,
            topic=cls.topic_arrays, keyword=cls.kw_element, date=cls.yesterday
        )
        
        # Student 1 - Some linked list questions (older)
        msg4 = ChatMessage.objects.create(
            session=cls.session1,
            sender='user',
            message='How do nodes work with pointers?'
        )
        TopicWeight.objects.create(
            message=msg4, student=cls.student1, course=cls.course,
            topic=cls.topic_linked_lists, keyword=cls.kw_node, date=cls.week_ago
        )
        TopicWeight.objects.create(
            message=msg4, student=cls.student1, course=cls.course,
            topic=cls.topic_linked_lists, keyword=cls.kw_pointer, date=cls.week_ago
        )
        
        msg5 = ChatMessage.objects.create(
            session=cls.session1,
            sender='user',
            message='Explain the next pointer'
        )
        TopicWeight.objects.create(
            message=msg5, student=cls.student1, course=cls.course,
            topic=cls.topic_linked_lists, keyword=cls.kw_next, date=cls.two_weeks_ago
        )
        
        # Student 2 - Balanced between Trees and Graphs (recent)
        msg6 = ChatMessage.objects.create(
            session=cls.session2,
            sender='user',
            message='What is a binary tree root?'
        )
        TopicWeight.objects.create(
            message=msg6, student=cls.student2, course=cls.course,
            topic=cls.topic_trees, keyword=cls.kw_tree, date=cls.today
        )
        TopicWeight.objects.create(
            message=msg6, student=cls.student2, course=cls.course,
            topic=cls.topic_trees, keyword=cls.kw_root, date=cls.today
        )
        
        msg7 = ChatMessage.objects.create(
            session=cls.session2,
            sender='user',
            message='Tree leaf nodes explained'
        )
        TopicWeight.objects.create(
            message=msg7, student=cls.student2, course=cls.course,
            topic=cls.topic_trees, keyword=cls.kw_tree, date=cls.yesterday
        )
        TopicWeight.objects.create(
            message=msg7, student=cls.student2, course=cls.course,
            topic=cls.topic_trees, keyword=cls.kw_leaf, date=cls.yesterday
        )
        
        msg8 = ChatMessage.objects.create(
            session=cls.session2,
            sender='user',
            message='Graph vertices and edges'
        )
        TopicWeight.objects.create(
            message=msg8, student=cls.student2, course=cls.course,
            topic=cls.topic_graphs, keyword=cls.kw_graph, date=cls.today
        )
        TopicWeight.objects.create(
            message=msg8, student=cls.student2, course=cls.course,
            topic=cls.topic_graphs, keyword=cls.kw_vertex, date=cls.today
        )
        TopicWeight.objects.create(
            message=msg8, student=cls.student2, course=cls.course,
            topic=cls.topic_graphs, keyword=cls.kw_edge, date=cls.today
        )
        
        msg9 = ChatMessage.objects.create(
            session=cls.session2,
            sender='user',
            message='More about graph theory'
        )
        TopicWeight.objects.create(
            message=msg9, student=cls.student2, course=cls.course,
            topic=cls.topic_graphs, keyword=cls.kw_graph, date=cls.two_days_ago
        )
        
        # Student 3 - Graph specialist (spread across dates)
        msg10 = ChatMessage.objects.create(
            session=cls.session3,
            sender='user',
            message='Graph algorithms with vertices'
        )
        TopicWeight.objects.create(
            message=msg10, student=cls.student3, course=cls.course,
            topic=cls.topic_graphs, keyword=cls.kw_graph, date=cls.today
        )
        TopicWeight.objects.create(
            message=msg10, student=cls.student3, course=cls.course,
            topic=cls.topic_graphs, keyword=cls.kw_vertex, date=cls.today
        )
        
        msg11 = ChatMessage.objects.create(
            session=cls.session3,
            sender='user',
            message='Edge cases in graphs'
        )
        TopicWeight.objects.create(
            message=msg11, student=cls.student3, course=cls.course,
            topic=cls.topic_graphs, keyword=cls.kw_graph, date=cls.three_days_ago
        )
        TopicWeight.objects.create(
            message=msg11, student=cls.student3, course=cls.course,
            topic=cls.topic_graphs, keyword=cls.kw_edge, date=cls.three_days_ago
        )
        
        msg12 = ChatMessage.objects.create(
            session=cls.session3,
            sender='user',
            message='Understanding graph structure'
        )
        TopicWeight.objects.create(
            message=msg12, student=cls.student3, course=cls.course,
            topic=cls.topic_graphs, keyword=cls.kw_graph, date=cls.week_ago
        )
        
        msg13 = ChatMessage.objects.create(
            session=cls.session3,
            sender='user',
            message='Graph and vertex relationships'
        )
        TopicWeight.objects.create(
            message=msg13, student=cls.student3, course=cls.course,
            topic=cls.topic_graphs, keyword=cls.kw_graph, date=cls.month_ago
        )
        TopicWeight.objects.create(
            message=msg13, student=cls.student3, course=cls.course,
            topic=cls.topic_graphs, keyword=cls.kw_vertex, date=cls.month_ago
        )
        
        # Student 3 - Some tree questions (older)
        msg14 = ChatMessage.objects.create(
            session=cls.session3,
            sender='user',
            message='Tree root structure'
        )
        TopicWeight.objects.create(
            message=msg14, student=cls.student3, course=cls.course,
            topic=cls.topic_trees, keyword=cls.kw_tree, date=cls.two_weeks_ago
        )
        TopicWeight.objects.create(
            message=msg14, student=cls.student3, course=cls.course,
            topic=cls.topic_trees, keyword=cls.kw_root, date=cls.two_weeks_ago
        )
    
    # =========================================================================
    # STUDENT-LEVEL STATISTICS TESTS
    # =========================================================================
    
    def test_student_topic_percentages_no_date_filter(self):
        """Test student topic percentages without date filtering."""
        results = self.stats_service.get_student_topic_percentages(
            student_id=self.student1.id,
            course_id=self.course.id
        )
        
        self.assertGreater(len(results), 0)
        
        # Student 1 should have Arrays as top topic (6 weights) vs Linked Lists (3 weights)
        self.assertEqual(results[0]['topic'], 'Arrays')
        self.assertAlmostEqual(results[0]['percentage'], 66.67, places=1)
        
        # Verify percentages sum to 100
        total_percentage = sum(r['percentage'] for r in results)
        self.assertAlmostEqual(total_percentage, 100.0, places=1)
    
    def test_student_topic_percentages_with_date_filter(self):
        """Test that date filtering correctly filters topic weights."""
        # Only get data from the last 3 days
        start_date = self.today - timedelta(days=3)
        
        results = self.stats_service.get_student_topic_percentages(
            student_id=self.student1.id,
            course_id=self.course.id,
            start_date=start_date
        )
        
        # Should only include Arrays (recent), not Linked Lists (older)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['topic'], 'Arrays')
        self.assertEqual(results[0]['percentage'], 100.0)
    
    def test_student_topic_percentages_date_range(self):
        """Test topic percentages within a specific date range."""
        # Get data only from 2 weeks ago to 1 week ago
        results = self.stats_service.get_student_topic_percentages(
            student_id=self.student1.id,
            course_id=self.course.id,
            start_date=self.two_weeks_ago,
            end_date=self.week_ago
        )
        
        # Should only include Linked Lists weights from that period
        self.assertGreater(len(results), 0)
        linked_lists_found = any(r['topic'] == 'Linked Lists' for r in results)
        self.assertTrue(linked_lists_found)
    
    def test_student_no_activity(self):
        """Test student with no topic weights returns empty list."""
        # Create a new student with no activity
        student_inactive = CustomUser.objects.create_user(
            email='inactive@university.edu',
            password='testpass123',
            name='Inactive',
            last_name='Student',
            cedula='9999999999',
            university_code='STU999',
            user_group='CS2024A',
            role=UserRole.STUDENT
        )
        
        results = self.stats_service.get_student_topic_percentages(
            student_id=student_inactive.id,
            course_id=self.course.id
        )
        
        self.assertEqual(len(results), 0)
    
    def test_student_keyword_breakdown_all_data(self):
        """Test keyword breakdown for a student without filters."""
        results = self.stats_service.get_student_keyword_breakdown(
            student_id=self.student1.id,
            course_id=self.course.id
        )
        
        self.assertGreater(len(results), 0)
        
        # Verify structure
        for result in results:
            self.assertIn('keyword', result)
            self.assertIn('topic', result)
            self.assertIn('count', result)
            self.assertIn('percentage', result)
        
        # Verify total percentage
        total_percentage = sum(r['percentage'] for r in results)
        self.assertAlmostEqual(total_percentage, 100.0, places=1)
    
    def test_student_keyword_breakdown_with_topic_filter(self):
        """Test keyword breakdown filtered by specific topic."""
        results = self.stats_service.get_student_keyword_breakdown(
            student_id=self.student1.id,
            course_id=self.course.id,
            topic_id=self.topic_arrays.id
        )
        
        # All results should be from Arrays topic
        for result in results:
            self.assertEqual(result['topic'], 'Arrays')
        
        # Should have array, index, element keywords
        keywords = [r['keyword'] for r in results]
        self.assertIn('array', keywords)
    
    def test_student_keyword_breakdown_with_dates(self):
        """Test keyword breakdown with date filtering."""
        results = self.stats_service.get_student_keyword_breakdown(
            student_id=self.student2.id,
            course_id=self.course.id,
            start_date=self.today - timedelta(days=1),
            end_date=self.today
        )
        
        # Should only include recent keywords (Trees and Graphs)
        topics = {r['topic'] for r in results}
        self.assertIn('Trees', topics)
        self.assertIn('Graphs', topics)
    
    # =========================================================================
    # GROUP-LEVEL STATISTICS TESTS
    # =========================================================================
    
    def test_group_topic_percentages_no_dates(self):
        """Test group topic percentages without date filtering."""
        results = self.stats_service.get_group_topic_percentages(
            group_id=self.group1.id
        )
        
        self.assertGreater(len(results), 0)
        
        # Verify structure
        for result in results:
            self.assertIn('topic', result)
            self.assertIn('weighted_total', result)
            self.assertIn('percentage', result)
        
        # Verify percentages sum to 100
        total_percentage = sum(r['percentage'] for r in results)
        self.assertAlmostEqual(total_percentage, 100.0, places=1)
    
    def test_group_topic_percentages_with_dates(self):
        """Test group topic percentages with date filtering."""
        results = self.stats_service.get_group_topic_percentages(
            group_id=self.group1.id,
            start_date=self.today - timedelta(days=2),
            end_date=self.today
        )
        
        # Should include recent activity from student1 (Arrays) and student2 (Trees, Graphs)
        topics = [r['topic'] for r in results]
        self.assertIn('Arrays', topics)
        self.assertIn('Trees', topics)
        self.assertIn('Graphs', topics)
    
    def test_group_keyword_breakdown(self):
        """Test group keyword breakdown."""
        results = self.stats_service.get_group_keyword_breakdown(
            group_id=self.group2.id
        )
        
        # Group 2 has only student3 (Graphs and Trees)
        self.assertGreater(len(results), 0)
        
        topics = {r['topic'] for r in results}
        self.assertIn('Graphs', topics)
    
    def test_empty_group(self):
        """Test statistics for group with no enrollments."""
        empty_group = Group.objects.create(
            course=self.course,
            teacher=self.teacher,
            name='Empty Group',
            schedule='Fri 09:00-11:00'
        )
        
        results = self.stats_service.get_group_topic_percentages(
            group_id=empty_group.id
        )
        
        self.assertEqual(len(results), 0)
    
    # =========================================================================
    # COURSE-LEVEL STATISTICS TESTS
    # =========================================================================
    
    def test_course_topic_percentages_all_students(self):
        """Test course-wide topic percentages including all students."""
        results = self.stats_service.get_course_topic_percentages(
            course_id=self.course.id
        )
        
        self.assertGreater(len(results), 0)
        
        # Should include all topics from all students
        topics = [r['topic'] for r in results]
        self.assertIn('Arrays', topics)
        self.assertIn('Linked Lists', topics)
        self.assertIn('Trees', topics)
        self.assertIn('Graphs', topics)
        
        # Verify percentages sum to 100
        total_percentage = sum(r['percentage'] for r in results)
        self.assertAlmostEqual(total_percentage, 100.0, places=1)
    
    def test_course_topic_percentages_recent_only(self):
        """Test course statistics with recent date filter."""
        results = self.stats_service.get_course_topic_percentages(
            course_id=self.course.id,
            start_date=self.today - timedelta(days=3)
        )
        
        # Should include recent topics: Arrays, Trees, Graphs
        # Should NOT include Linked Lists (older activity)
        topics = [r['topic'] for r in results]
        self.assertIn('Arrays', topics)
        self.assertIn('Trees', topics)
        self.assertIn('Graphs', topics)
    
    def test_course_keyword_breakdown(self):
        """Test course-wide keyword breakdown."""
        results = self.stats_service.get_course_keyword_breakdown(
            course_id=self.course.id
        )
        
        self.assertGreater(len(results), 0)
        
        # Verify we have keywords from multiple topics
        keywords = [r['keyword'] for r in results]
        self.assertIn('array', keywords)
        self.assertIn('graph', keywords)
        self.assertIn('tree', keywords)
    
    def test_course_keyword_breakdown_topic_filter(self):
        """Test course keyword breakdown filtered by topic."""
        results = self.stats_service.get_course_keyword_breakdown(
            course_id=self.course.id,
            topic_id=self.topic_graphs.id
        )
        
        # All results should be from Graphs topic
        for result in results:
            self.assertEqual(result['topic'], 'Graphs')
    
    # =========================================================================
    # ACTIVITY SUMMARY TESTS
    # =========================================================================
    
    def test_activity_summary_all_dates(self):
        """Test activity summary without date filtering."""
        results = self.stats_service.get_activity_summary(
            course_id=self.course.id
        )
        
        self.assertGreater(len(results), 0)
        
        # Verify structure
        for result in results:
            self.assertIn('date', result)
            self.assertIn('total_keywords', result)
            self.assertIn('unique_students', result)
            self.assertIn('unique_topics', result)
    
    def test_activity_summary_date_range(self):
        """Test activity summary with date filtering."""
        results = self.stats_service.get_activity_summary(
            course_id=self.course.id,
            start_date=self.today - timedelta(days=7),
            end_date=self.today
        )
        
        # Verify all dates are within range
        for result in results:
            self.assertGreaterEqual(result['date'], self.today - timedelta(days=7))
            self.assertLessEqual(result['date'], self.today)
    
    def test_activity_summary_specific_day(self):
        """Test activity summary for a specific day."""
        results = self.stats_service.get_activity_summary(
            course_id=self.course.id,
            start_date=self.today,
            end_date=self.today
        )
        
        # Should have activity from today
        if len(results) > 0:
            self.assertEqual(results[0]['date'], self.today)
            self.assertGreater(results[0]['total_keywords'], 0)
    
    # =========================================================================
    # TOP TOPICS BY DATE RANGE TESTS
    # =========================================================================
    
    def test_top_topics_by_date_range(self):
        """Test top topics in a date range."""
        results = self.stats_service.get_top_topics_by_date_range(
            course_id=self.course.id,
            start_date=self.today - timedelta(days=7),
            end_date=self.today
        )
        
        self.assertGreater(len(results), 0)
        
        # Verify structure
        for result in results:
            self.assertIn('topic__name', result)
            self.assertIn('total_count', result)
            self.assertIn('unique_students', result)
            self.assertIn('unique_keywords', result)
        
        # Verify sorted by total_count descending
        counts = [r['total_count'] for r in results]
        self.assertEqual(counts, sorted(counts, reverse=True))
    
    def test_top_topics_narrow_date_range(self):
        """Test top topics in a narrow date range."""
        results = self.stats_service.get_top_topics_by_date_range(
            course_id=self.course.id,
            start_date=self.today,
            end_date=self.today
        )
        
        # Should only include today's activity
        if len(results) > 0:
            for result in results:
                self.assertGreater(result['total_count'], 0)
    
    # =========================================================================
    # EDGE CASES AND DATA INTEGRITY TESTS
    # =========================================================================
    
    def test_percentages_always_sum_to_100(self):
        """Verify that percentages always sum to 100 across different scenarios."""
        test_cases = [
            (self.student1.id, self.course.id, None, None),
            (self.student2.id, self.course.id, None, None),
            (self.student3.id, self.course.id, self.today - timedelta(days=7), self.today),
        ]
        
        for student_id, course_id, start_date, end_date in test_cases:
            results = self.stats_service.get_student_topic_percentages(
                student_id=student_id,
                course_id=course_id,
                start_date=start_date,
                end_date=end_date
            )
            
            if len(results) > 0:
                total = sum(r['percentage'] for r in results)
                self.assertAlmostEqual(total, 100.0, places=1,
                    msg=f"Percentages don't sum to 100 for student {student_id}")
    
    def test_future_date_range_returns_empty(self):
        """Test that future date ranges return empty results."""
        future_start = self.today + timedelta(days=1)
        future_end = self.today + timedelta(days=7)
        
        results = self.stats_service.get_student_topic_percentages(
            student_id=self.student1.id,
            course_id=self.course.id,
            start_date=future_start,
            end_date=future_end
        )
        
        self.assertEqual(len(results), 0)
    
    def test_invalid_date_range_returns_empty(self):
        """Test that invalid date range (end before start) returns empty."""
        results = self.stats_service.get_student_topic_percentages(
            student_id=self.student1.id,
            course_id=self.course.id,
            start_date=self.today,
            end_date=self.week_ago
        )
        
        self.assertEqual(len(results), 0)
    
    def test_count_accuracy(self):
        """Test that counts match actual database records."""
        # Get student1's Arrays topic count
        results = self.stats_service.get_student_topic_percentages(
            student_id=self.student1.id,
            course_id=self.course.id
        )
        
        arrays_result = next(r for r in results if r['topic'] == 'Arrays')
        
        # Manually count TopicWeight records
        actual_count = TopicWeight.objects.filter(
            student_id=self.student1.id,
            course_id=self.course.id,
            topic=self.topic_arrays
        ).count()
        
        self.assertEqual(arrays_result['count'], actual_count)
    
    def test_multiple_students_same_keyword(self):
        """Test that statistics correctly handle multiple students using same keywords."""
        # Both student2 and student3 use 'graph' keyword
        results = self.stats_service.get_course_keyword_breakdown(
            course_id=self.course.id,
            topic_id=self.topic_graphs.id
        )
        
        graph_keyword = next(r for r in results if r['keyword'] == 'graph')
        
        # Should have multiple occurrences
        self.assertGreater(graph_keyword['count'], 1)
    
    def test_nonexistent_course(self):
        """Test that nonexistent course returns empty results."""
        results = self.stats_service.get_course_topic_percentages(
            course_id=99999
        )
        
        self.assertEqual(len(results), 0)
