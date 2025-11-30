from rest_framework import permissions
from rest_framework.pagination import PageNumberPagination


class CustomPermission(permissions.BasePermission):
    """
    разграничение прав доступа только для суперпользователя и администраторов
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        if hasattr(request.user, 'role') and request.user.role:
            return request.user.role.role_name == 'администратор'
        
        return False
    
    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class PaginationPage(PageNumberPagination):
    page_size_query_param = 'page_size'
    page_query_param = 'page'
    page_size = 4