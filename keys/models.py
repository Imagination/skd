from django.db import models
import django.contrib.auth.models

class User(models.Model):
    """
    Stores a SSH-user record
    """

    name = models.CharField(max_length = 200, blank=False)
    fullname = models.CharField(max_length = 200)
    comment = models.TextField(blank=True)

    class Meta:
        permissions = (
            ("list_users", "Can list all users"),
        )

    def __unicode__(self):
        return "%s (%s)" % (self.name, self.fullname)

class Key(models.Model):
    """
    Stores keys of a SSH-User. Relates to :model:`keys.User`
    """

    user = models.ForeignKey(User)
    name = models.CharField(max_length = 200,blank=False)
    key = models.TextField(
        help_text="Public key in form 'ssh-dss AAA(...)'" \
            "or 'ssh-rsa AAA(...)'. DSA-Keys are recommended.",
        blank=False
    )
    comment = models.TextField(blank=True)

    class Meta:
        permissions = (
            ("list_users_keys", "Can list all keys of every user"),
        )

    def __unicode__(self):
        return "%s - %s" % (self.user.name, self.name)

class UserGroup(models.Model):
    """
    Groups of users.
    """
    name = models.CharField(max_length = 200, blank=False)
    comment = models.TextField(blank=True)

    class Meta:
        permissions = (
            ("list_usergroups", "Can list all usergroups"),
        )

    def __unicode__(self):
        return self.name

class UserInGroup(models.Model):
    """
    Binds users to usergroups. Relates to :model:`keys.User` and
    :model:`keys.UserGroup
    """
    group = models.ForeignKey(UserGroup)
    user = models.ForeignKey(User)

    class Meta:
        unique_together = ("group","user")
        permissions = (
            (
                "list_users_in_usergroups",
                "Can see which users are in which usergroups"
            ),
        )

    def __unicode__(self):
        return "%s <=> %s" % (self.group.name, self.user.name)

class Host(models.Model):
    """
    SSH-aware hosts.
    """

    name = models.CharField(max_length = 200, blank = False)
    fqdn = models.CharField(max_length = 200, blank = False)
    user = models.CharField(max_length = 200, blank = False)
    comment = models.TextField(blank=True)

    class Meta:
        permissions = (
            ("list_hosts", "Can list all hosts"),
            ("setup_host", "Write skd public key to host")
        )

    def __unicode__(self):
        return "%s (%s)" % (self.name, self.fqdn)

class HostGroup(models.Model):
    """
    Groups of hosts.
    """

    name = models.CharField(max_length = 200, blank=False)
    comment = models.TextField(blank = True)

    class Meta:
        permissions = (
            ("list_hostgroups", "Can list all hostgroups"),
        )

    def __unicode__(self):
        return self.name

class HostInGroup(models.Model):
    """
    Binds hosts to hostgroups. Relates to :model:`keys.Host` and
    :model:`keys.HostGroup`
    """

    group = models.ForeignKey(HostGroup)
    host = models.ForeignKey(Host)

    class Meta:
        unique_together = ("group", "host")
        permissions = (
            (
                "list_hosts_in_hostgroups",
                "Can see which hosts are in which hostgroups"
            ),
        )
    
    def __unicode__(self):
        return "%s <=> %s" % (self.group.name, self.host.name)

class UserGroupInHostGroup(models.Model):
    """
    Assings usergroups to hostgroups, meaning that all users in the
    usergroup can login into all hosts in the hostgroup.

    Relates to :model:`keys.UserGroup` and :model:`keys.HostGroup`
    """
    usergroup = models.ForeignKey(UserGroup)
    hostgroup = models.ForeignKey(HostGroup)

    class Meta:
        unique_together = ("usergroup", "hostgroup")
        permissions = (
            (
                "list_usergroups_in_hostgroups",
                "Can see which hostgroups are assigned to which usergroups"
            ),
        )

    def __unicode__(self):
        return "%s <=> %s" % (self.usergroup.name, self.hostgroup.name)

class ActionLog(models.Model):
    """
    Logs changes in the UI for an audit trail.

    Has a relation to :model:`auth.User`
    """

    timestamp = models.DateTimeField(null = False)
    user = models.ForeignKey(django.contrib.auth.models.User)
    action = models.CharField(max_length = 100, blank = False)
    objectid = models.IntegerField(null = True)
    objectid2 = models.IntegerField(null = True)
    comment = models.TextField(blank = True)

    class Meta:
        permissions = (
            (
                "list_actionlog",
                "The user can see the action log."
            ),
        )

class ApplyLog(models.Model):
    """
    Logs hosts, that are affected by changes in the UI.
    These hosts are taken into account, when the user clicks on "Apply".
    """

    host = models.ForeignKey(Host)

    class Meta:
        permissions = (
            (
                "can_apply",
                "The user can apply key-deployment"
                ),
            )

class Configuration(models.Model):
    """
    Internal configuration of skd.

    Currently available keys:

    ssh_key_private: Private SSH-Key blob in base64
    ssh_key_public: Public SSH-Key blob in base64
    """

    key = models.CharField(max_length = 100, blank = False, unique = True)
    value = models.TextField(blank = True)