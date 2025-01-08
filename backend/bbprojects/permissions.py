from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the snippet
        return obj.owner == request.user

class IsUserOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow users to edit their own profile.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        return obj == request.user

class IsPublicOrIsOwner(permissions.BasePermission):
    """
    Custom permission to only allow access to public snippets or owner's snippets.
    """
    def has_object_permission(self, request, view, obj):
        # Allow access if snippet is public
        if obj.is_public:
            return True
            
        # Allow access if user is the owner
        return request.user and request.user == obj.owner 