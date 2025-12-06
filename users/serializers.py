from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserSettings

class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        fields = ['length_unit', 'area_unit', 'volume_unit', 'mass_unit']

class UserSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    
    # Include settings as a nested field
    settings = UserSettingsSerializer(read_only=False, required=False)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'first_name', 'last_name', 'settings')

    def create(self, validated_data):
        # Extract settings data if present
        settings_data = validated_data.pop('settings', {})
        
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        
        # Settings are auto-created by signal, so we just update them if provided
        if settings_data:
            # Access the auto-created settings instance
            user_settings = user.settings 
            for attr, value in settings_data.items():
                setattr(user_settings, attr, value)
            user_settings.save()
            
        return user

    def update(self, instance, validated_data):
        # Handle nested update for settings
        settings_data = validated_data.pop('settings', None)
        
        # Update User fields
        for attr, value in validated_data.items():
            if attr == 'password':
                instance.set_password(value)
            else:
                setattr(instance, attr, value)
        instance.save()

        # Update Settings fields
        if settings_data:
            user_settings = instance.settings
            for attr, value in settings_data.items():
                setattr(user_settings, attr, value)
            user_settings.save()

        return instance