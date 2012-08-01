from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, get_object_or_404
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from keys.models import User,Key, UserGroup, UserInGroup, HostInGroup, Host, HostGroup, UserGroupInHostGroup

# User views

# User/Key

class UserKeyListView(ListView):

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
            "user_keys_list",
            kwargs = {
                "user": self.key_owner.id
            }
        )

class UserKeyUpdateView(UpdateView):

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
            "user_keys_list",
            kwargs = {
                "user": self.key_owner.id
            }
        )

# User/Group

class UserGroupListView(ListView):

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

class UserGroupUnassignView(DeleteView):

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

# Usergroup/User

class UserGroupUserListView(ListView):

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

class UserGroupUserUnassignView(DeleteView):

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

# Usergroup/Hostgroup

class UserGroupHostGroupListView(ListView):

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

class UserGroupHostGroupUnassignView(DeleteView):

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

# Host-Views

# Host/Group

class HostGroupListView(ListView):

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

class HostGroupUnassignView(DeleteView):

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

# Hostgroup/Host

class HostGroupHostListView(ListView):

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

class HostGroupHostUnassignView(DeleteView):

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

# Hostgroup/Usergroup

class HostGroupUserGroupListView(ListView):

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

class HostGroupUserGroupUnassignView(DeleteView):

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