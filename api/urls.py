from django.urls import path
from .views import (
    UserRegistrationView,
    UserProfileView,
    UserListView,
    UserDetailView,
    CompanyListView,
    CompanyDetailView,
    BranchListView,
    BranchDetailView,
    CompanyMembershipView,
    CompanyMembershipDetailView,
    ItemListView,
    ItemDetailView,
    ItemScanCodeView,
    ItemUpdateOriginalStockView,
    AddStockView,
    RemoveStockView,
    TransactionListView,
    AllBranchesListView,
    AllItemsListView,
    CreateUserWithMembershipsView,
    CreateUserForCompanyView,
    QRLoginView,
    CategoryListCreateView,
    CategoryDetailView,
    UserBranchesListView,
    TransactionReceiptView,
    BranchStatisticsView
)

urlpatterns = [
    # User Management
    path('register/', UserRegistrationView.as_view(), name='user-register'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/<uuid:pk>/', UserDetailView.as_view(), name='user-detail'),
    path('users/create-with-memberships/', CreateUserWithMembershipsView.as_view(), name='user-create-with-memberships'),
    path('users/create-for-company/', CreateUserForCompanyView.as_view(), name='user-create-for-company'),

    # Company & Branch Management
    path('companies/', CompanyListView.as_view(), name='company-list'),
    path('companies/<uuid:pk>/', CompanyDetailView.as_view(), name='company-detail'),
    path('companies/<uuid:company_id>/branches/', BranchListView.as_view(), name='branch-list'),
    path('companies/<uuid:company_id>/branches/<uuid:pk>/', BranchDetailView.as_view(), name='branch-detail'),
    path('user-branches/', UserBranchesListView.as_view(), name='user-branches-list'),

    # Membership Management
    path('companies/<uuid:company_id>/members/', CompanyMembershipView.as_view(), name='company-membership'),
    path('companies/<uuid:company_id>/members/<uuid:membership_id>/', CompanyMembershipDetailView.as_view(), name='company-membership-detail'),

    # Inventory & Transactions
    path('items/', ItemListView.as_view(), name='item-list'),
    path('items/scan_code/', ItemScanCodeView.as_view(), name='item-scan-code'),
    path('items/<uuid:pk>/', ItemDetailView.as_view(), name='item-detail'),
    path('items/<uuid:item_id>/update-original-stock/', ItemUpdateOriginalStockView.as_view(), name='item-update-original-stock'),
    path('items/<uuid:pk>/add_stock/', AddStockView.as_view(), name='item-add-stock'),
    path('items/<uuid:pk>/remove_stock/', RemoveStockView.as_view(), name='item-remove-stock'),
    path('transactions/', TransactionListView.as_view(), name='transaction-list'),
    path('transactions/<uuid:id>/receipt/', TransactionReceiptView.as_view(), name='transaction-receipt'),

    # Category CRUD
    path('categories/', CategoryListCreateView.as_view(), name='category-list-create'),
    path('categories/<uuid:pk>/', CategoryDetailView.as_view(), name='category-detail'),

    # System-wide views for DEVELOPER
    path('all-branches/', AllBranchesListView.as_view(), name='all-branches-list'),
    path('all-items/', AllItemsListView.as_view(), name='all-items-list'),

    # Branch Statistics
    path('branch-statistics/', BranchStatisticsView.as_view(), name='branch-statistics'),

    path('qr-login/', QRLoginView.as_view(), name='qr-login'),
]
