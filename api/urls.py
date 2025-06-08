from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterUserView,
    QRLoginView,
    UserProfileView,
    UserLookupView,
    CustomUserViewSet,
    ItemViewSet,
    TransactionViewSet
)

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'users', CustomUserViewSet)
router.register(r'items', ItemViewSet)
router.register(r'transactions', TransactionViewSet, basename='transaction')

urlpatterns = [
    path('', include(router.urls)),
    path('register/', RegisterUserView.as_view(), name='register'),
    path('qr-login/', QRLoginView.as_view(), name='qr-login'),
    path('user-lookup/', UserLookupView.as_view(), name='user-lookup'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
