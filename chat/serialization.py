from rest_framework import serializers
from .models import Message, Room


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["id", "body", "sent_by", "created_by", "is_read", "created_at"]
        read_only_fields = ["created_by"]

    def validate_body(self, value):
        if len(value) > 1000:
            raise serializers.ValidationError(
                "الرسالة لازم تكون اقل من 1000 حرف على الاكثر"
            )
        return value
    def validate(self , attrs):
        request = self.context.get("request")
        
        is_read = attrs.get("is_read")
        
        if is_read is True and request and not request.user.is_authenticated:
            raise serializers.ValidationError("غير مسموح لك بتعديل حالة القراءة.")
            
        return attrs


class RoomSerializer(serializers.ModelSerializer):
    unread_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Room
        fields = ["id", "client_name", "status", "updated_at", "unread_count"]
        read_only_fields = ["updated_at", "unread_count"]


class RoomStatusItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=Room.CHOICES_STATUS)
