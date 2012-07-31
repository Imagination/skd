from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, get_object_or_404
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from keys.models import User,Key, UserGroup, UserInGroup

# Home page

def home(request):
    return render_to_response('keys/home.html')

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
        context['key_owner'] = self.key_owner
        return context

class UserKeyCreateView(CreateView):

    template_name = "keys/key_form.html"

    def get_queryset(self):
        self.key_owner = get_object_or_404(User, id=self.kwargs["user"])
        return Key.objects.all()

    def get_context_data(self, **kwargs):
        context = super(UserKeyCreateView, self).get_context_data(**kwargs)
        context['key_owner'] = self.key_owner
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
        context['key_owner'] = self.key_owner
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
        context['key_owner'] = self.key_owner
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
        context['group_member'] = self.group_member
        return context

class UserGroupAssignView(CreateView):

    template_name = "keys/user_groups_assign.html"

    def get_queryset(self):
        self.group_member = get_object_or_404(User, id=self.kwargs["user"])
        return UserInGroup.objects.all()

    def get_context_data(self, **kwargs):
        context = super(UserGroupAssignView, self).get_context_data(**kwargs)
        context['group_member'] = self.group_member
        return context

    def get_initial(self):
        return {"user": self.group_member}

    def get_success_url(self):
        return reverse(
            'users_groups_list',
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
        context['group_member'] = self.group_member
        return context

    def get_success_url(self):
        return reverse(
            'users_groups_list',
            kwargs = {
                "user": self.group_member.id
            }
        )

# Usergroup/User
# TODO
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
        context['usergroup'] = self.usergroup
        return context

class UserGroupUserAssignView(CreateView):

    template_name = "keys/usergroup_users_assign.html"

    def get_queryset(self):
        self.usergroup = get_object_or_404(User, id=self.kwargs["usergroup"])
        return UserInGroup.objects.all()

    def get_context_data(self, **kwargs):
        context = super(UserGroupUserAssignView, self).get_context_data(**kwargs)
        context['usergroup'] = self.usergroup
        return context

    def get_initial(self):
        return {"group": self.usergroup}

    def get_success_url(self):
        return reverse(
            'usersgroup_users_list',
            kwargs = {
                "usergroup": self.usergroup.id
            }
        )

class UserGroupUserUnassignView(DeleteView):

    template_name = "keys/usergroup_user_unassign_confirm.html"

    def get_object(self, queryset=None):
        self.usergroup = get_object_or_404(UserGroup, id=self.kwargs["usergroup"])
        return get_object_or_404(
            UserInGroup,
            id=self.kwargs["pk"],
            group=self.usergroup
        )

    def get_context_data(self, **kwargs):
        context = super(UserGroupUserUnassignView, self).get_context_data(**kwargs)
        context['usergroup'] = self.usergroup
        return context

    def get_success_url(self):
        return reverse(
            'usergroups_users_list',
            kwargs = {
                "usergroup": self.usergroup.id
            }
        )