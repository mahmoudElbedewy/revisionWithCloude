from django.contrib import admin
from .models import Room , Message

class MessageInline(admin.TabularInline):
    model = Message
    extra = 0 
    readonly_fields = ('created_at' , )


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('id', 'client_name', 'status', 'agent', 'updated_at')
    list_filter = ('status',)
    search_fields = ('client_name', 'id')
    inlines = [MessageInline]
    readonly_fields = ('created_at' , 'updated_at')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'room', 'sent_by', 'body', 'is_read', 'created_at')
    list_filter = ('is_read',)
    search_fields = ('body', 'sent_by')
    readonly_fields = ('created_at',)