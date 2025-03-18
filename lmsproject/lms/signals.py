from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.db.utils import ProgrammingError
from .models import Role

@receiver(post_migrate)
def create_default_superuser(sender, **kwargs):
    try:
        User = get_user_model()
        if not User.objects.filter(is_superuser=True).exists():
            admin_role, created = Role.objects.get_or_create(role_name='admin')
            User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin',
                role=admin_role
            )
    except ProgrammingError:
        # Table doesn't exist yet, skip
        pass