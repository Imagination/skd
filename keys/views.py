import StringIO
from datetime import datetime
from sets import Set
import socket
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.generic.base import TemplateView
from django.views.generic.edit import CreateView, UpdateView, DeleteView, \
    ModelFormMixin
from django.views.generic.list import ListView

from paramiko.client import SSHClient, AutoAddPolicy
from paramiko.dsskey import DSSKey
from paramiko.pkey import PKey
from paramiko.ssh_exception import AuthenticationException, SSHException
import sys
from keys.models import User,Key, UserGroup, UserInGroup, HostInGroup, Host, \
    HostGroup, UserGroupInHostGroup, Configuration, ActionLog
from django.utils.translation import ugettext as _

# Apply-View

class ApplyView(TemplateView):
    """
    Applies the current configuration and delivers the authorized_keys-files.

    **Template:**

    :template:`keys/apply.html`

    """

    template_name = "keys/apply.html"

    mode = "index"

    affected_hosts = Set()

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

            self.affected_hosts = Set()
            self.mode = "scanned"

            scan_timestamp = datetime.now()

            # Check the ActionLog and analyze pending changes.

            for line in ActionLog.objects.filter(
                timestamp__lte = scan_timestamp
            ).order_by("timestamp"):

                if line.action == "UNASSIGN_HOSTINGROUP" or\
                   line.action == "ASSIGN_HOSTINGROUP":

                    # A host has been added to or removed from a hostgroup

                    self.affected_hosts.add(line.memberid)

                elif line.action == "UNASSIGN_USERINGROUP" or\
                    line.action == "ASSIGN_USERINGROUP":

                    # A user has been assigned to or removed from a usergroup

                    # Find all hosts for this usergroup

                    affected_mastergroups =\
                        UserGroupInHostGroup.objects.filter(
                        usergroup__id = line.groupid
                    )

                    for hostgroup in affected_mastergroups:

                        affected_hosts = Host.objects.filter(
                            hostingroup__group__id = hostgroup.id
                        )

                        for host in affected_hosts:
                            self.affected_hosts.add(host.id)

                elif line.action == "UNASSIGN_USERGROUPINHOSTGROUP" or\
                    line.action == "ASSIGN_USERGROUPINHOSTGROUP":

                    # A usergroup has been removed from a hostgroup or vice
                    # versa

                    affected_hosts = Host.objects.filter(
                        hostingroup__group__id = line.groupid
                    )

                    for host in affected_hosts:
                        self.affected_hosts.add(host.id)

                request.session["affected_hosts"] = self.affected_hosts
                request.session["scan_timestamp"] = scan_timestamp

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

            private_key = DSSKey.from_private_key(private_key_file)

            private_key_file.close()

            affected_host_objects = Host.objects.filter(
                id__in = self.affected_hosts
            )

            self.ssh_messages = []

            for host in affected_host_objects:

                # Find all users, that have access to this host.

                authorized_keys = Set()

                user_keys = Key.objects.filter(
                    user__useringroup__group__usergroupinhostgroup__hostgroup__hostingroup__host__id =
                    host.id
                )

                for key in user_keys:
                    authorized_keys.add(key.key)

                # Add our own public key to the keys

                authorized_keys.add("ssh-dss %s skd" % (public_key.value))

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

                    except:

                        self.ssh_messages.append(_(
                            "Error adding my public key to the "
                            "authorized_keys-file of host %(host)s / user %"
                            "(user)s: %(error)s" %\
                            {
                                "error": sys.exc_info()[0],
                                "host": host.name,
                                "user": user.name
                            }
                        ))

            # Delete the action log up to the scan time

            ActionLog.objects.filter(
                timestamp__lte = request.session["scan_timestamp"]
            ).delete()

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

    def get_context_data(self, **kwargs):
        context = super(SetupView, self).get_context_data(**kwargs)

        if Configuration.objects.filter(key="sshkey_public").count() == 1:

            context["sshkey_public"] = Configuration.objects.get(
                key = "sshkey_public"
            )

        return context

    def post(self, request, *args, **kwargs):

        if request.POST["sshkey_generate"]:

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

        return self.get(request, *args, **kwargs)

# User views

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
            "user_keys_list",
            kwargs = {
                self.key_owner.id
            }
        )

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

# User/Group

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

        # Filter an "UNASSIGN"-logentry for the same user.

        unassign_logs = ActionLog.objects.filter(
            action = "UNASSIGN_USERINGROUP",
            groupid = self.object.group.id,
            memberid = self.object.user.id
        )

        if unassign_logs.count() == 1:

            # There already is an assignment for that. Remove that one

            for unassign_log in unassign_logs:
                unassign_log.delete()

        elif unassign_logs.count() > 1:

            raise _("System error. Retrieved more than one assignment log.")

        else:

            # Log Assignment

            ActionLog(
                timestamp = datetime.now(),
                user = self.request.user,
                action = "ASSIGN_USERINGROUP",
                groupid = self.object.group.id,
                memberid = self.object.user.id
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

        # Filter an "ASSIGN"-logentry for the same host.

        assign_logs = ActionLog.objects.filter(
            action = "ASSIGN_USERINGROUP",
            groupid = self.object.group.id,
            memberid = self.object.user.id
        )

        if assign_logs.count() == 1:

            # There already is an assignment for that. Remove that one

            for assign_log in assign_logs:
                assign_log.delete()

        elif assign_logs.count() > 1:

            raise _("System error. Retrieved more than one assignment log.")

        else:

            # Log Unassignment

            ActionLog(
                timestamp = datetime.now(),
                user = self.request.user,
                action = "UNASSIGN_USERINGROUP",
                groupid = self.object.group.id,
                memberid = self.object.user.id
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

        # Filter an "UNASSIGN"-logentry for the same user.

        unassign_logs = ActionLog.objects.filter(
            action = "UNASSIGN_USERINGROUP",
            groupid = self.object.group.id,
            memberid = self.object.user.id
        )

        if unassign_logs.count() == 1:

            # There already is an assignment for that. Remove that one

            for unassign_log in unassign_logs:
                unassign_log.delete()

        elif unassign_logs.count() > 1:

            raise _("System error. Retrieved more than one assignment log.")

        else:

            # Log Assignment

            ActionLog(
                timestamp = datetime.now(),
                user = self.request.user,
                action = "ASSIGN_USERINGROUP",
                groupid = self.object.group.id,
                memberid = self.object.user.id
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

        # Filter an "ASSIGN"-logentry for the same host.

        assign_logs = ActionLog.objects.filter(
            action = "ASSIGN_USERINGROUP",
            groupid = self.object.group.id,
            memberid = self.object.user.id
        )

        if assign_logs.count() == 1:

            # There already is an assignment for that. Remove that one

            for assign_log in assign_logs:
                assign_log.delete()

        elif assign_logs.count() > 1:

            raise _("System error. Retrieved more than one assignment log.")

        else:

            # Log Unassignment

            ActionLog(
                timestamp = datetime.now(),
                user = self.request.user,
                action = "UNASSIGN_USERINGROUP",
                groupid = self.object.group.id,
                memberid = self.object.user.id
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

        # Filter an "UNASSIGN"-logentry for the same host.

        unassign_logs = ActionLog.objects.filter(
            action = "UNASSIGN_USERGROUPINHOSTGROUP",
            groupid = self.object.hostgroup.id,
            memberid = self.object.usergroup.id
        )

        if unassign_logs.count() == 1:

            # There already is an assignment for that. Remove that one

            for unassign_log in unassign_logs:
                unassign_log.delete()

        elif unassign_logs.count() > 1:

            raise _("System error. Retrieved more than one assignment log.")

        else:

            # Log Assignment

            ActionLog(
                timestamp = datetime.now(),
                user = self.request.user,
                action = "ASSIGN_USERGROUPINHOSTGROUP",
                groupid = self.object.hostgroup.id,
                memberid = self.object.usergroup.id
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

        # Filter an "ASSIGN"-logentry for the same host.

        assign_logs = ActionLog.objects.filter(
            action = "ASSIGN_USERGROUPINHOSTGROUP",
            groupid = self.object.hostgroup.id,
            memberid = self.object.usergroup.id
        )

        if assign_logs.count() == 1:

            # There already is an assignment for that. Remove that one

            for assign_log in assign_logs:
                assign_log.delete()

        elif assign_logs.count() > 1:

            raise _("System error. Retrieved more than one assignment log.")

        else:

            # Log Unassignment

            ActionLog(
                timestamp = datetime.now(),
                user = self.request.user,
                action = "UNASSIGN_USERGROUPINHOSTGROUP",
                groupid = self.object.hostgroup.id,
                memberid = self.object.usergroup.id
            ).save()

        # Delete object

        self.object.delete()

        return HttpResponseRedirect(self.get_success_url())

# Host-Views

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
                        ( sshkey_public.value )

                    client.exec_command(command = command)

                    self.ssh_message = _("Host is set up.")

                except:

                    self.ssh_message = _(
                        "Error adding my public key to the "
                        "authorized_keys-file: %(error)s" % \
                        { "error": sys.exc_info()[0] }
                    )

        return self.get(request, *args, **kwargs)


# Host/Group

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

        # Filter an "UNASSIGN"-logentry for the same host.

        unassign_logs = ActionLog.objects.filter(
            action = "UNASSIGN_HOSTINGROUP",
            groupid = self.object.group.id,
            memberid = self.object.host.id
        )

        if unassign_logs.count() == 1:

            # There already is an assignment for that. Remove that one

            for unassign_log in unassign_logs:
                unassign_log.delete()

        elif unassign_logs.count() > 1:

            raise _("System error. Retrieved more than one assignment log.")

        else:

            # Log Assignment

            ActionLog(
                timestamp = datetime.now(),
                user = self.request.user,
                action = "ASSIGN_HOSTINGROUP",
                groupid = self.object.group.id,
                memberid = self.object.host.id
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

        # Filter an "ASSIGN"-logentry for the same host.

        assign_logs = ActionLog.objects.filter(
            action = "ASSIGN_HOSTINGROUP",
            groupid = self.object.group.id,
            memberid = self.object.host.id
        )

        if assign_logs.count() == 1:

            # There already is an assignment for that. Remove that one

            for assign_log in assign_logs:
                assign_log.delete()

        elif assign_logs.count() > 1:

            raise _("System error. Retrieved more than one assignment log.")

        else:

            # Log Unassignment

            ActionLog(
                timestamp = datetime.now(),
                user = self.request.user,
                action = "UNASSIGN_HOSTINGROUP",
                groupid = self.object.group.id,
                memberid = self.object.host.id
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

        # Filter an "UNASSIGN"-logentry for the same host.

        unassign_logs = ActionLog.objects.filter(
            action = "UNASSIGN_HOSTINGROUP",
            groupid = self.object.group.id,
            memberid = self.object.host.id
        )

        if unassign_logs.count() == 1:

            # There already is an assignment for that. Remove that one

            for unassign_log in unassign_logs:
                unassign_log.delete()

        elif unassign_logs.count() > 1:

            raise _("System error. Retrieved more than one assignment log.")

        else:

            # Log Assignment

            ActionLog(
                timestamp = datetime.now(),
                user = self.request.user,
                action = "ASSIGN_HOSTINGROUP",
                groupid = self.object.group.id,
                memberid = self.object.host.id
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

        # Filter an "ASSIGN"-logentry for the same host.

        assign_logs = ActionLog.objects.filter(
            action = "ASSIGN_HOSTINGROUP",
            groupid = self.object.group.id,
            memberid = self.object.host.id
        )

        if assign_logs.count() == 1:

            # There already is an assignment for that. Remove that one

            for assign_log in assign_logs:
                assign_log.delete()

        elif assign_logs.count() > 1:

            raise _("System error. Retrieved more than one assignment log.")

        else:

            # Log Unassignment

            ActionLog(
                timestamp = datetime.now(),
                user = self.request.user,
                action = "UNASSIGN_HOSTINGROUP",
                groupid = self.object.group.id,
                memberid = self.object.host.id
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

        # Filter an "UNASSIGN"-logentry for the same host.

        unassign_logs = ActionLog.objects.filter(
            action = "UNASSIGN_USERGROUPINHOSTGROUP",
            groupid = self.object.hostgroup.id,
            memberid = self.object.usergroup.id
        )

        if unassign_logs.count() == 1:

            # There already is an assignment for that. Remove that one

            for unassign_log in unassign_logs:
                unassign_log.delete()

        elif unassign_logs.count() > 1:

            raise _("System error. Retrieved more than one assignment log.")

        else:

            # Log Assignment

            ActionLog(
                timestamp = datetime.now(),
                user = self.request.user,
                action = "ASSIGN_USERGROUPINHOSTGROUP",
                groupid = self.object.hostgroup.id,
                memberid = self.object.usergroup.id
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

        # Filter an "ASSIGN"-logentry for the same host.

        assign_logs = ActionLog.objects.filter(
            action = "ASSIGN_USERGROUPINHOSTGROUP",
            groupid = self.object.hostgroup.id,
            memberid = self.object.usergroup.id
        )

        if assign_logs.count() == 1:

            # There already is an assignment for that. Remove that one

            for assign_log in assign_logs:
                assign_log.delete()

        elif assign_logs.count() > 1:

            raise _("System error. Retrieved more than one assignment log.")

        else:

            # Log Unassignment

            ActionLog(
                timestamp = datetime.now(),
                user = self.request.user,
                action = "UNASSIGN_USERGROUPINHOSTGROUP",
                groupid = self.object.hostgroup.id,
                memberid = self.object.usergroup.id
            ).save()

        # Delete object

        self.object.delete()

        return HttpResponseRedirect(self.get_success_url())