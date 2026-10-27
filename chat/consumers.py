import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Message, Room
from .serialization import MessageSerializer
import logging

logger = logging.getLogger("chat")


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.chat_group_name = f"chat_{self.room_id}"

        await self.channel_layer.group_add(self.chat_group_name, self.channel_name)
        await self.accept()
        if self.scope["user"].is_authenticated:
            logger.info(
                "user authenticated : name -> %s , room id -> %s",
                self.scope["user"].name,
                self.room_id,
            )
        else:
            logger.info("user not authenticated : room id -> %s", self.room_id)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.chat_group_name, self.channel_name)
        logger.info(
            "room closed : reason -> %s , room id -> %s", close_code, self.room_id
        )
        if not self.scope["user"].is_authenticated:
            await self.close_room(self.room_id)

    async def receive(self, text_data=None):
        data = json.loads(text_data)
        message = data.get("message", "")
        logger.debug("message length : %d , room id : %s", len(message), self.room_id)
        name = data.get("name", "")
        await self.save_message(self.room_id, name, message)

        await self.channel_layer.group_send(
            self.chat_group_name,
            {"type": "chat_message", "message": message, "name": name},
        )

    @database_sync_to_async
    def save_message(self, room_id, sent_by, message):
        data = MessageSerializer(data={"body": message, "sent_by": sent_by})
        if not data.is_valid():
            logger.warning(
                "invalid message data room=%s errors=%s", room_id, data.errors
            )
            return

        try:
            room = Room.objects.get(id=room_id)
        except Room.DoesNotExist:
            logger.warning("room not found room=%s", room_id)
            return

        user = self.scope["user"]
        data.save(room=room, created_by=user if user.is_authenticated else None)

    async def chat_message(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "message",
                    "message": event["message"],
                    "name": event["name"],
                }
            )
        )

    @database_sync_to_async
    def close_room(self, room_id):
        room = Room.objects.get(id=room_id)
        room.status = Room.CLOSED
        room.save()
        logger.info("room closed : room id -> %s", self.room_id)
