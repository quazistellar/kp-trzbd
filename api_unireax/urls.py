from django.urls import path, include
from rest_framework import routers
from .views import *

app_name = 'api'  


router = routers.SimpleRouter()

router.register('roles', RoleViewSet, basename='roles')
router.register('users', UserViewSet, basename='users')
router.register('course-categories', CourseCategoryViewSet, basename='course-categories')
router.register('course-types', CourseTypeViewSet, basename='course-types')
router.register('assignment-statuses', AssignmentStatusViewSet, basename='assignment-statuses')
router.register('courses', CourseViewSet, basename='courses')
router.register('course-teachers', CourseTeacherViewSet, basename='course-teachers')
router.register('lectures', LectureViewSet, basename='lectures')
router.register('practical-assignments', PracticalAssignmentViewSet, basename='practical-assignments')
router.register('user-practical-assignments', UserPracticalAssignmentViewSet, basename='user-practical-assignments')
router.register('user-courses', UserCourseViewSet, basename='user-courses')
router.register('feedback', FeedbackViewSet, basename='feedback')
router.register('reviews', ReviewViewSet, basename='reviews')
router.register('answer-types', AnswerTypeViewSet, basename='answer-types')
router.register('tests', TestViewSet, basename='tests')
router.register('questions', QuestionViewSet, basename='questions')
router.register('choice-options', ChoiceOptionViewSet, basename='choice-options')
router.register('matching-pairs', MatchingPairViewSet, basename='matching-pairs')
router.register('user-answers', UserAnswerViewSet, basename='user-answers')
router.register('user-selected-choices', UserSelectedChoiceViewSet, basename='user-selected-choices')
router.register('user-matching-answers', UserMatchingAnswerViewSet, basename='user-matching-answers')
router.register('test-results', TestResultViewSet, basename='test-results')
router.register('certificates', CertificateViewSet, basename='certificates')
router.register('assignment-submission-files', AssignmentSubmissionFileViewSet, basename='assignment-submission-files')
router.register('password-reset-codes', PasswordResetCodeViewSet, basename='password-reset-codes')


router.register('view-course-assignments', ViewCoursePracticalAssignmentsViewSet, basename='view-course-assignments')
router.register('view-course-lectures', ViewCourseLecturesViewSet, basename='view-course-lectures')
router.register('view-course-tests', ViewCourseTestsViewSet, basename='view-course-tests')
router.register('view-assignment-submissions', ViewAssignmentSubmissionsViewSet, basename='view-assignment-submissions')

router.register('course-analytics', CourseAnalyticsViewSet, basename='course-analytics')
router.register('user-progress', UserProgressViewSet, basename='user-progress')

router.register('platform-stats', PlatformStatsViewSet, basename='platform-stats')


router.register('test-exceptions', TestExceptionsViewSet, basename='test-exceptions')

urlpatterns = [
    path('', include(router.urls)),
]

