from rest_framework import permissions

class IsBossDeveloper(permissions.BasePermission):
    """
    Allows access only to users with the global 'DEVELOPER' level.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.global_user_level == 'DEVELOPER'

class IsCompanyOwner(permissions.BasePermission):
    """
    Allows access only to users with 'OWNER' role in the company.
    Checks company membership role instead of the owner field.
    """
    def has_permission(self, request, view):
        # For list views or when object is not available
        # Check if user has 'OWNER' role in any company
        return request.user and request.user.is_authenticated and request.user.company_memberships.filter(role='OWNER').exists()

    def has_object_permission(self, request, view, obj):
        from .models import Company
        # For Company objects, check if the user has 'OWNER' role
        if isinstance(obj, Company):
            return obj.members.filter(user=request.user, role='OWNER').exists()
        # For objects related to a company (like Branch), check the company membership
        if hasattr(obj, 'company'):
            return obj.company.members.filter(user=request.user, role='OWNER').exists()
        return False

class IsSupervisor(permissions.BasePermission):
    """
    Allows access to users who have a 'SUPERVISOR' role in the relevant company.
    """
    def has_permission(self, request, view):
        # This check is more complex and might depend on the view's context.
        # It could involve checking if the user has a supervisor role in ANY company,
        # or in the specific company being accessed.
        # For now, we'll keep it simple.
        if not (request.user and request.user.is_authenticated):
            return False
        
        # A basic check for a supervisor role in any company membership.
        # More specific object-level permissions might be needed.
        return request.user.company_memberships.filter(role='SUPERVISOR').exists()

    def has_object_permission(self, request, view, obj):
        # Check if the user is a supervisor in the company related to the object.
        from .models import Company, Branch, CompanyMembership
        company = None
        if isinstance(obj, Company):
            company = obj
        elif isinstance(obj, (Branch, CompanyMembership)):
            company = obj.company

        if company:
            return company.members.filter(user=request.user, role='SUPERVISOR').exists()
        return False 