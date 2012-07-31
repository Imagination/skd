from django.db import models

class User(models.Model):
    name = models.CharField(max_length = 200, blank=False)
    fullname = models.CharField(max_length = 200)
    comment = models.TextField(blank=True)

    def __unicode__(self):
        return "%s (%s)" % (self.name, self.fullname)

class Key(models.Model):
    user = models.ForeignKey(User)
    name = models.CharField(max_length = 200,blank=False)
    key = models.TextField(
        help_text="Public key in form 'ssh-dss AAA(...)'" \
            "or 'ssh-rsa AAA(...)'. DSA-Keys are recommended.",
        blank=False
    )
    comment = models.TextField(blank=True)

    def __unicode__(self):
        return "%s - %s" % (self.user.name, self.name)

class UserGroup(models.Model):
    name = models.CharField(max_length = 200, blank=False)
    comment = models.TextField(blank=True)

    def __unicode__(self):
        return self.name

class UserInGroup(models.Model):
    group = models.ForeignKey(UserGroup)
    user = models.ForeignKey(User)

    class Meta:
        unique_together = ("group","user")

    def __unicode__(self):
        return "%s <=> %s" % (self.group.name, self.user.name)

class Host(models.Model):
    name = models.CharField(max_length = 200, blank=False)
    fqdn = models.CharField(max_length = 200, blank=False)
    comment = models.TextField(blank=True)

    def __unicode__(self):
        return "%s (%s)" % (self.name, self.fqdn)

class HostGroup(models.Model):
    name = models.CharField(max_length = 200, blank=False)
    comment = models.TextField()

    def __unicode__(self):
        return self.name

class HostInGroup(models.Model):
    group = models.ForeignKey(HostGroup)
    host = models.ForeignKey(Host)

    class Meta:
        unique_together = ("group", "host")
    
    def __unicode__(self):
        return "%s <=> %s" % (self.group.name, self.host.name)

class UserGroupInHostGroup(models.Model):
    usergroup = models.ForeignKey(UserGroup)
    hostgroup = models.ForeignKey(HostGroup)

    class Meta:
        unique_together = ("usergroup", "hostgroup")

    def __unicode__(self):
        return "%s <=> %s" % (self.usergroup.name, self.hostgroup.name)
