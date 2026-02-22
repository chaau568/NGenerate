from rest_framework import serializers
from .models import CharacterImage, CharacterVoice, IllustrationImage, Video

class CharacterImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CharacterImage
        fields = '__all__'

class CharacterVoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CharacterVoice
        fields = '__all__'

class IllustrationImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = IllustrationImage
        fields = '__all__'

class VideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Video
        fields = '__all__'