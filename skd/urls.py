import django
from django.conf.urls import patterns, include, url

from django.contrib import admin
from django.contrib.auth.decorators import login_required, \
    permission_required, user_passes_test
admin.autodiscover()

from django.views.generic.base import TemplateView
from django.views.generic.edit import UpdateView, DeleteView, CreateView
from django.views.generic.list import ListView
from keys.models import User, Host, UserGroup, HostGroup
from keys.views import UserKeyListView,UserKeyCreateView, UserKeyUpdateView, \
    UserKeyDeleteView, UserGroupListView, UserGroupAssignView, \
    UserGroupUnassignView, UserGroupUserListView, UserGroupUserAssignView, \
    UserGroupUserUnassignView, HostGroupUnassignView, HostGroupAssignView, \
    HostGroupListView, HostGroupHostListView, HostGroupHostAssignView, \
    HostGroupHostUnassignView, UserGroupHostGroupListView, \
    UserGroupHostGroupAssignView, UserGroupHostGroupUnassignView, \
    HostGroupUserGroupListView, HostGroupUserGroupAssignView, \
    HostGroupUserGroupUnassignView, SetupView, HostSetupView, ApplyView, \
    UserDeleteView, HostDeleteView, UserGroupDeleteView, HostGroupDeleteView


urlpatterns = patterns('keys.views',

    # Home page

    url(
        r"^$",
        login_required(
            TemplateView.as_view(
                template_name="keys/home.html"
            )
        ),
        name = "home"
    ),

    # SKD setup

    url(
        r"^setup$",
        user_passes_test(lambda u: u.is_staff)(
            SetupView.as_view()
        ),
        name = "setup"
    ),

    # User management

    url(
        r"^users/list$",
        permission_required("keys.list_users")(
            ListView.as_view(
                queryset = User.objects.all(),
                context_object_name = "users"
            )
        ),
        name = "users_list"
    ),

    url(
        r"^users/create",
        permission_required("keys.add_user")(
            CreateView.as_view(
                model = User,
                success_url = "/users/list"
            )
        ),
        name = "users_create"
    ),

    url(
        r"^users/edit/(?P<pk>.*)$",
        permission_required("keys.change_user")(
            UpdateView.as_view(
                model = User,
                success_url = "/users/list"
            )
        ),
        name = "users_edit"
    ),

    url(
        r'^users/delete/(?P<pk>.*)$',
        permission_required("keys.delete_user")(
            UserDeleteView.as_view()
        ),
        name = 'users_delete'
    ),

    url(
        r"^users/keys/(?P<user>.*)/list$",
        permission_required("keys.list_users_keys")(
            UserKeyListView.as_view()
        ),
        name = "users_keys_list"
    ),

    url(
        r"^users/keys/(?P<user>.*)/create$",
        permission_required("keys.add_key")(
            UserKeyCreateView.as_view()
        ),
        name = "users_keys_create"
    ),

    url(
        r"^users/keys/(?P<user>.*)/edit/(?P<pk>.*)$",
        permission_required("keys.change_key")(
            UserKeyUpdateView.as_view()
        ),
        name = "users_keys_edit"
    ),

    url(
        r"^users/keys/(?P<user>.*)/delete/(?P<pk>.*)$",
        permission_required("keys.delete_key")(
            UserKeyDeleteView.as_view()
        ),
        name = "users_keys_delete"
    ),

    url(
        r"^users/groups/(?P<user>.*)/list$",
        permission_required("keys.list_users_in_usergroups")(
            UserGroupListView.as_view()
        ),
        name = "users_groups_list"
    ),

    url(
        r"^users/groups/(?P<user>.*)/assign$",
        permission_required("keys.add_useringroup")(
            UserGroupAssignView.as_view()
        ),
        name = "users_groups_assign"
    ),

    url(
        r"^users/groups/(?P<user>.*)/unassign/(?P<pk>.*)$",
        permission_required("keys.delete_useringroup")(
            UserGroupUnassignView.as_view()
        ),
        name = "users_groups_unassign"
    ),

    # Usergroup management

    url(
        r"^usergroups/list$",
        permission_required("keys.list_usergroups")(
            ListView.as_view(
                queryset = UserGroup.objects.all(),
                context_object_name = "usergroups"
            )
        ),
        name = "usergroups_list"
    ),

    url(
        r"^usergroups/create$",
        permission_required("keys.add_usergroup")(
            CreateView.as_view(
                model = UserGroup,
                success_url = "/usergroups/list"
            )
        ),
        name = "usergroups_create"
    ),

    url(
        r"^usergroups/edit/(?P<pk>.*)$",
        permission_required("keys.change_usergroup")(
            UpdateView.as_view(
                model = UserGroup,
                success_url = "/usergroups/list"
            )
        ),
        name = "usergroups_edit"
    ),

    url(
        r"^usergroups/delete/(?P<pk>.*)$",
        permission_required("keys.delete_usergroup")(
            UserGroupDeleteView.as_view()
        ),
        name = "usergroups_delete"
    ),

    url(
        r"^usergroups/users/(?P<usergroup>.*)/list$",
        permission_required("keys.list_users_in_usergroups")(
            UserGroupUserListView.as_view()
        ),
        name = "usergroups_users_list"
    ),

    url(
        r"^usergroups/users/(?P<usergroup>.*)/assign$",
        permission_required("keys.add_useringroup")(
            UserGroupUserAssignView.as_view()
        ),
        name = "usergroups_users_assign"
    ),

    url(
        r"^usergroups/users/(?P<usergroup>.*)/unassign/(?P<pk>.*)$",
        permission_required("keys.delete_useringroup")(
            UserGroupUserUnassignView.as_view()
        ),
        name = "usergroups_users_unassign"
    ),

    url(
        "^usergroups/hostgroups/(?P<usergroup>.*)/list$",
        permission_required("keys.list_usergroups_in_hostgroups")(
            UserGroupHostGroupListView.as_view()
        ),
        name = "usergroups_hostgroups_list"
    ),

    url(
        "^usergroups/hostgroups/(?P<usergroup>.*)/assign$",
        permission_required("keys.add_usergroupinhostgroup")(
            UserGroupHostGroupAssignView.as_view()
        ),
        name = "usergroups_hostgroups_assign"
    ),

    url(
        "^usergroups/hostgroups/(?P<usergroup>.*)/unassign/(?P<pk>.*)$",
        permission_required("keys.delete_usergroupinhostgroup")(
            UserGroupHostGroupUnassignView.as_view()
        ),
        name = "usergroups_hostgroups_unassign"
    ),

    # Host management

    url(
        r"^hosts/list$",
        permission_required("keys.list_hosts")(
            ListView.as_view(
                queryset = Host.objects.all(),
                context_object_name = "hosts"
            )
        ),
        name="hosts_list"
    ),

    url(
        r"^hosts/create$",
        permission_required("keys.add_host")(
            CreateView.as_view(
                model = Host,
                success_url = "/hosts/list"
            )
        ),
        name = "hosts_create"
    ),

    url(
        r"^hosts/edit/(?P<pk>.*)$",
        permission_required("keys.change_host")(
            UpdateView.as_view(
                model = Host,
                success_url = "/hosts/list"
            )
        ),
        name = "hosts_edit"
    ),

    url(
        r"^hosts/delete/(?P<pk>.*)$",
        permission_required("keys.delete_host")(
            HostDeleteView.as_view()
        ),
        name = "hosts_delete"
    ),

    url(
        r"^hosts/setup/(?P<host>.*)$",
        permission_required("setup_host")(
            HostSetupView.as_view()
        ),
        name = "hosts_setup"
    ),

    url(
        r"^hosts/groups/(?P<host>.*)/list$",
        permission_required("keys.list_hosts_in_groups")(
            HostGroupListView.as_view()
        ),
        name = "hosts_groups_list"
    ),

    url(
        r"^hosts/groups/(?P<host>.*)/assign$",
        permission_required("keys.add_hostingroup")(
            HostGroupAssignView.as_view()
        ),
        name = "hosts_groups_assign"
    ),

    url(
        r"^hosts/groups/(?P<host>.*)/unassign/(?P<pk>.*)$",
        permission_required("keys.delete_hostingroup")(
            HostGroupUnassignView.as_view()
        ),
        name = "hosts_groups_unassign"
    ),

    # Hostgroup management

    url(
        r"^hostgroups/list$",
        permission_required("keys.list_hostgroups")(
            ListView.as_view(
                queryset = HostGroup.objects.all(),
                context_object_name = "hostgroups"
            )
        ),
        name = "hostgroups_list"
    ),

    url(
        r"^hostgroups/create$",
        permission_required("keys.add_hostgroup")(
            CreateView.as_view(
                model = HostGroup,
                success_url = "/hostgroups/list"
            )
        ),
        name = "hostgroups_create"
    ),

    url(
        r"^hostgroups/edit/(?P<pk>.*)$",
        permission_required("keys.change_host")(
            UpdateView.as_view(
                model = HostGroup,
                success_url = "/hostgroups/list"
            )
        ),
        name = "hostgroups_edit"
    ),

    url(
        r"^hostgroups/delete/(?P<pk>.*)$",
        permission_required("keys.delete_host")(
            HostGroupDeleteView.as_view()
        ),
        name = "hostgroups_delete"
    ),

    url(
        r"^hostgroups/hosts/(?P<hostgroup>.*)/list$",
        permission_required("keys.list_hosts_in_hostgroups")(
            HostGroupHostListView.as_view()
        ),
        name = "hostgroups_hosts_list"
    ),

    url(
        r"^hostgroups/hosts/(?P<hostgroup>.*)/assign$",
        permission_required("keys.add_hostingroup")(
            HostGroupHostAssignView.as_view()
        ),
        name = "hostgroups_hosts_assign"
    ),

    url(
        r"^hostgroups/hosts/(?P<hostgroup>.*)/unassign/(?P<pk>.*)$",
        permission_required("keys.delete_hostingroup")(
            HostGroupHostUnassignView.as_view()
        ),
        name = "hostgroups_hosts_unassign"
    ),

    url(
        r"^hostgroups/usergroups/(?P<hostgroup>.*)/list$",
        permission_required("keys.list_usergroups_in_hostgroups")(
            HostGroupUserGroupListView.as_view()
        ),
        name = "hostgroups_usergroups_list"
    ),

    url(
        r"^hostgroups/usergroups/(?P<hostgroup>.*)/assign$",
        permission_required("keys.add_usergroupinhostgroup")(
            HostGroupUserGroupAssignView.as_view()
        ),
        name = "hostgroups_usergroups_assign"
    ),

    url(
        r"^hostgroups/usergroups/(?P<hostgroup>.*)/unassign/(?P<pk>.*)$",
        permission_required("keys.delete_usergroupinhostgroup")(
            HostGroupUserGroupUnassignView.as_view()
        ),
        name = "hostgroups_usergroups_unassign"
    ),

    url(
        r"^apply$",
        ApplyView.as_view(),
        name = "apply"
    )

)

urlpatterns += patterns('',

    url(
        r"^logout$",
        "django.contrib.auth.views.logout",
        {
            "next_page" : "/"
        },
        name = "logout"
    ),

    url(
        r"^login$",
        "django.contrib.auth.views.login",
        name = "login"
    ),

    url(
        r"^password/change$",
        "django.contrib.auth.views.password_change",
        name = "password_change"
    ),

    url(
        r"^password/change/done$",
        "django.contrib.auth.views.password_change_done",
        name = "password_change_done"
    ),

    url(
        r'^admin/',
        include(admin.site.urls)
    )

)
