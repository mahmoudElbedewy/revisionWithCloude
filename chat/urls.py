from django.urls import path
from .views import (
    MessageListCreateView,
    RoomListCreateView,
    MarkAsReadView,
    HasUnreadView,
    RoomSummaryView,
    BulkMessageCreateView,
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views


urlpatterns = [
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/rooms/", RoomListCreateView.as_view(), name="room-create"),
    path(
        "api/rooms/<uuid:room_id>/messages/",
        MessageListCreateView.as_view(),
        name="room-messages",
    ),
    path(
        "api/rooms/<uuid:room_id>/mark-read/",
        MarkAsReadView.as_view(),
        name="mark-read",
    ),
    path(
        "api/rooms/<uuid:room_id>/has-unread/",
        HasUnreadView.as_view(),
        name="has_unread",
    ),
    path("api/rooms/summary/", RoomSummaryView.as_view(), name="room_summary"),
    path(
        "api/rooms/<uuid:room_id>/messages/bulk/",
        BulkMessageCreateView.as_view(),
        name="bulk_create",
    ),
    path("rooms/bulk-status/", views.BulkRoomStatusView.as_view()),
]
