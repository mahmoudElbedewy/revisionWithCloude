from django.db import models
from account.models import User
import uuid
from datetime import timedelta
from django.utils import timezone


class RoomQuerySet(models.QuerySet):
    def waiting(self):
        return self.filter(status=Room.WAITING)

    def stale(self, hours=24):
        cutoff = timezone.now() - timedelta(hours=hours)
        return self.filter(updated_at__lt=cutoff)


class Message(models.Model):
    body = models.TextField()
    sent_by = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, blank=True, null=True, on_delete=models.SET_NULL
    )
    is_read = models.BooleanField(default=False)
    room = models.ForeignKey("Room", on_delete=models.CASCADE, related_name="messages")

    class Meta:
        ordering = ("created_at",)

    def __str__(self):
        return f"{self.sent_by}: {self.body}"


class Room(models.Model):
    WAITING = "waiting"
    ACTIVE = "active"
    CLOSED = "closed"

    CHOICES_STATUS = (
        (WAITING, "Waiting"),
        (ACTIVE, "Active"),
        (CLOSED, "Closed"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    client_name = models.CharField(max_length=255)
    agent = models.ForeignKey(
        User, related_name="rooms", blank=True, null=True, on_delete=models.SET_NULL
    )
    url = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=CHOICES_STATUS, default=WAITING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["status"], name="room_status_idx")]
        constraints = [
            models.UniqueConstraint(
                fields=["client_name", "url"],
                condition=~models.Q(status="closed"),
                name="one_open_room_per_client_url",
            )
        ]

    def __str__(self):
        return f"{self.client_name} - {self.id}"

    objects = RoomQuerySet.as_manager()
