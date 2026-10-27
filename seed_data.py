import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils import timezone

from chat.models import Message, Room  # غيّر "chat" لو اسم الـ app عندك مختلف

random.seed(42)
User = get_user_model()
NOW = timezone.now()

if Room.objects.filter(client_name__startswith="seed-").exists():
    raise SystemExit("seed data already exists - delete it first")

GUEST_LINES = [
    "السلام عليكم، عايز أسأل عن المنتج ده",
    "هل متوفر بلون تاني؟",
    "السعر شامل التوصيل؟",
    "Hello, is this still available?",
    "ممكن تفاصيل الضمان؟",
    "طلبي اتأخر، ممكن تتابعوا؟",
    "شكرًا جدًا على المساعدة",
]
STAFF_LINES = [
    "أهلاً بحضرتك، اتفضل",
    "المنتج متوفر وبيتوصل خلال 3 أيام",
    "السعر شامل التوصيل",
    "هراجع الطلب وأرد عليك حالًا",
]


def get_agent(key, name):
    field = User.USERNAME_FIELD
    value = f"{key}@example.com" if field == "email" else key
    user = User.objects.filter(**{field: value}).first()
    if user:
        return user
    has_name = any(f.name == "name" for f in User._meta.get_fields())
    extra = {"name": name} if has_name else {}
    return User.objects.create_user(**{field: value}, password="Test12345!", **extra)


def display(user):
    return getattr(user, "name", "") or str(user)


admin = User.objects.filter(is_superuser=True).first()
agent_b = get_agent("agent2", "Agent Two")


def make_room(label, agent, status, age_hours=1, guest=0, unread=0, staff=0):
    room = Room.objects.create(
        client_name=f"seed-{label}",
        agent=agent,
        status=status,
        url="https://example.com/product/1",
    )
    msgs = [
        Message(
            room=room,
            body=random.choice(GUEST_LINES),
            sent_by=room.client_name,
            is_read=(i < guest - unread),  # القديمة مقروءة، والأحدث غير مقروءة
        )
        for i in range(guest)
    ]
    if agent:
        msgs += [
            Message(
                room=room,
                body=random.choice(STAFF_LINES),
                sent_by=display(agent),
                created_by=agent,
            )
            for _ in range(staff)
        ]
    Message.objects.bulk_create(msgs, batch_size=500)

    # auto_now_add بيكتب الوقت الحالي، فنعدّل التواريخ بعد الإنشاء
    start = NOW - timedelta(hours=age_hours)
    for i, m in enumerate(msgs):
        m.created_at = start + timedelta(seconds=2 * i)
    Message.objects.bulk_update(msgs, ["created_at"], batch_size=500)

    last = start + timedelta(seconds=2 * len(msgs))
    Room.objects.filter(pk=room.pk).update(created_at=start, updated_at=last)
    return room


W, A, C = Room.WAITING, Room.ACTIVE, Room.CLOSED

# --- غرف الأدمن: حالات مختلفة ---
make_room("waiting-unread", admin, W, 1, guest=5, unread=5)
make_room("active-mixed", admin, A, 2, guest=8, unread=3, staff=4)
make_room("active-allread", admin, A, 2, guest=6, unread=0)
make_room("closed", admin, C, 48, guest=4, unread=0, staff=3)
make_room("empty", admin, W, 1)  # صفر رسايل
make_room("stale-active", admin, A, 72, guest=3, unread=1, staff=1)
make_room("stale-waiting", admin, W, 30, guest=2, unread=2)
make_room("stale-closed", admin, C, 100, guest=2, unread=0, staff=1)
make_room("big", admin, A, 24, guest=3000, unread=500, staff=1000)  # 4000 رسالة

# --- غرف من غير agent (للـ Q: agent فاضي أو closed) ---
make_room("guest-unassigned-1", None, W, 1, guest=2, unread=2)
make_room("guest-unassigned-2", None, W, 5, guest=1, unread=1)
make_room("guest-unassigned-closed", None, C, 60, guest=3, unread=0)

# --- غرف موظف تاني (اختبار IDOR) ---
make_room("b-waiting", agent_b, W, 1, guest=3, unread=3)
make_room("b-active", agent_b, A, 3, guest=5, unread=2, staff=2)
make_room("b-closed", agent_b, C, 50, guest=2, unread=0, staff=1)

# --- 40 غرفة عشوائية للأدمن (bulk-status وpagination) ---
for i in range(40):
    g = random.randint(0, 6)
    make_room(
        f"bulk-{i:02d}", admin, random.choice([W, A, C]),
        age_hours=random.randint(1, 200),
        guest=g, unread=random.randint(0, g), staff=random.randint(0, 3),
    )

# --- ملخص ---
rows = (
    Room.objects.filter(client_name__startswith="seed-")
    .exclude(client_name__startswith="seed-bulk")
    .annotate(
        total=Count("messages"),
        unread=Count("messages", filter=Q(messages__is_read=False)),
    )
    .order_by("client_name")
)
for r in rows:
    print(f"{r.id}  {r.client_name:<26} {r.status:<8} agent={r.agent_id}  msgs={r.total}  unread={r.unread}")
print("agent2 login:", getattr(agent_b, User.USERNAME_FIELD), "/ Test12345!")
print("total seed rooms:", Room.objects.filter(client_name__startswith="seed-").count())