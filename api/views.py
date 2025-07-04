from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Item, Transaction, Company, Branch, CompanyMembership, Category
from .serializers import (
    ItemSerializer, TransactionSerializer, UserProfileSerializer,
    UserRegistrationSerializer, CompanySerializer, BranchSerializer,
    AdminUserSerializer, CompanyMembershipSerializer, CategorySerializer
)
from .permissions import IsBossDeveloper, IsCompanyOwner, IsSupervisor
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated, AllowAny
import logging
from django.db import transaction
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from rest_framework.decorators import action
from rest_framework.generics import RetrieveAPIView
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime, timedelta

User = get_user_model()

logger = logging.getLogger(__name__)

# --- User Management Views ---

class UserRegistrationView(generics.CreateAPIView):
    """Public endpoint for new user registration."""
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

class UserProfileView(generics.RetrieveAPIView):
    """Endpoint to retrieve the profile of the currently authenticated user."""
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

class UserListView(generics.ListAPIView):
    """Endpoint for admins/developers to list users."""
    serializer_class = AdminUserSerializer
    permission_classes = [permissions.IsAuthenticated, IsBossDeveloper | IsCompanyOwner]
    filter_backends = [filters.SearchFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name', 'id_number']

    def get_queryset(self):
        user = self.request.user
        if user.global_user_level == 'DEVELOPER':
            return User.objects.all()
        
        # Company owners can see users in their companies
        owned_companies = Company.objects.filter(owner=user)
        return User.objects.filter(company_memberships__company__in=owned_companies).distinct()

class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = AdminUserSerializer
    permission_classes = [permissions.IsAuthenticated, IsBossDeveloper | IsCompanyOwner]

# --- Company & Branch Management Views ---

class CompanyListView(generics.ListCreateAPIView):
    """Endpoint for listing companies or creating a new one."""
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.global_user_level == 'DEVELOPER':
            return Company.objects.all()
        
        # Return companies the user is a member of
        return Company.objects.filter(members__id=user.id)

    def perform_create(self, serializer):
        company = serializer.save(owner=self.request.user)
        # Automatically make the creator a member with 'OWNER' role
        CompanyMembership.objects.create(
            user=self.request.user, 
            company=company, 
            role='OWNER'
        )

class CompanyDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Endpoint for managing a specific company."""
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated, IsBossDeveloper | IsCompanyOwner]
    queryset = Company.objects.all()

class BranchListView(generics.ListCreateAPIView):
    """Endpoint for listing branches of a company or creating a new one."""
    serializer_class = BranchSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyOwner]

    def get_queryset(self):
        company_id = self.kwargs['company_id']
        return Branch.objects.filter(company_id=company_id)

    def perform_create(self, serializer):
        company_id = self.kwargs['company_id']
        company = Company.objects.get(pk=company_id)
        serializer.save(company=company)

class BranchDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Endpoint for managing a specific branch."""
    serializer_class = BranchSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyOwner]
    lookup_url_kwarg = 'pk'

    def get_queryset(self):
        company_id = self.kwargs['company_id']
        return Branch.objects.filter(company_id=company_id)

class AllBranchesListView(generics.ListAPIView):
    """
    System-wide endpoint for DEVELOPER to list and filter all branches.
    """
    serializer_class = BranchSerializer
    permission_classes = [permissions.IsAuthenticated, IsBossDeveloper]
    queryset = Branch.objects.select_related('company').all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['company'] # Filter by company ID: /api/all-branches/?company=1
    search_fields = ['name', 'company__name'] # Search by branch or company name

# --- Membership Management ---

class CompanyMembershipView(generics.ListCreateAPIView):
    """Endpoint to list members of a company or add a new one."""
    serializer_class = CompanyMembershipSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyOwner | IsSupervisor]

    def get_queryset(self):
        company_id = self.kwargs['company_id']
        return CompanyMembership.objects.filter(company_id=company_id)

    def perform_create(self, serializer):
        company_id = self.kwargs['company_id']
        company = Company.objects.get(pk=company_id)
        # Ensure the creator has permission to add members to this company
        if company.owner != self.request.user and not self.request.user.global_user_level == 'DEVELOPER':
             self.permission_denied(self.request, message="You do not have permission to add members to this company.")
        serializer.save(company=company)

class CompanyMembershipDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Endpoint for managing individual company memberships."""
    serializer_class = CompanyMembershipSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyOwner | IsSupervisor]
    lookup_url_kwarg = 'membership_id'

    def get_queryset(self):
        company_id = self.kwargs['company_id']
        return CompanyMembership.objects.filter(company_id=company_id)

    @transaction.atomic
    def perform_update(self, serializer):
        try:
            # Additional validation for role changes
            if 'role' in self.request.data:
                new_role = self.request.data['role']
                if new_role == 'SUPERVISOR' and not self.request.user.global_user_level == 'DEVELOPER':
                    self.permission_denied(
                        self.request,
                        message="Only DEVELOPER can assign SUPERVISOR role."
                    )
            
            logger.info(f"Updating membership {serializer.instance.id}")
            logger.info(f"Request data: {self.request.data}")
            logger.info(f"Current instance state: {serializer.instance.__dict__}")
            
            # Log branch information if it's being updated
            if 'branch' in self.request.data:
                branch_id = self.request.data['branch']
                try:
                    branch = Branch.objects.get(id=branch_id)
                    logger.info(f"Branch being assigned: {branch.id}, {branch.name}, Company: {branch.company.id}")
                    
                    # Verify branch belongs to company
                    if branch.company_id != serializer.instance.company_id:
                        raise DRFValidationError({
                            'branch': f'Branch {branch.name} does not belong to company {serializer.instance.company.name}'
                        })
                except Branch.DoesNotExist:
                    logger.error(f"Branch with ID {branch_id} not found")
                    raise DRFValidationError({'branch': f'Branch with ID {branch_id} not found'})
                except Exception as e:
                    logger.error(f"Error fetching branch info: {str(e)}")
                    raise

            # Save the instance
            instance = serializer.save()
            logger.info(f"Successfully updated membership {instance.id}")
            return instance
            
        except DRFValidationError:
            raise
        except Exception as e:
            logger.error(f"Error updating membership: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Error args: {e.args}")
            raise

    def update(self, request, *args, **kwargs):
        try:
            logger.info(f"Received PATCH request for membership {kwargs.get('membership_id')}")
            logger.info(f"Request data: {request.data}")
            
            response = super().update(request, *args, **kwargs)
            logger.info("Update completed successfully")
            return response
            
        except Exception as e:
            logger.error(f"Error in update: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Error args: {e.args}")
            raise

class ItemScanCodeView(APIView):
    """Endpoint for scanning items by barcode or QR code."""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        scan_type = request.data.get('type')  # 'barcode' or 'qr'
        scan_value = request.data.get('value')
        
        if not scan_type or not scan_value:
            return Response(
                {'error': 'Both type and value are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = request.user
        
        try:
            if scan_type == 'barcode':
                # Search by barcode number
                items = Item.objects.filter(barcode_number=scan_value)
            elif scan_type == 'qr':
                # For QR codes, extract UUID if it starts with 'item:'
                if scan_value.startswith('item:'):
                    item_id = scan_value.replace('item:', '')
                    items = Item.objects.filter(id=item_id)
                else:
                    # Try direct UUID lookup
                    items = Item.objects.filter(id=scan_value)
            else:
                return Response(
                    {'error': 'Invalid scan type. Use "barcode" or "qr"'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Filter by user access
            if user.company_memberships.filter(role__in=['SUPERVISOR', 'OWNER']).exists():
                company_ids = user.company_memberships.filter(role__in=['SUPERVISOR', 'OWNER']).values_list('company_id', flat=True)
                branch_ids = Branch.objects.filter(company_id__in=company_ids).values_list('id', flat=True)
                items = items.filter(branch_id__in=branch_ids)
            else:
                accessible_branches = user.company_memberships.values_list('branch_id', flat=True)
                items = items.filter(branch_id__in=accessible_branches)
            
            if not items.exists():
                return Response(
                    {'error': f'Item not found with this {scan_type}'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Return the first matching item
            item = items.first()
            serializer = ItemSerializer(item)
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {'error': f'Error scanning item: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ItemListView(generics.ListCreateAPIView):
    """Endpoint for listing or creating items within a user's accessible branches."""
    serializer_class = ItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name', 'item_id', 'description']
    filterset_fields = ['barcode_number', 'branch__company']

    def get_queryset(self):
        user = self.request.user
        # Supervisors and Owners see all items in their companies
        if user.company_memberships.filter(role__in=['SUPERVISOR', 'OWNER']).exists():
            company_ids = user.company_memberships.filter(role__in=['SUPERVISOR', 'OWNER']).values_list('company_id', flat=True)
            branch_ids = Branch.objects.filter(company_id__in=company_ids).values_list('id', flat=True)
            return Item.objects.filter(branch_id__in=branch_ids)
        # Otherwise, filter by accessible branches
        accessible_branches = user.company_memberships.values_list('branch_id', flat=True)
        return Item.objects.filter(branch_id__in=accessible_branches)

    def perform_create(self, serializer):
        branch_id = self.request.data.get('branch')
        user = self.request.user
        # Check if user is a supervisor or owner of the company that owns this branch
        if user.company_memberships.filter(role__in=['SUPERVISOR', 'OWNER']).exists():
            # Get the branch and check if it belongs to a company the user supervises
            try:
                branch = Branch.objects.get(id=branch_id)
                user_companies = user.company_memberships.filter(role__in=['SUPERVISOR', 'OWNER']).values_list('company_id', flat=True)
                if branch.company_id in user_companies:
                    item = serializer.save(created_by=self.request.user)
                    # Log CREATE event
                    Transaction.objects.create(
                        item=item,
                        user=self.request.user,
                        branch=item.branch,
                        transaction_type='CREATE',
                        quantity=item.stock_quantity,
                        notes='Item created'
                    )
                    return
            except Branch.DoesNotExist:
                pass
        # For regular users, check if they are a member of the specified branch
        if not CompanyMembership.objects.filter(user=user, branch_id=branch_id).exists():
            self.permission_denied(self.request, message="You are not authorized to add items to this branch.")
        item = serializer.save(created_by=self.request.user)
        # Log CREATE event
        Transaction.objects.create(
            item=item,
            user=self.request.user,
            branch=item.branch,
            transaction_type='CREATE',
            quantity=item.stock_quantity,
            notes='Item created'
        )

class AllItemsListView(generics.ListAPIView):
    """
    System-wide endpoint for DEVELOPER to list and filter all items.
    """
    serializer_class = ItemSerializer
    permission_classes = [permissions.IsAuthenticated, IsBossDeveloper]
    queryset = Item.objects.select_related('branch', 'branch__company').all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['branch', 'branch__company'] # /api/all-items/?branch=1 or /?branch__company=1
    search_fields = ['name', 'item_id', 'description', 'category']

class ItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Supervisors and Owners see all items in their companies
        if user.company_memberships.filter(role__in=['SUPERVISOR', 'OWNER']).exists():
            company_ids = user.company_memberships.filter(role__in=['SUPERVISOR', 'OWNER']).values_list('company_id', flat=True)
            branch_ids = Branch.objects.filter(company_id__in=company_ids).values_list('id', flat=True)
            return Item.objects.filter(branch_id__in=branch_ids)
        # Otherwise, filter by accessible branches
        accessible_branches = user.company_memberships.values_list('branch_id', flat=True)
        return Item.objects.filter(branch_id__in=accessible_branches)

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        item = self.get_object()
        from .models import Transaction
        Transaction.objects.create(
            item=item,
            user=request.user,
            branch=item.branch,
            transaction_type='UPDATE',
            quantity=item.stock_quantity,
            notes='Item updated'
        )
        return response

    def destroy(self, request, *args, **kwargs):
        item = self.get_object()
        from .models import Transaction
        Transaction.objects.create(
            item=item,
            user=request.user,
            branch=item.branch,
            transaction_type='DELETE',
            quantity=item.stock_quantity,
            notes='Item deleted'
        )
        return super().destroy(request, *args, **kwargs)

class TransactionListView(generics.ListCreateAPIView):
    """Endpoint for listing or creating transactions."""
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['branch__company', 'transaction_type', 'user']
    search_fields = ['item__name', 'user__username', 'notes', 'item__item_id']

    def get_queryset(self):
        user = self.request.user
        print(f"[DEBUG] TransactionListView.get_queryset - User: {user.username}, Level: {user.global_user_level}")
        
        # Supervisors and Owners see all transactions in their companies
        supervisor_companies = CompanyMembership.objects.filter(
            user=user, 
            role__in=['SUPERVISOR', 'OWNER']
        ).values_list('company_id', flat=True)
        if supervisor_companies.exists():
            company_branches = Branch.objects.filter(
                company_id__in=supervisor_companies
            ).values_list('id', flat=True)
            queryset = Transaction.objects.filter(branch_id__in=company_branches)
            print(f"[DEBUG] Supervisor/Owner view - Found {queryset.count()} transactions")
        else:
            # Otherwise, filter by accessible branches
            accessible_branches = CompanyMembership.objects.filter(user=user).values_list('branch_id', flat=True)
            queryset = Transaction.objects.filter(branch_id__in=accessible_branches)
            print(f"[DEBUG] Regular user view - Found {queryset.count()} transactions")
        
        # Add select_related to optimize queries
        return queryset.select_related('user', 'item', 'item__category', 'branch')
    
    def perform_create(self, serializer):
        print("[DEBUG] TransactionListView.perform_create called")
        # Get the item and branch from the request data
        item_id = self.request.data.get('item')
        branch_id = self.request.data.get('branch')
        user = self.request.user
        
        print(f"[DEBUG] Received item_id: {item_id}")
        print(f"[DEBUG] Received branch_id: {branch_id}")
        
        # Validate that the item exists and user has access to it
        try:
            item = Item.objects.get(id=item_id)
            print(f"[DEBUG] Found item: {item.name} (stock: {item.stock_quantity})")
            
            # Check if user has access to the item's branch
            # For supervisors/owners, check if they supervise the company that owns the branch
            if user.company_memberships.filter(role__in=['SUPERVISOR', 'OWNER']).exists():
                user_companies = user.company_memberships.filter(role__in=['SUPERVISOR', 'OWNER']).values_list('company_id', flat=True)
                if item.branch.company_id in user_companies:
                    print(f"[DEBUG] User is supervisor/owner of company {item.branch.company_id}")
                else:
                    raise Item.DoesNotExist("Item not accessible")
            else:
                # For regular users, check direct branch membership
                user_branches = CompanyMembership.objects.filter(user=user).values_list('branch_id', flat=True)
                if item.branch_id not in user_branches:
                    raise Item.DoesNotExist("Item not accessible")
        except Item.DoesNotExist:
            print("[DEBUG] Item not found or not accessible")
            raise serializers.ValidationError("Item not found or not accessible")
        
        # Validate that the branch exists and user has access to it
        try:
            branch = Branch.objects.get(id=branch_id)
            print(f"[DEBUG] Found branch: {branch.name}")
            
            # Check if user has access to the branch
            # For supervisors/owners, check if they supervise the company that owns the branch
            if user.company_memberships.filter(role__in=['SUPERVISOR', 'OWNER']).exists():
                user_companies = user.company_memberships.filter(role__in=['SUPERVISOR', 'OWNER']).values_list('company_id', flat=True)
                if branch.company_id in user_companies:
                    print(f"[DEBUG] User is supervisor/owner of company {branch.company_id}")
                else:
                    raise Branch.DoesNotExist("Branch not accessible")
            else:
                # For regular users, check direct branch membership
                user_branches = CompanyMembership.objects.filter(user=user).values_list('branch_id', flat=True)
                if branch.id not in user_branches:
                    raise Branch.DoesNotExist("Branch not accessible")
        except Branch.DoesNotExist:
            print("[DEBUG] Branch not found or not accessible")
            raise serializers.ValidationError("Branch not found or not accessible")
        
        print("[DEBUG] About to save transaction...")
        # Save the transaction with the validated item and branch
        transaction = serializer.save(user=self.request.user, item=item, branch=branch)
        print(f"[DEBUG] Transaction saved with ID: {transaction.id}")
        print(f"[DEBUG] Transaction type: {transaction.transaction_type}")

class CreateUserWithMembershipsSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    id_number = serializers.CharField(required=True)
    global_user_level = serializers.ChoiceField(choices=[('DEVELOPER', 'DEVELOPER'), ('SUPERVISOR', 'SUPERVISOR'), ('MEMBER', 'MEMBER')], default='MEMBER')
    memberships = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField()),
        help_text="List of {company: <company_id>, role: <role>} objects",
        required=True
    )

    def create(self, validated_data):
        memberships_data = validated_data.pop('memberships')
        
        # Ensure password is not passed directly to create_user if it's already handled
        password = validated_data.pop('password')

        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()

        for membership_data in memberships_data:
            company_id = membership_data['company']
            role = membership_data['role']
            company = Company.objects.get(id=company_id)
            CompanyMembership.objects.create(user=user, company=company, role=role)
            
        return user

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with that username already exists.")
        return value
    
    def validate_id_number(self, value):
        if User.objects.filter(id_number=value).exists():
            raise serializers.ValidationError("A user with that ID number already exists.")
        return value

class CreateUserWithMembershipsView(APIView):
    permission_classes = [IsAuthenticated, IsBossDeveloper]

    def post(self, request):
        serializer = CreateUserWithMembershipsSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'user_id': user.id, 
                'username': user.username,
                'qr_code': user.qr_code.url if user.qr_code else None
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CreateUserForCompanySerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    id_number = serializers.CharField(required=True)
    company_id = serializers.UUIDField()
    branch_id = serializers.UUIDField()
    role = serializers.ChoiceField(choices=['USER']) # Supervisors can only create users with 'USER' role

    def validate_company_id(self, value):
        # Ensure the company exists
        if not Company.objects.filter(id=value).exists():
            raise serializers.ValidationError("Company not found.")
        return value

    def create(self, validated_data):
        company_id = validated_data.pop('company_id')
        branch_id = validated_data.pop('branch_id')
        role = validated_data.pop('role')
        
        password = validated_data.pop('password')
        
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()

        company = Company.objects.get(id=company_id)
        CompanyMembership.objects.create(
            user=user, 
            company=company, 
            branch_id=branch_id, 
            role=role
        )
        return user

class CreateUserForCompanyView(APIView):
    """
    Endpoint for Supervisors/Owners to create a user and assign them
    directly to their company, a specific branch, and a 'MEMBER' role.
    """
    permission_classes = [IsAuthenticated, IsCompanyOwner | IsSupervisor]

    def post(self, request):
        serializer = CreateUserForCompanySerializer(data=request.data)
        if serializer.is_valid():
            # Security Check: Ensure the requesting user is part of the target company
            requesting_user = request.user
            target_company_id = request.data.get('company_id')
            
            is_member = CompanyMembership.objects.filter(
                user=requesting_user, 
                company_id=target_company_id,
                role__in=['OWNER', 'SUPERVISOR']
            ).exists()

            if not is_member and not requesting_user.global_user_level == 'DEVELOPER':
                return Response({'detail': 'You do not have permission to add users to this company.'}, status=status.HTTP_403_FORBIDDEN)
            
            user = serializer.save()
            return Response({
                'user_id': user.id,
                'username': user.username,
                'qr_code': user.qr_code.url if user.qr_code else None
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class QRLoginView(APIView):
    """
    Endpoint for logging in via QR code. Expects a POST with 'login_token' (UUID from QR code).
    Returns JWT tokens if successful.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        login_token = request.data.get('login_token')
        if not login_token:
            return Response({'detail': 'login_token is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(login_token=login_token)
        except User.DoesNotExist:
            return Response({'detail': 'Invalid QR token.'}, status=status.HTTP_401_UNAUTHORIZED)
        # Optionally, check if user is active
        if not user.is_active:
            return Response({'detail': 'User account is disabled.'}, status=status.HTTP_403_FORBIDDEN)
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        user_data = UserProfileSerializer(user).data
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': user_data,
        }, status=status.HTTP_200_OK)

# --- Category Management Views ---

class CategoryListCreateView(generics.ListCreateAPIView):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Optionally filter by company or branch
        company_id = self.request.query_params.get('company')
        branch_id = self.request.query_params.get('branch')
        qs = Category.objects.all()
        if company_id:
            qs = qs.filter(company_id=company_id)
        if branch_id and branch_id not in ('null', '', None):
            qs = qs.filter(branch_id=branch_id)
        return qs

    def perform_create(self, serializer):
        # Default to current user's company if not provided
        company = None
        branch = None
        user = self.request.user
        
        try:
            if 'company' in self.request.data:
                company = Company.objects.get(id=self.request.data['company'])
            elif hasattr(user, 'company_memberships') and user.company_memberships.exists():
                company = user.company_memberships.first().company
            
            if 'branch' in self.request.data and self.request.data['branch']:
                try:
                    branch = Branch.objects.get(id=self.request.data['branch'])
                except Branch.DoesNotExist:
                    raise serializers.ValidationError({
                        'branch': f'Branch with ID {self.request.data["branch"]} does not exist.'
                    })
            
            serializer.save(company=company, branch=branch)
        except Company.DoesNotExist:
            raise serializers.ValidationError({
                'company': 'Company not found.'
            })
        except Exception as e:
            raise serializers.ValidationError({
                'error': str(e)
            })

class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    queryset = Category.objects.all()

class UserBranchesListView(generics.ListAPIView):
    """
    Endpoint for getting all branches that the current user has access to.
    For supervisors/owners, this returns all branches in their companies.
    For regular users, this returns only the branches they are assigned to.
    """
    serializer_class = BranchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        
        # Supervisors and Owners see all branches in their companies
        if user.company_memberships.filter(role__in=['SUPERVISOR', 'OWNER']).exists():
            supervisor_companies = user.company_memberships.filter(
                role__in=['SUPERVISOR', 'OWNER']
            ).values_list('company_id', flat=True)
            return Branch.objects.filter(company_id__in=supervisor_companies)
        
        # Regular users see only branches they are assigned to
        user_branches = user.company_memberships.values_list('branch_id', flat=True)
        return Branch.objects.filter(id__in=user_branches)

class ItemUpdateOriginalStockView(APIView):
    """Endpoint for updating the original stock quantity of an item."""
    permission_classes = [permissions.IsAuthenticated, IsCompanyOwner | IsSupervisor]
    
    def post(self, request, item_id):
        try:
            new_original_stock = request.data.get('original_stock_quantity')
            if new_original_stock is None:
                return Response(
                    {'error': 'original_stock_quantity is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                new_original_stock = int(new_original_stock)
                if new_original_stock < 0:
                    return Response(
                        {'error': 'Original stock quantity cannot be negative'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except (ValueError, TypeError):
                return Response(
                    {'error': 'Original stock quantity must be a valid number'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get the item and check permissions
            try:
                item = Item.objects.get(id=item_id)
            except Item.DoesNotExist:
                return Response(
                    {'error': 'Item not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check if user has access to this item's branch
            user = request.user
            if user.company_memberships.filter(role__in=['SUPERVISOR', 'OWNER']).exists():
                user_companies = user.company_memberships.filter(role__in=['SUPERVISOR', 'OWNER']).values_list('company_id', flat=True)
                if item.branch.company_id not in user_companies:
                    return Response(
                        {'error': 'You do not have permission to modify this item'}, 
                        status=status.HTTP_403_FORBIDDEN
                    )
            else:
                user_branches = user.company_memberships.values_list('branch_id', flat=True)
                if item.branch_id not in user_branches:
                    return Response(
                        {'error': 'You do not have permission to modify this item'}, 
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # Update the original stock quantity
            try:
                item.update_original_stock(new_original_stock)
                serializer = ItemSerializer(item)
                return Response({
                    'message': f'Original stock quantity updated to {new_original_stock}',
                    'item': serializer.data
                })
            except ValueError as e:
                return Response(
                    {'error': str(e)}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            return Response(
                {'error': f'Error updating original stock: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class AddStockView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, pk):
        from .models import Item, Transaction
        try:
            item = Item.objects.get(pk=pk)
        except Item.DoesNotExist:
            return Response({'error': 'Item not found'}, status=404)
        quantity = int(request.data.get('quantity', 0))
        notes = request.data.get('notes', '')
        if quantity <= 0:
            return Response({'error': 'Quantity must be positive'}, status=400)
        item.stock_quantity += quantity
        item.save()
        Transaction.objects.create(
            item=item,
            user=request.user,
            branch=item.branch,
            transaction_type='ADD_STOCK',
            quantity=quantity,
            notes=notes or 'Stock added'
        )
        from .serializers import ItemSerializer
        return Response(ItemSerializer(item).data)

class RemoveStockView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, pk):
        from .models import Item, Transaction
        try:
            item = Item.objects.get(pk=pk)
        except Item.DoesNotExist:
            return Response({'error': 'Item not found'}, status=404)
        quantity = int(request.data.get('quantity', 0))
        notes = request.data.get('notes', '')
        if quantity <= 0:
            return Response({'error': 'Quantity must be positive'}, status=400)
        if item.stock_quantity < quantity:
            return Response({'error': 'Not enough stock to remove'}, status=400)
        item.stock_quantity -= quantity
        item.save()
        Transaction.objects.create(
            item=item,
            user=request.user,
            branch=item.branch,
            transaction_type='REMOVE_STOCK',
            quantity=quantity,
            notes=notes or 'Stock removed'
        )
        from .serializers import ItemSerializer
        return Response(ItemSerializer(item).data)

class TransactionReceiptView(RetrieveAPIView):
    """Endpoint to retrieve a detailed receipt for a transaction by its ID."""
    queryset = Transaction.objects.select_related('item', 'item__category', 'branch', 'branch__company', 'user')
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def get(self, request, *args, **kwargs):
        """Return a detailed receipt for the transaction."""
        return self.retrieve(request, *args, **kwargs)

class BranchStatisticsView(APIView):
    """Endpoint for getting branch transaction statistics with time filtering."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Get filter parameters
        period = request.query_params.get('period', 'all')  # yesterday, month, year, all
        company_id = request.query_params.get('company')
        
        # Calculate date range based on period
        now = timezone.now()
        if period == 'yesterday':
            start_date = now - timedelta(days=1)
            end_date = now
        elif period == 'month':
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        elif period == 'year':
            start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        else:  # 'all'
            start_date = None
            end_date = None

        # Build queryset based on user permissions
        user = request.user
        if user.global_user_level == 'DEVELOPER':
            # Developer can see all branches
            branches = Branch.objects.all()
        else:
            # Company owners/supervisors can only see their company's branches
            if company_id:
                branches = Branch.objects.filter(company_id=company_id)
            else:
                # Get user's company memberships
                user_companies = Company.objects.filter(members__user=user)
                branches = Branch.objects.filter(company__in=user_companies)

        # Get transaction statistics for each branch
        branch_stats = []
        for branch in branches:
            # Base transaction queryset for this branch
            transactions = Transaction.objects.filter(branch=branch)
            
            # Apply date filter if specified
            if start_date and end_date:
                transactions = transactions.filter(timestamp__range=[start_date, end_date])
            
            # Calculate statistics
            total_transactions = transactions.count()
            withdrawals = transactions.filter(transaction_type='WITHDRAW').count()
            returns = transactions.filter(transaction_type='RETURN').count()
            
            # Get unique users who made transactions
            unique_users = transactions.values('user').distinct().count()
            
            # Get most active items (top 5)
            top_items = transactions.values('item__name').annotate(
                count=Count('id')
            ).order_by('-count')[:5]
            
            branch_stats.append({
                'branch_id': branch.id,
                'branch_name': branch.name,
                'company_name': branch.company.name,
                'total_transactions': total_transactions,
                'withdrawals': withdrawals,
                'returns': returns,
                'unique_users': unique_users,
                'top_items': [
                    {'item_name': item['item__name'], 'transaction_count': item['count']}
                    for item in top_items
                ],
                'period': period,
                'date_range': {
                    'start': start_date.isoformat() if start_date else None,
                    'end': end_date.isoformat() if end_date else None
                }
            })
        
        # Sort by total transactions (descending)
        branch_stats.sort(key=lambda x: x['total_transactions'], reverse=True)
        
        return Response({
            'statistics': branch_stats,
            'period': period,
            'total_branches': len(branch_stats),
            'summary': {
                'total_transactions': sum(stat['total_transactions'] for stat in branch_stats),
                'total_withdrawals': sum(stat['withdrawals'] for stat in branch_stats),
                'total_returns': sum(stat['returns'] for stat in branch_stats),
                'total_unique_users': len(set(
                    user_id for stat in branch_stats 
                    for user_id in range(stat['unique_users'])
                ))
            }
        })
