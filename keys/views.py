import StringIO
from datetime import datetime
import socket
from django.contrib.auth import models
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.template.context import RequestContext
from django.views.generic.base import TemplateView
from django.views.generic.edit import CreateView, UpdateView, DeleteView, \
    ModelFormMixin
from django.views.generic.list import ListView

from paramiko.client import SSHClient, AutoAddPolicy
from paramiko.dsskey import DSSKey
from paramiko.ssh_exception import AuthenticationException, SSHException
import sys
from skd import settings
from keys.models import User,Key, UserGroup, UserInGroup, HostInGroup, Host, \
    HostGroup, UserGroupInHostGroup, Configuration, ActionLog, ApplyLog
from django.utils.translation import ugettext as _

# Actions-List

class ListActionLogView(TemplateView):

    def get(self, request, *args, **kwargs):

        actions_list = ActionLog.objects.order_by("-timestamp")

        paginator = Paginator(actions_list, settings.ACTIONS_MAX)

        page = request.GET.get("page")

        try:
            actions = paginator.page(page)

        except PageNotAnInteger:
            actions = paginator.page(1)

        except EmptyPage:
            actions = paginator.page(paginator.num_pages)

        return render_to_response(
            "keys/actionslist.html",
            RequestContext(
                request,
                {
                    "actions": actions
                }
            )
        )

class DeleteActionLogView(TemplateView):

    def get(self, request, *args, **kwargs):

        # Clean actionlog

        ActionLog.objects.all().delete()

        # Add note about that

        ActionLog(
            timestamp = datetime.now(),
            user = self.request.user,
            action = "DELETE_ACTIONLOG"
        ).save()

        return redirect("actionlog_list")


# Apply-View

class ApplyView(TemplateView):
    """
    Applies the current configuration and delivers the authorized_keys-files.

    **Template:**

    :template:`keys/apply.html`

    """

    template_name = "keys/apply.html"

    mode = "index"

    affected_hosts = set()

    ssh_messages = []

    def get_context_data(self, **kwargs):
        context = super(ApplyView, self).get_context_data(**kwargs)

        context["mode"] = self.mode

        if len(self.affected_hosts) > 0:
            context["affected_hosts"] = Host.objects.filter(
                id__in = self.affected_hosts
            )

        if len(self.ssh_messages) > 0:
            context["log_output"] = "\n".join(self.ssh_messages)

        return context

    def post(self, request, *args, **kwargs):

        if "do_scan" in request.POST:

            self.affected_hosts = set()
            self.mode = "scanned"

            for host in ApplyLog.objects.all():
                self.affected_hosts.add(host.host.id)

            request.session["affected_hosts"] = self.affected_hosts

        elif "do_apply" in request.POST:

            self.mode = "done"

            self.affected_hosts = request.session["affected_hosts"]

            public_key = Configuration.objects.get(
                key = "sshkey_public"
            )

            private_key_config = Configuration.objects.get(
                key = "sshkey_private"
            )

            private_key_file = StringIO.StringIO(str(private_key_config.value))

            private_key = DSSKey.from_private_key(file(private_key_file))

            private_key_file.close()

            affected_host_objects = Host.objects.filter(
                id__in = self.affected_hosts
            )

            self.ssh_messages = []

            for host in affected_host_objects:

                # Find all users, that have access to this host.

                authorized_keys = set()

                user_keys = Key.objects.filter(
                    user__useringroup__group__usergroupinhostgroup__hostgroup__hostingroup__host__id =
                    host.id
                )

                for key in user_keys:
                    authorized_keys.add(key.key)

                # Add our own public key to the keys

                authorized_keys.add("ssh-dss %s skd" % (public_key.value,))

                # Generate the authorized_keys file onto the server.

                client = SSHClient()
                client.load_system_host_keys()
                client.set_missing_host_key_policy(AutoAddPolicy)

                is_connected = False

                try:

                    client.connect(
                        hostname = str(host.fqdn),
                        username = str(host.user),
                        pkey = private_key
                    )

                    is_connected = True

                except AuthenticationException:

                    self.ssh_messages.append(_(
                        "Cannot connect to host %(name)s as user %(user)s. "
                        "Perhaps the skd-key hasn't  been added to it's "
                        "authorized_keys-file" %
                        {
                            "name": host.name,
                            "user": host.user
                        }
                    ))

                except SSHException, socket.error:

                    self.ssh_messages.append(_(
                        "System failure connecting to SSH host %(host)s as "
                        "user %(user)s: %(error)s" %
                        {
                            "error": sys.exc_info()[0],
                            "host": host.name,
                            "user": host.user
                        }
                    ))

                if is_connected:

                    try:

                        command = 'echo -e "%s" > ~/'\
                                  '.ssh/authorized_keys' %\
                                  (
                                      "\n".join(authorized_keys)
                                  )

                        client.exec_command(command = command)

                        self.ssh_messages.append(_(
                            "Host %(host)s with user %(user)s completed." %
                            {
                                "host": host.name,
                                "user": host.user
                            }
                        ))

                        # Add note

                        ActionLog(
                            timestamp = datetime.now(),
                            user = self.request.user,
                            action = "APPLY"
                        ).save()

                        # Delete host from apply-Log.

                        ApplyLog.objects.get(host = host).delete()

                    except SSHException:

                        self.ssh_messages.append(_(
                            "Error deploying the authorized_keys-file of "
                            "host %(host)s / user %(user)s: %(error)s" %\
                            {
                                "error": sys.exc_info()[0],
                                "host": host.name,
                                "user": host.user
                            }
                        ))

        return self.get(request, *args, **kwargs)

# Setup-View

class SetupView(TemplateView):
    """
    Creates a setup view for basic installation tasks such as creating
    a new ssh key pair.

    **Template:**

    :template:`keys/setup.html`

    """

    template_name = "keys/setup.html"

    default_groups = [
        {
            "name": "skd_viewer",
            "description": "Users can only view and list objects like users, "
                           "keys, hosts, etc. They cannot edit, delete or "
                           "create them and cannot apply changes. They cannot"
                           " see the Action Log.",
            "permissions": [
                "keys.list_users",
                "keys.list_users_keys",
                "keys.list_usergroups",
                "keys.list_users_in_usergroups",
                "keys.list_hosts",
                "keys.list_hostgroups",
                "keys.list_hosts_in_hostgroups",
                "keys.list_usergroups_in_hostgroups"
            ]
        },
        {
            "name": "skd_audit",
            "description": "Users can see the action log.",
            "permissions": [
                "keys.list_users",
                "keys.list_users_keys",
                "keys.list_usergroups",
                "keys.list_users_in_usergroups",
                "keys.list_hosts",
                "keys.list_hostgroups",
                "keys.list_hosts_in_hostgroups",
                "keys.list_usergroups_in_hostgroups",
                "keys.list_actionlog"
            ]
        },
        {
            "name": "skd_usermanager",
            "description": "Users have full control of the user, "
                           "usergroup and key objects",
            "permissions": [
                "keys.list_users",
                "keys.list_users_keys",
                "keys.list_usergroups",
                "keys.list_users_in_usergroups",
                "keys.list_hosts",
                "keys.list_hostgroups",
                "keys.list_hosts_in_hostgroups",
                "keys.list_usergroups_in_hostgroups",
                "keys.list_actionlog",
                "keys.add_user",
                "keys.change_user",
                "keys.delete_user",
                "keys.add_key",
                "keys.change_key",
                "keys.delete_key",
                "keys.add_usergroup",
                "keys.change_usergroup",
                "keys.delete_usergroup",
                "keys.add_useringroup",
                "keys.change_useringroup",
                "keys.delete_useringroup",
                "keys.add_actionlog",
                "keys.add_applylog"
            ]
        },
        {
            "name": "skd_hostmanager",
            "description": "Users have the permissions in <em>skd_audit</em> "
                           "plus full control of the host and hostgroup "
                           "objects.",
            "permissions": [
                "keys.list_users",
                "keys.list_users_keys",
                "keys.list_usergroups",
                "keys.list_users_in_usergroups",
                "keys.list_hosts",
                "keys.list_hostgroups",
                "keys.list_hosts_in_hostgroups",
                "keys.list_usergroups_in_hostgroups",
                "keys.list_actionlog",
                "keys.add_host",
                "keys.change_host",
                "keys.delete_host",
                "keys.add_hostgroup",
                "keys.change_hostgroup",
                "keys.delete_hostgroup",
                "keys.add_hostingroup",
                "keys.change_hostingroup",
                "keys.delete_hostingroup",
                "keys.add_actionlog",
                "keys.add_applylog"
            ]
        },
        {
            "name": "skd_manager",
            "description": "<em>skd_usermanager</em> and "
                           "<em>skd_hostmanager</em> combined.",
            "permissions": [
                "keys.list_users",
                "keys.list_users_keys",
                "keys.list_usergroups",
                "keys.list_users_in_usergroups",
                "keys.list_hosts",
                "keys.list_hostgroups",
                "keys.list_hosts_in_hostgroups",
                "keys.list_usergroups_in_hostgroups",
                "keys.list_actionlog",
                "keys.add_user",
                "keys.change_user",
                "keys.delete_user",
                "keys.add_key",
                "keys.change_key",
                "keys.delete_key",
                "keys.add_usergroup",
                "keys.change_usergroup",
                "keys.delete_usergroup",
                "keys.add_useringroup",
                "keys.change_useringroup",
                "keys.delete_useringroup",
                "keys.add_host",
                "keys.change_host",
                "keys.delete_host",
                "keys.add_hostgroup",
                "keys.change_hostgroup",
                "keys.delete_hostgroup",
                "keys.add_hostingroup",
                "keys.change_hostingroup",
                "keys.delete_hostingroup",
                "keys.add_actionlog",
                "keys.add_applylog"
            ]
        },
        {
            "name": "skd_deployer",
            "description": "Can manage the whole database and apply the "
                           "changes (thus deploy new keys). Can delete the "
                           "actionlog.",
            "permissions": [
                "keys.list_users",
                "keys.list_users_keys",
                "keys.list_usergroups",
                "keys.list_users_in_usergroups",
                "keys.list_hosts",
                "keys.list_hostgroups",
                "keys.list_hosts_in_hostgroups",
                "keys.list_usergroups_in_hostgroups",
                "keys.list_actionlog",
                "keys.add_user",
                "keys.change_user",
                "keys.delete_user",
                "keys.add_key",
                "keys.change_key",
                "keys.delete_key",
                "keys.add_usergroup",
                "keys.change_usergroup",
                "keys.delete_usergroup",
                "keys.add_useringroup",
                "keys.change_useringroup",
                "keys.delete_useringroup",
                "keys.add_host",
                "keys.change_host",
                "keys.delete_host",
                "keys.add_hostgroup",
                "keys.change_hostgroup",
                "keys.delete_hostgroup",
                "keys.add_hostingroup",
                "keys.change_hostingroup",
                "keys.delete_hostingroup",
                "keys.add_actionlog",
                "keys.change_actionlog",
                "keys.delete_actionlog",
                "keys.can_apply",
                "keys.add_applylog",
                "keys.change_applylog",
                "keys.delete_applylog"
            ]
        }
    ]

    def get_context_data(self, **kwargs):
        context = super(SetupView, self).get_context_data(**kwargs)

        if Configuration.objects.filter(key="sshkey_public").count() == 1:

            context["sshkey_public"] = Configuration.objects.get(
                key = "sshkey_public"
            )

        if not models.Group.objects.filter(name__istartswith = "skd_").exists():

            context["no_groups"] = True
            context["default_groups"] = self.default_groups

        return context

    def post(self, request, *args, **kwargs):

        if "sshkey_generate" in request.POST:

            if Configuration.objects.filter(key="sshkey_public").count() == 1:

                public_key = Configuration.objects.get(
                    key = "sshkey_public"
                )

                private_key = Configuration.objects.get(
                    key = "sshkey_private"
                )

            else:

                public_key = Configuration()
                public_key.key = "sshkey_public"

                private_key = Configuration()
                private_key.key = "sshkey_private"

            dsskey = DSSKey.generate()

            public_key.value = dsskey.get_base64()

            public_key.save()

            private_key_file = StringIO.StringIO()

            dsskey.write_private_key(private_key_file)

            private_key.value = private_key_file.getvalue()

            private_key.save()

        if "groups_generate" in request.POST:

            for group in self.default_groups:
                current_group = models.Group(
                    name = group["name"]
                )

                current_group.save()

                for permission in group["permissions"]:
                    app, codename = permission.split(".")

                    app_ids = models.ContentType.objects.filter(
                        app_label = app
                    )

                    permission_object = models.Permission.objects.get (
                        codename = codename,
                        content_type_id__in = app_ids
                    )

                    current_group.permissions.add(permission_object)

                current_group.save()

        return self.get(request, *args, **kwargs)

# User views

class UserCreateView(CreateView):
    """
    Creates a user.

    **Context**

    ``RequestContext``

    **Template:**

    :template:`keys/user_form.html`
    """

    model = User
    success_url = "/users/list"

    def form_valid(self, form):

        # Save object

        self.object = form.save()

        # Log Creation

        ActionLog(
            timestamp = datetime.now(),
            user = self.request.user,
            action = "CREATE_USER",
            objectid = self.object.id
        ).save()

        return super(ModelFormMixin, self).form_valid(form)

class UserUpdateView(UpdateView):
    """
    Updates a user.

    **Context**

    ``RequestContext``

    **Template:**

    :template:`keys/user_form.html`
    """

    model = User
    success_url = "/users/list"

    def form_valid(self, form):

        # Log Update

        ActionLog(
            timestamp = datetime.now(),
            user = self.request.user,
            action = "UPDATE_USER",
            objectid = self.object.id,
            comment = _(
                "Updated user:\n"
                "Original data: \n"
                "%(name)s (%(fullname)s)\n"
                "%(comment)s\n"
                "\n"
                "New data: \n"
                "%(newname)s (%(newfullname)s)\n"
                "%(newcomment)s\n"
                % {
                    "name": self.object.name,
                    "fullname": self.object.fullname,
                    "comment": self.object.comment,
                    "newname": form.data["name"],
                    "newfullname": form.data["fullname"],
                    "newcomment": form.data["comment"]
                }
            )
        ).save()

        # Save object

        self.object = form.save()

        return super(ModelFormMixin, self).form_valid(form)



class UserDeleteView(DeleteView):
    """
    Deletes a user.

    **Context**

    ``RequestContext``

    **Template:**

    :template:`keys/user_confirm_delete.html`

    """

    model = User
    success_url = "/users/list"

    def delete(self, request, *args, **kwargs):

        # Delete object

        self.object = self.get_object()

        # Log affected hosts

        affected_hosts = Host.objects.filter(
            hostingroup__group__usergroupinhostgroup__usergroup__useringroup__user__id =
            self.object.id
        )

        for host in affected_hosts:
            if not ApplyLog.objects.filter(host = host).exists():
                ApplyLog(host = host).save()

        # Log Deletion

        ActionLog(
            timestamp = datetime.now(),
            user = self.request.user,
            action = "DELETE_USER",
            comment = _(
                "Deleting user %(name)s (%(fullname)s) with comment %"
                "(comment)s" %
                {
                    "name": self.object.name,
                    "fullname": self.object.fullname,
                    "comment": self.object.comment
                }
            )
        ).save()

        # Delete object

        self.object.delete()

        return HttpResponseRedirect(self.get_success_url())

# User/Key

class UserKeyListView(ListView):
    """
    Lists keys from a given user.

    **Context**

    ``RequestContext``

    ``key_owner``
        An instance of the owner holding the keys.

    **Template:**

    :template:`keys/key_list.html`

    """

    context_object_name = "user_keys"
    template_name = "keys/key_list.html"

    def get_queryset(self):
        self.key_owner = get_object_or_404(User, id=self.kwargs["user"])
        return Key.objects.filter(user=self.key_owner)

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(UserKeyListView, self).get_context_data(**kwargs)
        # Add in the Owner
        context["key_owner"] = self.key_owner
        return context

class UserKeyCreateView(CreateView):
    """
    Adds a new key for a user.

    **Context**

    ``RequestContext``

    ``key_owner``
        An instance of the owner holding the key.

    **Template:**

    :template:`keys/key_form.html`

    """

    template_name = "keys/key_form.html"

    def get_queryset(self):
        self.key_owner = get_object_or_404(User, id=self.kwargs["user"])
        return Key.objects.all()

    def get_context_data(self, **kwargs):
        context = super(UserKeyCreateView, self).get_context_data(**kwargs)
        context["key_owner"] = self.key_owner
        return context

    def get_initial(self):
        return {"user": self.key_owner}

    def get_success_url(self):
        return reverse(
            "users_keys_list",
            kwargs = {
                "user": self.key_owner.id
            }
        )

    def form_valid(self, form):

        # Save object

        self.object = form.save()

        # Log affected hosts

        affected_hosts = Host.objects.filter(
            hostingroup__group__usergroupinhostgroup__usergroup__useringroup__user__id =
            self.object.user.id
        )

        for host in affected_hosts:
            if not ApplyLog.objects.filter(host = host).exists():
                ApplyLog(host = host).save()

        # Log Creation

        ActionLog(
            timestamp = datetime.now(),
            user = self.request.user,
            action = "CREATE_KEY",
            objectid = self.object.id
        ).save()

        return super(ModelFormMixin, self).form_valid(form)

class UserKeyUpdateView(UpdateView):
    """
    Edits an existing key of a user.

    **Context**

    ``RequestContext``

    ``key_owner``
        An instance of the owner holding the key.

    **Template:**

    :template:`keys/key_form.html`

    """

    template_name = "keys/key_form.html"

    def get_queryset(self):
        self.key_owner = get_object_or_404(User, id=self.kwargs["user"])
        return Key.objects.all()

    def get_context_data(self, **kwargs):
        context = super(UserKeyUpdateView, self).get_context_data(**kwargs)
        context["key_owner"] = self.key_owner
        return context

    def get_initial(self):
        return {"user": self.key_owner}

    def get_success_url(self):
        return reverse(
            "users_keys_list",
            kwargs = {
                "user": self.key_owner.id
            }
        )

    def form_valid(self, form):

        # Log Update

        ActionLog(
            timestamp = datetime.now(),
            user = self.request.user,
            action = "UPDATE_KEY",
            objectid = self.object.id,
            objectid2 = self.object.user.id,
            comment = _(
                "Updated key of user %(user)s.\n"
                "Original data:\n"
                "Name: %(name)s\n"
                "Key: %(key)s\n"
                "%(comment)s\n"
                "\n"
                "New data:\n"
                "Name: %(newname)s\n"
                "Key: %(newkey)s\n"
                "%(newcomment)s\n"
                % {
                    "user": self.object.user.name,
                    "name": self.object.name,
                    "key": self.object.key,
                    "comment": self.object.comment,
                    "newname": form.data["name"],
                    "newkey": form.data["key"],
                    "newcomment": form.data["comment"]
                }
            )
        ).save()

        # Save object

        self.object = form.save()

        # Log affected hosts

        affected_hosts = Host.objects.filter(
            hostingroup__group__usergroupinhostgroup__usergroup__useringroup__user__id =
            self.object.user.id
        )

        for host in affected_hosts:
            if not ApplyLog.objects.filter(host = host).exists():
                ApplyLog(host = host).save()

        return super(ModelFormMixin, self).form_valid(form)

class UserKeyDeleteView(DeleteView):
    """
    Removes an existing key for a user.

    **Context**

    ``RequestContext``

    ``key_owner``
        An instance of the owner holding the key.

    **Template:**

    :template:`keys/key_confirm_delete.html`

    """

    template_name = "keys/key_confirm_delete.html"

    def get_object(self, queryset=None):
        self.key_owner = get_object_or_404(User, id=self.kwargs["user"])
        return get_object_or_404(Key, id=self.kwargs["pk"], user=self.key_owner)

    def get_context_data(self, **kwargs):
        context = super(UserKeyDeleteView, self).get_context_data(**kwargs)
        context["key_owner"] = self.key_owner
        return context

    def get_success_url(self):
        return reverse(
            "users_keys_list",
            kwargs = {
                "user": self.key_owner.id
            }
        )

    def delete(self, request, *args, **kwargs):

        # Delete object

        self.object = self.get_object()

        # Log affected hosts

        affected_hosts = Host.objects.filter(
            hostingroup__group__usergroupinhostgroup__usergroup__useringroup__user__id =
            self.object.user.id
        )

        for host in affected_hosts:
            if not ApplyLog.objects.filter(host = host).exists():
                ApplyLog(host = host).save()

        # Log Deletion

        ActionLog(
            timestamp = datetime.now(),
            user = self.request.user,
            action = "DELETE_KEY_FROM_USER",
            comment = _(
                "Deleting key '%(name)s' from user %(username)s with comment "
                "%(comment)s" % {
                    "name": self.object.name,
                    "username": self.object.user.name,
                    "comment": self.object.comment
                }
            )
        ).save()

        # Delete object

        self.object.delete()

        return HttpResponseRedirect(self.get_success_url())

# User/Group

class UserGroupCreateView(CreateView):
    """
    Creates a usergroup.

    **Context**

    ``RequestContext``

    **Template:**

    :template:`keys/usergroup_form.html`
    """

    model = UserGroup
    success_url = "/usergroups/list"

    def form_valid(self, form):

        # Save object

        self.object = form.save()

        # Log Creation

        ActionLog(
            timestamp = datetime.now(),
            user = self.request.user,
            action = "CREATE_USERGROUP",
            objectid = self.object.id
        ).save()

        return super(ModelFormMixin, self).form_valid(form)

class UserGroupUpdateView(UpdateView):
    """
    Updates a usergroup.

    **Context**

    ``RequestContext``

    **Template:**

    :template:`keys/usergroup_form.html`
    """

    model = UserGroup
    success_url = "/usergroups/list"

    def form_valid(self, form):

        # Log Update

        ActionLog(
            timestamp = datetime.now(),
            user = self.request.user,
            action = "UPDATE_USERGROUP",
            objectid = self.object.id,
            comment = _(
                "Updated usergroup.\n"
                "Original data:\n"
                "Name: %(name)s\n"
                "%(comment)s\n"
                "New data:\n"
                "Name: %(newname)s\n"
                "%(newcomment)s\n"
                % {
                    "name": self.object.name,
                    "comment": self.object.comment,
                    "newname": form.data["name"],
                    "newcomment": form.data["comment"]
                }
            )
        ).save()

        # Save object

        self.object = form.save()

        return super(ModelFormMixin, self).form_valid(form)

class UserGroupDeleteView(DeleteView):
    """
    Deletes a usergroup.

    **Context**

    ``RequestContext``

    **Template:**

    :template:`keys/usergroup_confirm_delete.html`

    """

    model = UserGroup
    success_url = "/usergroups/list"

    def delete(self, request, *args, **kwargs):

        # Delete object

        self.object = self.get_object()

        # Log affected hosts

        affected_hosts = Host.objects.filter(
            hostingroup__group__usergroupinhostgroup__usergroup__id =
            self.object.id
        )

        for host in affected_hosts:
            if not ApplyLog.objects.filter(host = host).exists():
                ApplyLog(host = host).save()

        # Log Deletion

        ActionLog(
            timestamp = datetime.now(),
            user = self.request.user,
            action = "DELETE_USERGROUP",
            comment = _(
                "Deleting usergroup %(name)s with comment %(comment)s" %
                {
                    "name": self.object.name,
                    "comment": self.object.comment
                }
            )
        ).save()

        # Delete object

        self.object.delete()

        return HttpResponseRedirect(self.get_success_url())

class UserGroupListView(ListView):
    """
    Lists groups a user is member of.

    **Context**

    ``RequestContext``

    ``group_member``
        The member of the groups.

    **Template:**

    :template:`keys/user_groups_list.html`

    """

    context_object_name = "user_groups"
    template_name = "keys/user_groups_list.html"

    def get_queryset(self):
        self.group_member = get_object_or_404(User, id=self.kwargs["user"])
        return UserInGroup.objects.filter(user=self.group_member)

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(UserGroupListView, self).get_context_data(**kwargs)
        # Add in the Owner
        context["group_member"] = self.group_member
        return context

class UserGroupAssignView(CreateView):
    """
    Assigns a user to a new group.

    **Context**

    ``RequestContext``

    ``group_member``
        The member of the group to be.

    **Template:**

    :template:`keys/user_groups_assign.html`

    """

    template_name = "keys/user_groups_assign.html"

    def get_queryset(self):
        self.group_member = get_object_or_404(User, id=self.kwargs["user"])
        return UserInGroup.objects.all()

    def get_context_data(self, **kwargs):
        context = super(UserGroupAssignView, self).get_context_data(**kwargs)
        context["group_member"] = self.group_member
        return context

    def get_initial(self):
        return {"user": self.group_member}

    def get_success_url(self):
        return reverse(
            "users_groups_list",
            kwargs = {
                "user": self.group_member.id
            }
        )

    def form_valid(self, form):

        # Save object

        self.object = form.save()

        # Log affected hosts

        affected_hosts = Host.objects.filter(
            hostingroup__group__usergroupinhostgroup__usergroup__useringroup__group__id =
                self.object.group.id
        )

        for host in affected_hosts:
            if not ApplyLog.objects.filter(host = host).exists():
                ApplyLog(host = host).save()

        # Log Assignment

        ActionLog(
            timestamp = datetime.now(),
            user = self.request.user,
            action = "ASSIGN_USERINGROUP",
            objectid = self.object.user.id,
            comment = _(
                "Assigned user %(user)s to usergroup %(usergroup)s" %
                {
                    "user": self.object.user.name,
                    "usergroup": self.object.group.name
                }
            )
        ).save()

        return super(ModelFormMixin, self).form_valid(form)

class UserGroupUnassignView(DeleteView):
    """
    Removes a member from a group.

    **Context**

    ``RequestContext``

    ``group_member``
        The member of the group.

    **Template:**

    :template:`keys/user_groups_unassign_confirm.html`

    """

    template_name = "keys/user_groups_unassign_confirm.html"

    def get_object(self, queryset=None):
        self.group_member = get_object_or_404(User, id=self.kwargs["user"])
        return get_object_or_404(
            UserInGroup,
            id=self.kwargs["pk"],
            user=self.group_member
        )

    def get_context_data(self, **kwargs):
        context = super(UserGroupUnassignView, self).get_context_data(**kwargs)
        context["group_member"] = self.group_member
        return context

    def get_success_url(self):
        return reverse(
            "users_groups_list",
            kwargs = {
                "user": self.group_member.id
            }
        )

    def delete(self, request, *args, **kwargs):

        # Delete object

        self.object = self.get_object()

        # Log affected hosts

        affected_hosts = Host.objects.filter(
            hostingroup__group__usergroupinhostgroup__usergroup__useringroup__id =
            self.object.group.id
        )

        for host in affected_hosts:
            if not ApplyLog.objects.filter(host = host).exists():
                ApplyLog(host = host).save()

        # Log Unassignment

        ActionLog(
            timestamp = datetime.now(),
            user = self.request.user,
            action = "UNASSIGN_USERINGROUP",
            objectid = self.object.user.id,
            comment = _(
                "Removed user %(user)s from usergroup %(usergroup)s" %
                {
                    "user": self.object.user.name,
                    "usergroup": self.object.group.name
                }
            )
        ).save()

        # Delete object

        self.object.delete()

        return HttpResponseRedirect(self.get_success_url())

# Usergroup/User

class UserGroupUserListView(ListView):
    """
    Lists members of a usergroup.

    **Context**

    ``RequestContext``

    ``usergroup``
        The usergroup.

    **Template:**

    :template:`keys/usergroup_users_list.html`

    """

    context_object_name = "usergroup_users"
    template_name = "keys/usergroup_users_list.html"

    def get_queryset(self):
        self.usergroup = get_object_or_404(UserGroup, id=self.kwargs["usergroup"])
        return UserInGroup.objects.filter(group=self.usergroup)

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(UserGroupUserListView, self).get_context_data(**kwargs)
        # Add in the Owner
        context["usergroup"] = self.usergroup
        return context

class UserGroupUserAssignView(CreateView):
    """
    Adds a new member to an usergroup.

    **Context**

    ``RequestContext``

    ``usergroup``
        The usergroup.

    **Template:**

    :template:`keys/usergroup_users_assign.html`

    """

    template_name = "keys/usergroup_users_assign.html"

    def get_queryset(self):
        self.usergroup = get_object_or_404(UserGroup, id=self.kwargs["usergroup"])
        return UserInGroup.objects.all()

    def get_context_data(self, **kwargs):
        context = super(UserGroupUserAssignView, self).get_context_data(**kwargs)
        context["usergroup"] = self.usergroup
        return context

    def get_initial(self):
        return {"group": self.usergroup}

    def get_success_url(self):
        return reverse(
            "usergroups_users_list",
            kwargs = {
                "usergroup": self.usergroup.id
            }
        )

    def form_valid(self, form):

        # Save object

        self.object = form.save()

        # Log affected hosts

        affected_hosts = Host.objects.filter(
            hostingroup__group__usergroupinhostgroup__usergroup__useringroup__group__id =
            self.object.group.id
        )

        for host in affected_hosts:
            if not ApplyLog.objects.filter(host = host).exists():
                ApplyLog(host = host).save()

        # Log Assignment

        ActionLog(
            timestamp = datetime.now(),
            user = self.request.user,
            action = "ASSIGN_USERINGROUP",
            objectid = self.object.user.id,
            objectid2 = self.object.group.id
        ).save()

        return super(ModelFormMixin, self).form_valid(form)

class UserGroupUserUnassignView(DeleteView):
    """
    Removes a member from an usergroup.

    **Context**

    ``RequestContext``

    ``usergroup``
        The usergroup.

    **Template:**

    :template:`keys/usergroup_users_unassign_confirm.html`

    """

    template_name = "keys/usergroup_users_unassign_confirm.html"

    def get_object(self, queryset=None):
        self.usergroup = get_object_or_404(UserGroup, id=self.kwargs["usergroup"])
        return get_object_or_404(
            UserInGroup,
            id=self.kwargs["pk"],
            group=self.usergroup
        )

    def get_context_data(self, **kwargs):
        context = super(UserGroupUserUnassignView, self).get_context_data(**kwargs)
        context["usergroup"] = self.usergroup
        return context

    def get_success_url(self):
        return reverse(
            "usergroups_users_list",
            kwargs = {
                "usergroup": self.usergroup.id
            }
        )

    def delete(self, request, *args, **kwargs):

        # Delete object

        self.object = self.get_object()

        # Log affected hosts

        affected_hosts = Host.objects.filter(
            hostingroup__group__usergroupinhostgroup__usergroup__useringroup__id =
            self.object.group.id
        )

        for host in affected_hosts:
            if not ApplyLog.objects.filter(host = host).exists():
                ApplyLog(host = host).save()

        # Log Unassignment

        ActionLog(
            timestamp = datetime.now(),
            user = self.request.user,
            action = "UNASSIGN_USERINGROUP",
            objectid = self.object.user.id,
            objectid2 = self.object.group.id
        ).save()

        # Delete object

        self.object.delete()

        return HttpResponseRedirect(self.get_success_url())

# Usergroup/Hostgroup

class UserGroupHostGroupListView(ListView):
    """
    Lists hostgroup assignments of an usergroup

    **Context**

    ``RequestContext``

    ``usergroup``
        The usergroup.

    **Template:**

    :template:`keys/usergroup_hostgroups_list.html`

    """

    context_object_name = "usergroup_hostgroups"
    template_name = "keys/usergroup_hostgroups_list.html"

    def get_queryset(self):
        self.usergroup = get_object_or_404(UserGroup, id=self.kwargs["usergroup"])
        return UserGroupInHostGroup.objects.filter(usergroup=self.usergroup)

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(UserGroupHostGroupListView, self).get_context_data(**kwargs)
        # Add in the Owner
        context["usergroup"] = self.usergroup
        return context

class UserGroupHostGroupAssignView(CreateView):
    """
    Assigns a new hostgroup to a usergroup

    **Context**

    ``RequestContext``

    ``usergroup``
        The usergroup.

    **Template:**

    :template:`keys/usergroup_hostgroups_assign.html`

    """

    template_name = "keys/usergroup_hostgroups_assign.html"

    def get_queryset(self):
        self.usergroup = get_object_or_404(UserGroup, id=self.kwargs["usergroup"])
        return UserGroupInHostGroup.objects.all()

    def get_context_data(self, **kwargs):
        context = super(UserGroupHostGroupAssignView, self).get_context_data(**kwargs)
        context["usergroup"] = self.usergroup
        return context

    def get_initial(self):
        return {"usergroup": self.usergroup}

    def get_success_url(self):
        return reverse(
            "usergroups_hostgroups_list",
            kwargs = {
                "usergroup": self.usergroup.id
            }
        )

    def form_valid(self, form):

        # Save object

        self.object = form.save()

        # Log affected hosts

        affected_hosts = Host.objects.filter(
            hostingroup__group__id =
            self.object.hostgroup.id
        )

        for host in affected_hosts:
            if not ApplyLog.objects.filter(host = host).exists():
                ApplyLog(host = host).save()

        # Log Assignment

        ActionLog(
            timestamp = datetime.now(),
            user = self.request.user,
            action = "ASSIGN_USERGROUPINHOSTGROUP",
            objectid = self.object.usergroup.id,
            objectid2 = self.object.hostgroup.id
        ).save()

        return super(ModelFormMixin, self).form_valid(form)

class UserGroupHostGroupUnassignView(DeleteView):
    """
    Unassigns a hostgroup from a usergroup

    **Context**

    ``RequestContext``

    ``usergroup``
        The usergroup.

    **Template:**

    :template:`keys/usergroup_hostgroups_unassign_confirm.html`

    """

    template_name = "keys/usergroup_hostgroups_unassign_confirm.html"

    def get_object(self, queryset=None):
        self.usergroup = get_object_or_404(UserGroup, id=self.kwargs["usergroup"])
        return get_object_or_404(
            UserGroupInHostGroup,
            id=self.kwargs["pk"],
            usergroup=self.usergroup
        )

    def get_context_data(self, **kwargs):
        context = super(UserGroupHostGroupUnassignView, self).get_context_data(**kwargs)
        context["usergroup"] = self.usergroup
        return context

    def get_success_url(self):
        return reverse(
            "usergroups_hostgroups_list",
            kwargs = {
                "usergroup": self.usergroup.id
            }
        )

    def delete(self, request, *args, **kwargs):

        # Delete object

        self.object = self.get_object()

        # Log affected hosts

        affected_hosts = Host.objects.filter(
            hostingroup__group__id =
            self.object.hostgroup.id
        )

        for host in affected_hosts:
            if not ApplyLog.objects.filter(host = host).exists():
                ApplyLog(host = host).save()

        # Log Unassignment

        ActionLog(
            timestamp = datetime.now(),
            user = self.request.user,
            action = "UNASSIGN_USERGROUPINHOSTGROUP",
            objectid = self.object.usergroup.id,
            objectid2 = self.object.hostgroup.id
        ).save()

        # Delete object

        self.object.delete()

        return HttpResponseRedirect(self.get_success_url())

# Host-Views

class HostCreateView(CreateView):
    """
    Creates a host.

    **Context**

    ``RequestContext``

    **Template:**

    :template:`keys/host_form.html`
    """

    model = Host
    success_url = "/hosts/list"

    def form_valid(self, form):

        # Save object

        self.object = form.save()

        # Log Creation

        ActionLog(
            timestamp = datetime.now(),
            user = self.request.user,
            action = "CREATE_HOST",
            objectid = self.object.id
        ).save()

        return super(ModelFormMixin, self).form_valid(form)

class HostUpdateView(UpdateView):
    """
    Updates a host.

    **Context**

    ``RequestContext``

    **Template:**

    :template:`keys/host_form.html`
    """

    model = Host
    success_url = "/hosts/list"

    def form_valid(self, form):

        # Log Update

        ActionLog(
            timestamp = datetime.now(),
            user = self.request.user,
            action = "UPDATE_HOST",
            objectid = self.object.id,
            comment = _(
                "Updated host.\n"
                "Original data:\n"
                "Name: %(name)s\n"
                "FQDN: %(fqdn)s\n"
                "User: %(user)s\n"
                "%(comment)s\n"
                "\n"
                "New data:\n"
                "Name: %(newname)s\n"
                "FQDN: %(newfqdn)s\n"
                "User: %(newuser)s\n"
                "%(comment)s"
                % {
                    "name": self.object.name,
                    "fqdn": self.object.fqdn,
                    "user": self.object.user,
                    "comment": self.object.comment,
                    "newname": form.data["name"],
                    "newfqdn": form.data["fqdn"],
                    "newuser": form.data["user"],
                    "newcomment": form.data["comment"]
                }
            )
        ).save()

        # Save object

        self.object = form.save()

        # Log affected host

        if not ApplyLog.objects.filter(host = self.object).exists():
            ApplyLog(host = self.object).save()

        return super(ModelFormMixin, self).form_valid(form)

class HostDeleteView(DeleteView):
    """
    Deletes a host.

    **Context**

    ``RequestContext``

    **Template:**

    :template:`keys/host_confirm_delete.html`

    """

    model = Host
    success_url = "/hosts/list"

    def delete(self, request, *args, **kwargs):

        # Delete object

        self.object = self.get_object()

        # Log Deletion

        ActionLog(
            timestamp = datetime.now(),
            user = self.request.user,
            action = "DELETE_HOST",
            comment = _(
                "Deleting host %(user)s@%(name)s (%(fqdn)s) with comment %"
                "(comment)s" %
                {
                    "name": self.object.name,
                    "fqdn": self.object.fqdn,
                    "user": self.object.user,
                    "comment": self.object.comment
                }
            )
        ).save()

        # Delete object

        self.object.delete()

        return HttpResponseRedirect(self.get_success_url())

# Setup

class HostSetupView(TemplateView):
    """
    Copies the skd public key into the host after a password authentication.

    **Template:**

    :template:`keys/setup.html

    """

    template_name = "keys/host_setup.html"
    ssh_message = ""

    def get_context_data(self, **kwargs):
        context = super(HostSetupView, self).get_context_data(**kwargs)

        context["host"] = Host.objects.get(id = kwargs["host"])
        context["sshkey_public"] = Configuration.objects.get(
            key = "sshkey_public"
        )
        context["ssh_message"] = self.ssh_message

        return context

    def post(self, request, *args, **kwargs):

        if request.POST["do_setup"]:

            password = request.POST["password"]
            host = Host.objects.get(id = request.POST["host"])

            sshkey_public = Configuration.objects.get(
                key = "sshkey_public"
            )

            client = SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(AutoAddPolicy)

            self.ssh_message = ""

            is_connected = False

            try:

                client.connect(
                    hostname = str(host.fqdn),
                    username = str(host.user),
                    password = str(password)
                )

                is_connected = True

            except AuthenticationException:

                self.ssh_message = \
                    _("Cannot connect to host. Perhaps the password is wrong")

            except SSHException, socket.error:

                self.ssh_message = _(
                    "System failure connecting to SSH host: "
                    "%(error)s" % { "error": sys.exc_info()[0] }
                )

            if is_connected:

                try:

                    command = 'echo "ssh-dss %s skd" >> ~/' \
                        '.ssh/authorized_keys' % \
                        ( sshkey_public.value, )

                    client.exec_command(command = command)

                    self.ssh_message = _("Host is set up.")

                except SSHException:

                    self.ssh_message = _(
                        "Error adding my public key to the "
                        "authorized_keys-file: %(error)s" % \
                        { "error": sys.exc_info()[0] }
                    )

        return self.get(request, *args, **kwargs)

# Host/Group

class HostGroupCreateView(CreateView):
    """
    Creates a hostgroup.

    **Context**

    ``RequestContext``

    **Template:**

    :template:`keys/host_form.html`
    """

    model = HostGroup
    success_url = "/hostgroups/list"

    def form_valid(self, form):

        # Save object

        self.object = form.save()

        # Log Creation

        ActionLog(
            timestamp = datetime.now(),
            user = self.request.user,
            action = "CREATE_HOSTGROUP",
            objectid = self.object.id
        ).save()

        return super(ModelFormMixin, self).form_valid(form)

class HostGroupUpdateView(UpdateView):
    """
    Update a hostgroup.

    **Context**

    ``RequestContext``

    **Template:**

    :template:`keys/host_form.html`
    """

    model = HostGroup
    success_url = "/hostgroups/list"

    def form_valid(self, form):

        # Log Update

        ActionLog(
            timestamp = datetime.now(),
            user = self.request.user,
            action = "UPDATE_HOSTGROUP",
            objectid = self.object.id,
            comment = _(
                "Updated hostgroup.\n"
                "Original data:\n"
                "Name: %(name)s\n"
                "%(comment)s\n"
                "New data:\n"
                "Name: %(newname)s\n"
                "%(newcomment)s\n"
                % {
                    "name": self.object.name,
                    "comment": self.object.comment,
                    "newname": form.data["name"],
                    "newcomment": form.data["comment"]
                }

            )
        ).save()

        # Save object

        self.object = form.save()

        return super(ModelFormMixin, self).form_valid(form)

class HostGroupDeleteView(DeleteView):
    """
    Deletes a hostgroup.

    **Context**

    ``RequestContext`

    **Template:**

    :template:`keys/hostgroup_confirm_delete.html`

    """

    model = HostGroup
    success_url = "/hostgroups/list"

    def delete(self, request, *args, **kwargs):

        # Delete object

        self.object = self.get_object()

        # Log affected hosts

        affected_hosts = Host.objects.filter(
            hostingroup__group__id =
            self.object.id
        )

        for host in affected_hosts:
            if not ApplyLog.objects.filter(host = host).exists():
                ApplyLog(host = host).save()

        # Log Deletion

        ActionLog(
            timestamp = datetime.now(),
            user = self.request.user,
            action = "DELETE_HOSTGROUP",
            comment = _(
                "Deleting hostgroup %(name)s with comment %(comment)s" %
                {
                    "name": self.object.name,
                    "comment": self.object.comment
                }
            )
        ).save()

        # Delete object

        self.object.delete()

        return HttpResponseRedirect(self.get_success_url())

class HostGroupListView(ListView):
    """
    Lists hostgroups a host is member of

    **Context**

    ``RequestContext``

    ``group_member``
        The group member.

    **Template:**

    :template:`keys/host_groups_list.html`

    """

    context_object_name = "host_groups"
    template_name = "keys/host_groups_list.html"

    def get_queryset(self):
        self.group_member = get_object_or_404(Host, id=self.kwargs["host"])
        return HostInGroup.objects.filter(host=self.group_member)

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(HostGroupListView, self).get_context_data(**kwargs)
        # Add in the Owner
        context["group_member"] = self.group_member
        return context

class HostGroupAssignView(CreateView):
    """
    Assign a host to a hostgroup

    **Context**

    ``RequestContext``

    ``group_member``
        The group member to be.

    **Template:**

    :template:`keys/host_groups_assign.html`

    """

    template_name = "keys/host_groups_assign.html"

    def get_queryset(self):
        self.group_member = get_object_or_404(Host, id=self.kwargs["host"])
        return HostInGroup.objects.all()

    def get_context_data(self, **kwargs):
        context = super(HostGroupAssignView, self).get_context_data(**kwargs)
        context["group_member"] = self.group_member
        return context

    def get_initial(self):
        return {"host": self.group_member}

    def get_success_url(self):
        return reverse(
            "hosts_groups_list",
            kwargs = {
                "host": self.group_member.id
            }
        )

    def form_valid(self, form):

        # Save object

        self.object = form.save()

        # Log affected host

        if not ApplyLog.objects.filter(host = self.object.host).exists():
            ApplyLog(host = self.object.host).save()

        # Log Assignment

        ActionLog(
            timestamp = datetime.now(),
            user = self.request.user,
            action = "ASSIGN_HOSTINGROUP",
            objectid = self.object.host.id,
            comment = _(
                "Assigned host %(user)s@%(host)s to group %(group)s" % {
                    "user": self.object.host.user,
                    "host": self.object.host.name,
                    "group": self.object.group.name
                }
            )
        ).save()

        return super(ModelFormMixin, self).form_valid(form)

class HostGroupUnassignView(DeleteView):
    """
    Unassign a host from a hostgroup

    **Context**

    ``RequestContext``

    ``group_member``
        The group member.

    **Template:**

    :template:`keys/host_groups_unassign_confirm.html`

    """

    template_name = "keys/host_groups_unassign_confirm.html"

    def get_object(self, queryset=None):
        self.group_member = get_object_or_404(Host, id=self.kwargs["host"])
        return get_object_or_404(
            HostInGroup,
            id=self.kwargs["pk"],
            host=self.group_member
        )

    def get_context_data(self, **kwargs):
        context = super(HostGroupUnassignView, self).get_context_data(**kwargs)
        context["group_member"] = self.group_member
        return context

    def get_success_url(self):
        return reverse(
            "hosts_groups_list",
            kwargs = {
                "host": self.group_member.id
            }
        )

    def delete(self, request, *args, **kwargs):

        # Delete object

        self.object = self.get_object()

        # Log affected host

        if not ApplyLog.objects.filter(host = self.object.host).exists():
            ApplyLog(host = self.object.host).save()

        # Log Unassignment

        ActionLog(
            timestamp = datetime.now(),
            user = self.request.user,
            action = "UNASSIGN_HOSTINGROUP",
            objectid = self.object.host.id,
            comment = _(
                "Removed host %(user)s@%(host)s from group %(group)s" % {
                    "user": self.object.host.user,
                    "host": self.object.host.name,
                    "group": self.object.group.name
                }
            )
        ).save()

        # Delete object

        self.object.delete()

        return HttpResponseRedirect(self.get_success_url())

# Hostgroup/Host

class HostGroupHostListView(ListView):
    """
    Lists the member hosts of a hostgroups

    **Context**

    ``RequestContext``

    ``hostgroup``
        The hostgroup.

    **Template:**

    :template:`keys/hostgroup_hosts_list.html`

    """

    context_object_name = "hostgroup_hosts"
    template_name = "keys/hostgroup_hosts_list.html"

    def get_queryset(self):
        self.hostgroup = get_object_or_404(HostGroup, id=self.kwargs["hostgroup"])
        return HostInGroup.objects.filter(group=self.hostgroup)

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(HostGroupHostListView, self).get_context_data(**kwargs)
        # Add in the Owner
        context["hostgroup"] = self.hostgroup
        return context

class HostGroupHostAssignView(CreateView):
    """
    Adds a host to a hostgroup

    **Context**

    ``RequestContext``

    ``hostgroup``
        The hostgroup.

    **Template:**

    :template:`keys/hostgroup_hosts_assign.html`

    """

    template_name = "keys/hostgroup_hosts_assign.html"

    def get_queryset(self):
        self.hostgroup = get_object_or_404(HostGroup, id=self.kwargs["hostgroup"])
        return HostInGroup.objects.all()

    def get_context_data(self, **kwargs):
        context = super(HostGroupHostAssignView, self).get_context_data(**kwargs)
        context["hostgroup"] = self.hostgroup
        return context

    def get_initial(self):
        return {"group": self.hostgroup}

    def get_success_url(self):
        return reverse(
            "hostgroups_hosts_list",
            kwargs = {
                "hostgroup": self.hostgroup.id
            }
        )

    def form_valid(self, form):

        # Save object

        self.object = form.save()

        # Log affected host

        if not ApplyLog.objects.filter(host = self.object.host).exists():
            ApplyLog(host = self.object.host).save()

        # Log Assignment

        ActionLog(
            timestamp = datetime.now(),
            user = self.request.user,
            action = "ASSIGN_HOSTINGROUP",
            objectid = self.object.host.id,
            objectid2 = self.object.group.id
        ).save()

        return super(ModelFormMixin, self).form_valid(form)

class HostGroupHostUnassignView(DeleteView):
    """
    Removes a host from a hostgroup

    **Context**

    ``RequestContext``

    ``hostgroup``
        The hostgroup.

    **Template:**

    :template:`keys/hostgroup_hosts_unassign_confirm.html`

    """

    template_name = "keys/hostgroup_hosts_unassign_confirm.html"

    def get_object(self, queryset=None):
        self.hostgroup = get_object_or_404(HostGroup, id=self.kwargs["hostgroup"])
        return get_object_or_404(
            HostInGroup,
            id=self.kwargs["pk"],
            group=self.hostgroup
        )

    def get_context_data(self, **kwargs):
        context = super(HostGroupHostUnassignView, self).get_context_data(**kwargs)
        context["hostgroup"] = self.hostgroup
        return context

    def get_success_url(self):
        return reverse(
            "hostgroups_hosts_list",
            kwargs = {
                "hostgroup": self.hostgroup.id
            }
        )

    def delete(self, request, *args, **kwargs):

        # Delete object

        self.object = self.get_object()

        # Log affected host

        if not ApplyLog.objects.filter(host = self.object.host).exists():
            ApplyLog(host = self.object.host).save()

        # Log Unassignment

        ActionLog(
            timestamp = datetime.now(),
            user = self.request.user,
            action = "UNASSIGN_HOSTINGROUP",
            objectid = self.object.host.id,
            objectid2 = self.object.group.id
        ).save()

        # Delete object

        self.object.delete()

        return HttpResponseRedirect(self.get_success_url())

# Hostgroup/Usergroup

class HostGroupUserGroupListView(ListView):
    """
    Lists the usergroups assigned to a hostgroup

    **Context**

    ``RequestContext``

    ``hostgroup``
        The hostgroup.

    **Template:**

    :template:`keys/hostgroup_usergroups_list.html`

    """

    context_object_name = "hostgroup_usergroups"
    template_name = "keys/hostgroup_usergroups_list.html"

    def get_queryset(self):
        self.hostgroup = get_object_or_404(HostGroup, id=self.kwargs["hostgroup"])
        return UserGroupInHostGroup.objects.filter(hostgroup=self.hostgroup)

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(HostGroupUserGroupListView, self).get_context_data(**kwargs)
        # Add in the Owner
        context["hostgroup"] = self.hostgroup
        return context

class HostGroupUserGroupAssignView(CreateView):
    """
    Assigns an usergroup to a hostgroup

    **Context**

    ``RequestContext``

    ``hostgroup``
        The hostgroup.

    **Template:**

    :template:`keys/hostgroup_usergroups_assign.html`

    """

    template_name = "keys/hostgroup_usergroups_assign.html"

    def get_queryset(self):
        self.hostgroup = get_object_or_404(HostGroup, id=self.kwargs["hostgroup"])
        return UserGroupInHostGroup.objects.all()

    def get_context_data(self, **kwargs):
        context = super(HostGroupUserGroupAssignView, self).get_context_data(**kwargs)
        context["hostgroup"] = self.hostgroup
        return context

    def get_initial(self):
        return {"hostgroup": self.hostgroup}

    def get_success_url(self):
        return reverse(
            "hostgroups_usergroups_list",
            kwargs = {
                "hostgroup": self.hostgroup.id
            }
        )

    def form_valid(self, form):

        # Save object

        self.object = form.save()

        # Log affected hosts

        affected_hosts = Host.objects.filter(
            hostingroup__group__id =
            self.object.hostgroup.id
        )

        for host in affected_hosts:
            if not ApplyLog.objects.filter(host = host).exists():
                ApplyLog(host = host).save()

        # Log Assignment

        ActionLog(
            timestamp = datetime.now(),
            user = self.request.user,
            action = "ASSIGN_USERGROUPINHOSTGROUP",
            objectid = self.object.usergroup.id,
            comment = _(
                "Assigned usergroup %(usergroup)s to hostgroup %(hostgroup)s" %
                {
                    "usergroup": self.object.usergroup.name,
                    "hostgroup": self.object.hostgroup.name
                }
            )
        ).save()

        return super(ModelFormMixin, self).form_valid(form)

class HostGroupUserGroupUnassignView(DeleteView):
    """
    Unassigns a hostgroup from an usergroup

    **Context**

    ``RequestContext``

    ``hostgroup``
        The hostgroup.

    **Template:**

    :template:`keys/hostgroup_usergroups_unassign_confirm.html`

    """

    template_name = "keys/hostgroup_usergroups_unassign_confirm.html"

    def get_object(self, queryset=None):
        self.hostgroup = get_object_or_404(HostGroup, id=self.kwargs["hostgroup"])
        return get_object_or_404(
            UserGroupInHostGroup,
            id=self.kwargs["pk"],
            hostgroup=self.hostgroup
        )

    def get_context_data(self, **kwargs):
        context = super(HostGroupUserGroupUnassignView, self).get_context_data(**kwargs)
        context["hostgroup"] = self.hostgroup
        return context

    def get_success_url(self):
        return reverse(
            "hostgroups_usergroups_list",
            kwargs = {
                "hostgroup": self.hostgroup.id
            }
        )

    def delete(self, request, *args, **kwargs):

        # Delete object

        self.object = self.get_object()

        # Log affected hosts

        affected_hosts = Host.objects.filter(
            hostingroup__group__id =
            self.object.hostgroup.id
        )

        for host in affected_hosts:
            if not ApplyLog.objects.filter(host = host).exists():
                ApplyLog(host = host).save()

        # Log Unassignment

        ActionLog(
            timestamp = datetime.now(),
            user = self.request.user,
            action = "UNASSIGN_USERGROUPINHOSTGROUP",
            objectid = self.object.usergroup.id,
            comment = _(
                "Removed association of usergroup %(usergroup)s with hostgroup"
                " %(hostgroup)s" %
                {
                    "usergroup": self.object.usergroup.name,
                    "hostgroup": self.object.hostgroup.name
                }
            )
        ).save()

        # Delete object

        self.object.delete()

        return HttpResponseRedirect(self.get_success_url())