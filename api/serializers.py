from rest_framework import serializers
from .models import CustomUser, Item, Transaction
import logging

logger = logging.getLogger(__name__)

class CustomUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    username = serializers.CharField(required=False)

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'id_number', 'password', 'first_name', 'last_name', 'email', 'user_level', 'department', 'contact_number']
        read_only_fields = ['id']
        extra_kwargs = {
            'email': {'required': False},
            'department': {'required': False},
            'contact_number': {'required': False},
        }

    def create(self, validated_data):
        # Use id_number as username if not provided
        if 'username' not in validated_data:
            validated_data['username'] = validated_data['id_number']
        
        # Set a default email if not provided
        if 'email' not in validated_data:
            validated_data['email'] = f"{validated_data['id_number']}@example.com"

        password = validated_data.pop('password')
        user = CustomUser(**validated_data)
        user.set_password(password)
        user.save()
        return user

class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'id_number', 'username', 'first_name', 'last_name', 'email', 
                 'user_level', 'department', 'contact_number', 'is_active', 'date_joined']
        read_only_fields = ['id', 'date_joined']

class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = ['id', 'item_id', 'name', 'description', 'category', 'status', 'qr_code', 'created_at', 'updated_at']
        read_only_fields = ['id', 'qr_code', 'created_at', 'updated_at']

class TransactionSerializer(serializers.ModelSerializer):
    item = ItemSerializer(read_only=True)
    user = CustomUserSerializer(read_only=True)
    item_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Transaction
        fields = ['id', 'item', 'item_id', 'user', 'transaction_type', 'timestamp', 'notes']
        read_only_fields = ['id', 'timestamp']

    def validate(self, data):
        """
        Validate the transaction data.
        """
        try:
            item = Item.objects.get(id=data['item_id'])
            
            # Validate withdrawal
            if data['transaction_type'] == 'WITHDRAW':
                if item.status != 'AVAILABLE':
                    raise serializers.ValidationError({
                        'item_id': f'This item cannot be withdrawn because it is currently {item.status.lower()}'
                    })
                    
            # Validate return
            elif data['transaction_type'] == 'RETURN':
                if item.status != 'IN_USE':
                    raise serializers.ValidationError({
                        'item_id': f'This item cannot be returned because it is currently {item.status.lower()}'
                    })
            
            return data
            
        except Item.DoesNotExist:
            raise serializers.ValidationError({
                'item_id': 'Item not found'
            })

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['user'] = user
        
        item_id = validated_data.pop('item_id')
        try:
            item = Item.objects.get(id=item_id)
            validated_data['item'] = item
            return super().create(validated_data)
        except Item.DoesNotExist:
            raise serializers.ValidationError({
                'item_id': 'Item not found'
            })

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'id_number', 'first_name', 'last_name', 'email', 'department', 'contact_number', 'qr_code']
        read_only_fields = ['id', 'id_number', 'qr_code']

    def validate_email(self, value):
        if CustomUser.objects.exclude(pk=self.instance.pk).filter(email=value).exists():
            raise serializers.ValidationError("This email is already in use.")
        return value
