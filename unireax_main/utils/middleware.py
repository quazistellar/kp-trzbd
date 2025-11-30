import threading

_thread_locals = threading.local()

def get_current_request():
    """Функция возвращает текущий request, установленный middleware"""
    return getattr(_thread_locals, 'request', None)


class RequestMiddleware:
    """Middleware для сохранения request в thread local storage"""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.request = request
        
        try:
            response = self.get_response(request)
            return response
        finally:
            if hasattr(_thread_locals, 'request'):
                del _thread_locals.request