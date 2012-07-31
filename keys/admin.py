from keys.models import *
from django.contrib import admin

admin.site.register(User)
admin.site.register(Key)
admin.site.register(UserGroup)
admin.site.register(UserInGroup)
admin.site.register(Host)
admin.site.register(HostGroup)
admin.site.register(HostInGroup)
admin.site.register(UserGroupInHostGroup)
