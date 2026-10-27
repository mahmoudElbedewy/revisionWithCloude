from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Message, Room
from .serialization import RoomSerializer, MessageSerializer, RoomStatusItemSerializer
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.core.cache import cache
import logging
from django.db.models import Count, Q
from django.utils import timezone

loggings = logging.getLogger("chat")


class RoomListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        else:
            return [AllowAny()]

    # to create and fetch gests rooms
    def post(self, request):
        room_id = request.data.get("id", "")
        client_name = request.data.get("client_name", "")
        url = request.data.get("url", "")
        room, created = Room.objects.get_or_create(
            id=room_id, defaults={"client_name": client_name, "url": url}
        )
        serialized_data = RoomSerializer(room)
        return Response(serialized_data.data)

    # to retrieve agent chats
    def get(self, request):
        rooms = (
            Room.objects.only("id", "client_name", "status", "updated_at")
            .filter(agent=request.user)
            .annotate(
                unread_count=Count(
                    "messages",
                    filter=Q(
                        messages__is_read=False,
                        messages__created_by__isnull=True,
                    ),
                )
            )
        )
        data = RoomSerializer(rooms, many=True)
        return Response(data.data)


class MessageListCreateView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, room_id):
        cache_key = f"room_messages_{room_id}"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            loggings.debug("cache hit: %s", cache_key)
            return Response(cached_data)

        loggings.debug("cache miss: %s", cache_key)
        room = get_object_or_404(Room, id=room_id)
        messages = room.messages.all()

        serialzed_data = MessageSerializer(
            messages, many=True, context={"request": request}
        )
        cached_data = cache.set(cache_key, serialzed_data.data, 60)

        return Response(serialzed_data.data)

    def post(self, request, room_id):
        room = get_object_or_404(Room, id=room_id)
        data = MessageSerializer(data=request.data, context={"request": request})
        if data.is_valid():
            if request.user.is_authenticated:
                data.save(room=room, created_by=request.user, sent_by=request.user.name)
            else:
                data.save(room=room)
            return Response(data.data)
        else:
            loggings.warning(
                "invalid message data room=%s errors=%s", room_id, data.errors
            )
            return Response(raise_exception=True)


class MarkAsReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, room_id):
        room = get_object_or_404(Room, id=room_id)
        updated = Message.objects.filter(
            room=room, is_read=False, created_by__isnull=True
        ).update(is_read=True)

        if updated:
            cache.delete(f"room_messages_{room_id}")
            loggings.info("marked %s messages as read room=%s", updated, room_id)
        return Response({"status": "marked as read", "updated": updated})


class HasUnreadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, room_id):
        room = get_object_or_404(Room, id=room_id)

        has_unread = room.messages.filter(
            is_read=False, created_by__isnull=True
        ).exists()
        return Response({"has_unread": has_unread})


class RoomSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rooms = Room.objects.filter(agent=request.user).values("id", "status")
        return Response(list(rooms))


class BulkMessageCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, room_id):
        room = get_object_or_404(Room, id=room_id)
        serializer = MessageSerializer(
            data=request.data, context={"request": request}, many=True
        )
        if serializer.is_valid():
            messages = [
                Message(
                    **{
                        **item,
                        "room": room,
                        "created_by": request.user,
                        "sent_by": request.user.name,
                    }
                )
                for item in serializer.validated_data
            ]
            Message.objects.bulk_create(messages)
            cache.delete(f"room_messages_{room_id}")
            return Response({"created": len(messages)}, status=status.HTTP_201_CREATED)
        else:
            loggings.warning(
                "invalid bulk messages room=%s errors=%s", room_id, serializer.errors
            )
            return Response(raise_exception=True)


class BulkRoomStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RoomStatusItemSerializer(data=request.data, many=True)

        if not serializer.is_valid():
            loggings.warning("invalid bulk room status errors=%s", serializer.errors)
            return Response(raise_exception=True)

        status_by_id = {
            item["id"]: item["status"] for item in serializer.validated_data
        }

        rooms = list(
            Room.objects.only("id", "status", "updated_at").filter(
                id__in=status_by_id.keys(), agent=request.user
            )
        )

        now = timezone.now()
        for room in rooms:
            room.status = status_by_id[room.id]
            room.updated_at = now

        Room.objects.bulk_update(rooms, ["status", "updated_at"], batch_size=500)
        loggings.info("bulk updated %s rooms by user=%s", len(rooms), request.user.pk)
        return Response({"updated": len(rooms)}, status=status.HTTP_200_OK)
