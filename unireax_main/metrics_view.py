from django.http import HttpResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry
from prometheus_client.multiprocess import MultiProcessCollector
from prometheus_client import REGISTRY
from os import getenv


def prometheus_metrics_view(request):
    if getenv('PROMETHEUS_MULTIPROC_DIR'):
        registry = CollectorRegistry()
        MultiProcessCollector(registry)
    else:
        registry = REGISTRY

    from .metrics import (
        CoursesByCategoryCollector,
        UsersByRoleCollector,
        UsersPendingVerificationCollector,
    )

    collectors = [
        CoursesByCategoryCollector,
        UsersByRoleCollector,
        UsersPendingVerificationCollector,
    ]

    for collector in collectors:
        try:
            registry.register(collector())
        except ValueError:
            pass  

    data = generate_latest(registry)
    return HttpResponse(data, content_type=CONTENT_TYPE_LATEST)