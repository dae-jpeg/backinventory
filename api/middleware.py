from django.http import Http404, JsonResponse
from django.conf import settings
# from .models import Region
import logging
import jwt
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

class RegionMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # This middleware will need to be completely rewritten to handle
        # the new Company/Branch logic. For now, we'll disable it.
        request.region = None
        
        # region_slug = request.headers.get('X-Region-Slug')
        # if region_slug:
        #     try:
        #         request.region = Region.objects.get(slug=region_slug, is_active=True)
        #     except Region.DoesNotExist:
        #         request.region = None
        # else:
        #     request.region = None
        pass

class RegionValidationMiddleware:
    """
    Middleware to validate region access for authenticated users
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip validation for certain paths
        skip_paths = [
            '/api/regions/',
            '/api/register/',
            '/api/login/',
            '/api/qr-login/',
            '/api/profile/',
            '/admin/',
        ]
        
        current_path = request.path_info
        should_skip = any(current_path.startswith(path) for path in skip_paths)
        
        if should_skip:
            return self.get_response(request)
        
        # Only validate for authenticated users
        if hasattr(request, 'user') and request.user.is_authenticated:
            if hasattr(request, 'region') and request.region:
                # Check if user can access this region
                if not request.user.can_access_region(request.region):
                    logger.warning(f"User {request.user.id_number} denied access to region {request.region.name}")
                    return JsonResponse({
                        'error': 'Access denied to this region'
                    }, status=403)
        
        return self.get_response(request) 