from django.db import models
from django.conf import settings

class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=150)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, default='SYSTEM')
    is_read = models.BooleanField(default=False)
    link = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.username}: {self.title} [{'Read' if self.is_read else 'Unread'}]"


def send_notification(user, title, message, link='', notification_type='SYSTEM'):
    return Notification.objects.create(
        user=user,
        title=title,
        message=message,
        link=link,
        notification_type=notification_type
    )
