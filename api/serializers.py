from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import CustomUser, Item, Transaction, Company, Branch, CompanyMembership, Category
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

class CompanySerializer(serializers.ModelSerializer):
    """Serializer for the Company model."""
    owner = serializers.StringRelatedField(read_only=True)
    logo = serializers.ImageField(required=False, allow_null=True)
    contact_info = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    location = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Company
        fields = ['id', 'name', 'owner', 'description', 'logo', 'contact_info', 'email', 'location', 'created_at']
        read_only_fields = ['id', 'owner', 'created_at']

class BranchSerializer(serializers.ModelSerializer):
    """Serializer for the Branch model."""
    company = serializers.StringRelatedField()
    company_name = serializers.CharField(source='company.name', read_only=True)
    manager_name = serializers.SerializerMethodField()

    class Meta:
        model = Branch
        fields = ['id', 'name', 'company', 'company_name', 'description', 'is_active', 'manager_name']

    def get_manager_name(self, obj):
        manager = CompanyMembership.objects.filter(
            branch=obj,
            role='BRANCH_MANAGER'
        ).first()
        return manager.user.username if manager else None

class CompanyMembershipSerializer(serializers.ModelSerializer):
    """Serializer for assigning users to companies."""
    branch = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(),
        required=False,
        allow_null=True
    )
    user_name = serializers.CharField(source='user.username', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True, allow_null=True)
    company = serializers.UUIDField(source='company.id', read_only=True)
    company_logo = serializers.ImageField(source='company.logo', read_only=True, allow_null=True)

    class Meta:
        model = CompanyMembership
        fields = ['id', 'user', 'company', 'role', 'branch', 'user_name', 'company_name', 'branch_name', 'company_logo']
        extra_kwargs = {
            'user': {'write_only': True},
            'company': {'write_only': False},
        }

    def validate(self, data):
        try:
            # Get the instance and company
            instance = self.instance
            company = instance.company if instance else None

            # Log validation data
            logger.info(f"Validating data: {data}")
            logger.info(f"Current instance: {instance.__dict__ if instance else None}")

            # Validate branch belongs to company if provided
            if 'branch' in data and data['branch']:
                branch = data['branch']
                if branch.company != company:
                    raise serializers.ValidationError({
                        'branch': f'Branch {branch.name} does not belong to company {company.name}.'
                    })

            # Get the role (from data or instance)
            role = data.get('role', instance.role if instance else None)
            branch = data.get('branch', instance.branch if instance else None)

            # Validate role and branch assignment rules
            if role == 'SUPERVISOR' and branch:
                raise serializers.ValidationError({
                    'branch': 'A Supervisor cannot be assigned to a specific branch.'
                })
            if role == 'BRANCH_MANAGER' and not branch:
                raise serializers.ValidationError({
                    'branch': 'A Branch Manager must be assigned to a branch.'
                })

            return data
        except Exception as e:
            logger.error(f"Error in validate: {str(e)}")
            raise

    def update(self, instance, validated_data):
        try:
            logger.info(f"Starting update with validated data: {validated_data}")
            
            # Get the new role and branch
            new_role = validated_data.get('role', instance.role)
            new_branch = validated_data.get('branch', instance.branch)
            
            # If changing to branch manager
            if new_role == 'BRANCH_MANAGER' and new_branch:
                logger.info(f"Handling branch manager assignment for branch: {new_branch.id}")
                
                # Find any existing manager for this branch
                existing_manager = CompanyMembership.objects.filter(
                    branch=new_branch,
                    role='BRANCH_MANAGER'
                ).exclude(id=instance.id).first()
                
                if existing_manager:
                    logger.info(f"Found existing manager: {existing_manager.user.username}")
                    existing_manager.role = 'USER'
                    existing_manager.save()
                    logger.info("Demoted existing manager to USER")

            # Update the instance
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            
            # Save the instance
            instance.save()
            logger.info(f"Successfully updated membership: {instance.id}")
            
            return instance
        except Exception as e:
            logger.error(f"Error in update: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Error args: {e.args}")
            raise

class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for the currently authenticated user's profile."""
    company_memberships = CompanyMembershipSerializer(many=True, read_only=True)
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    qr_code = serializers.ImageField(read_only=True, allow_null=True)

    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'first_name', 'last_name', 'email',
            'global_user_level', 'id_number', 'department', 'contact_number',
            'profile_picture', 'qr_code', 'company_memberships'
        ]

class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for new user registration."""
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['username', 'password', 'email', 'first_name', 'last_name', 'id_number']

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

class AdminUserSerializer(serializers.ModelSerializer):
    """Serializer for admins to manage user details."""
    memberships_display = serializers.SerializerMethodField()
    memberships = serializers.SerializerMethodField()
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    qr_code = serializers.ImageField(read_only=True, allow_null=True)

    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'first_name', 'last_name', 'email', 'global_user_level', 'id_number',
            'profile_picture', 'qr_code', 'memberships_display', 'memberships'
        ]

    def get_memberships_display(self, obj):
        # Return a list of strings like "Company (Role) - Branch"
        return [
            f"{m.company.name} ({m.role})" + (f" - {m.branch.name}" if m.branch else "")
            for m in obj.company_memberships.select_related('company', 'branch').all()
        ]

    def get_memberships(self, obj):
        # Return a list of dicts with company_name, branch_name, and role
        return [
            {
                'company_name': m.company.name,
                'branch_name': m.branch.name if m.branch else None,
                'role': m.role
            }
            for m in obj.company_memberships.select_related('company', 'branch').all()
        ]

class ItemSerializer(serializers.ModelSerializer):
    """Serializer for the Item model."""
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    photo = serializers.ImageField(required=False, allow_null=True)
    original_stock_quantity = serializers.IntegerField(read_only=True)
    item_id = serializers.CharField(read_only=True)

    class Meta:
        model = Item
        fields = [
            'id', 'name', 'item_id', 'branch', 'branch_name', 'description', 'category', 'category_name',
            'status', 'stock_quantity', 'original_stock_quantity', 'minimum_stock', 'barcode_number',
            'barcode', 'qr_code', 'photo', 'created_at', 'updated_at', 'created_by', 'created_by_username'
        ]
        read_only_fields = ['id', 'qr_code', 'barcode', 'created_at', 'updated_at', 'status', 'created_by', 'created_by_username', 'category_name', 'original_stock_quantity', 'item_id']

    def create(self, validated_data):
        # Set original_stock_quantity to stock_quantity if not provided
        if 'original_stock_quantity' not in validated_data or validated_data.get('original_stock_quantity', 0) == 0:
            validated_data['original_stock_quantity'] = validated_data.get('stock_quantity', 0)
        return super().create(validated_data)

class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for the Transaction model."""
    user_name = serializers.CharField(source='user.username', read_only=True)
    user_full_name = serializers.SerializerMethodField()
    user_id_number = serializers.CharField(source='user.id_number', read_only=True, allow_null=True)
    user_department = serializers.CharField(source='user.department', read_only=True, allow_null=True)
    user_level = serializers.CharField(source='user.global_user_level', read_only=True)
    item_name = serializers.CharField(source='item.name', read_only=True)
    item_id = serializers.CharField(source='item.item_id', read_only=True)
    item_category = serializers.SerializerMethodField()
    item_status = serializers.CharField(source='item.status', read_only=True)
    item_stock_quantity = serializers.IntegerField(source='item.stock_quantity', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    company_name = serializers.CharField(source='branch.company.name', read_only=True)
    company_contact_info = serializers.CharField(source='branch.company.contact_info', read_only=True, allow_null=True)
    company_email = serializers.EmailField(source='branch.company.email', read_only=True, allow_null=True)
    company_location = serializers.CharField(source='branch.company.location', read_only=True, allow_null=True)
    company_logo = serializers.ImageField(source='branch.company.logo', read_only=True, allow_null=True)
    reference_number = serializers.CharField(read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'user_name', 'user_full_name', 'user_id_number', 'user_department', 'user_level',
            'item', 'item_name', 'item_id', 'item_category', 'item_status', 'item_stock_quantity',
            'branch', 'branch_name', 'company_name', 'company_contact_info', 'company_email', 'company_location', 'company_logo',
            'transaction_type', 'quantity', 'timestamp', 'notes', 'reference_number'
        ]
        extra_kwargs = {
            'item': {'write_only': True},
            'branch': {'write_only': True},
        }

    def get_user_full_name(self, obj):
        """Get the user's full name or username if full name is not available."""
        # Check if first_name and last_name are valid (not empty, not "New QR", etc.)
        first_name = obj.user.first_name.strip() if obj.user.first_name else ""
        last_name = obj.user.last_name.strip() if obj.user.last_name else ""
        
        # Filter out invalid names like "New QR", empty strings, etc.
        valid_first_name = first_name if first_name and first_name.lower() not in ['new qr', ''] else ""
        valid_last_name = last_name if last_name and last_name.lower() not in ['new qr', ''] else ""
        
        if valid_first_name and valid_last_name:
            full_name = f"{valid_first_name} {valid_last_name}"
            return full_name
        elif valid_first_name:
            return valid_first_name
        else:
            return obj.user.username

    def get_item_category(self, obj):
        """Get the item category name, handling cases where category might be null."""
        if obj.item.category:
            return obj.item.category.name
        return 'Uncategorized'

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'company', 'branch', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
