from prometheus_client.core import GaugeMetricFamily
from django.db.models import Count
from django.contrib.admin.models import LogEntry
from django.utils import timezone
from datetime import date
from .models import Course, CourseCategory, User, Role

class CoursesByCategoryCollector:
    """метрика для Grafana - количество курсов по категориям"""
    def collect(self):
        metric = GaugeMetricFamily('courses_by_category', 'Число курсов по категориям', labels=['category_name'])
        counts = Course.objects.values('course_category__course_category_name').annotate(count=Count('id'))
        reported = set()

        for row in counts:
            name = row['course_category__course_category_name'] or "Без категории"
            metric.add_metric([name], float(row['count']))
            reported.add(name)

        for cat in CourseCategory.objects.exclude(course_category_name__in=reported):
            metric.add_metric([cat.course_category_name], 0.0)

        yield metric

class UsersByRoleCollector:
    """метрика для Grafana - количество пользователей по ролям"""
    def collect(self):
        metric = GaugeMetricFamily('users_by_role', 'Количество пользователей по ролям', labels=['role_name'])

        for role in Role.objects.all():
            count = User.objects.filter(role=role).count()
            metric.add_metric([role.role_name], float(count))

        null_count = User.objects.filter(role__isnull=True).count()
        if null_count:
            metric.add_metric(["Не указана"], float(null_count))

        yield metric

class UsersPendingVerificationCollector:
    """метрика для Grafana - количество пользователей, ожидающих подтверждения"""
    def collect(self):
        pending_count = User.objects.filter(is_verified=False).count()
        verified_count = User.objects.filter(is_verified=True).count()

        metric = GaugeMetricFamily('users_verification_status', 'Статус верификации пользователей', labels=['status'])
        metric.add_metric(['ожидают подтверждения'], float(pending_count))
        metric.add_metric(['подтверждены'], float(verified_count))
        yield metric