from rest_framework import generics, status, permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound, ValidationError, PermissionDenied
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import authenticate
from .models import CustomUser, Item, Transaction
from .serializers import (
    CustomUserSerializer,
    AdminUserSerializer,
    UserProfileSerializer,
    ItemSerializer,
    TransactionSerializer
)
from django.shortcuts import get_object_or_404
import uuid
from rest_framework_simplejwt.tokens import RefreshToken
import logging
from rest_framework.decorators import action
from django.db.models import Q

logger = logging.getLogger(__name__)

class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.user_level == 'ADMIN'

class IsStaffUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.user_level in ['ADMIN', 'STAFF']

class RegisterUserView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = []  # Allow unauthenticated access
    authentication_classes = []  # No authentication required for registration

    def create(self, request, *args, **kwargs):
        try:
            logger.info(f"Registration attempt with data: {request.data}")

            required_fields = ['id_number', 'password', 'first_name', 'last_name']
            for field in required_fields:
                if not request.data.get(field):
                    raise ValidationError(f"{field} is required")

            id_number = request.data.get('id_number')
            if not id_number.isdigit():
                raise ValidationError("ID number must contain only digits")

            if CustomUser.objects.filter(id_number=id_number).exists():
                raise ValidationError("This ID number is already registered")

            # Set default user level for public registration
            request.data['user_level'] = 'USER'
            
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()

            # Set password
            user.set_password(request.data.get('password'))
            user.save()

            # Generate QR code
            user.generate_qr()
            user.save()

            # Create tokens for immediate login
            refresh = RefreshToken.for_user(user)
            
            response_data = {
                'status': 'success',
                'message': 'User registered successfully',
                'data': {
                    'id': user.id,
                    'id_number': user.id_number,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'qr_code': user.qr_code.url if user.qr_code else None,
                    'tokens': {
                        'access': str(refresh.access_token),
                        'refresh': str(refresh)
                    }
                }
            }
            
            logger.info(f"User registered successfully: {user.id_number}")
            return Response(response_data, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            logger.error(f"Validation error during registration: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Unexpected error during registration: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Error creating account. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserLookupView(APIView):
    def post(self, request):
        id_number = request.data.get('id_number')
        password = request.data.get('password')

        if not id_number or not password:
            return Response({
                'status': 'error',
                'message': 'ID number and password are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = authenticate(username=id_number, password=password)
            
            if user is None:
                return Response({
                    'status': 'error',
                    'message': 'Invalid ID number or password'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'status': 'success',
                'message': 'Login successful',
                'data': {
                    'id': user.id,
                    'id_number': user.id_number,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'user_level': user.user_level,
                    'qr_code': user.qr_code.url if user.qr_code else None,
                    'tokens': {
                        'access': str(refresh.access_token),
                        'refresh': str(refresh)
                    }
                }
            })
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

class QRLoginView(APIView):
    permission_classes = []  # Allow unauthenticated access
    authentication_classes = []  # No authentication required for this endpoint
    
    def post(self, request):
        login_token = request.data.get('login_token')
        logger.info(f"QR login attempt with token: {login_token}")
        
        if not login_token:
            logger.warning("No login token provided")
            return Response({
                'status': 'error',
                'message': 'Login token is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = CustomUser.objects.get(login_token=login_token)
            logger.info(f"Found user with token: {user.id_number}")
            
            refresh = RefreshToken.for_user(user)
            
            user.save()
            
            response_data = {
                'status': 'success',
                'message': 'Login successful',
                'data': {
                    'id': user.id,
                    'id_number': user.id_number,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'user_level': user.user_level,
                    'qr_code': user.qr_code.url if user.qr_code else None,
                    'tokens': {
                        'access': str(refresh.access_token),
                        'refresh': str(refresh)
                    }
                }
            }
            logger.info(f"Successful QR login for user: {user.id_number}")
            return Response(response_data)
            
        except ObjectDoesNotExist:
            logger.warning(f"Invalid login token: {login_token}")
            return Response({
                'status': 'error',
                'message': 'Invalid login token. Please try again or contact support.'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error during QR login: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response({
            'status': 'success',
            'data': serializer.data
        })

    def patch(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'status': 'success',
                'message': 'Profile updated successfully',
                'data': serializer.data
            })
        return Response({
            'status': 'error',
            'message': 'Invalid data provided',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if self.request.user.user_level == 'ADMIN':
            return AdminUserSerializer
        return CustomUserSerializer

    @action(detail=False, methods=['get', 'patch'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        if request.method == 'GET':
            serializer = UserProfileSerializer(request.user)
            return Response(serializer.data)
        
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsStaffUser()]
        return [permissions.IsAuthenticated()]

    @action(detail=False, methods=['get'])
    def available(self, request):
        available_items = Item.objects.filter(status='AVAILABLE')
        serializer = self.get_serializer(available_items, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.query_params.get('q', '')
        items = Item.objects.filter(
            Q(name__icontains=query) |
            Q(item_id__icontains=query) |
            Q(description__icontains=query)
        )
        serializer = self.get_serializer(items, many=True)
        return Response(serializer.data)

class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_level in ['ADMIN', 'STAFF']:
            return Transaction.objects.all()
        return Transaction.objects.filter(user=user)

    def create(self, request, *args, **kwargs):
        logger.info(f"Creating transaction with data: {request.data}")
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            try:
                transaction = serializer.save()
                logger.info(f"Transaction created successfully: {transaction.id}")
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except serializers.ValidationError as e:
                logger.error(f"Validation error while creating transaction: {str(e)}")
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.error(f"Error creating transaction: {str(e)}")
                return Response(
                    {'error': 'An error occurred while processing the transaction'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        logger.error(f"Invalid transaction data: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def my_transactions(self, request):
        transactions = Transaction.objects.filter(user=request.user)
        serializer = self.get_serializer(transactions, many=True)
        return Response(serializer.data)
