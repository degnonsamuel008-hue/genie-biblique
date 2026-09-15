from django.contrib import admin
from .models import UserProfile,Badge,UserBadge

admin.site.register(UserProfile)
admin.site.register(Badge)
admin.site.register(UserBadge)

