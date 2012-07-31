from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
#from django.contrib import admin
#admin.autodiscover()
from django.views.generic.edit import UpdateView, DeleteView, CreateView
from django.views.generic.list import ListView
from keys.models import User, Host, UserGroup
from keys.views import UserKeyListView,UserKeyCreateView, UserKeyUpdateView, UserKeyDeleteView, UserGroupListView, UserGroupAssignView, UserGroupUnassignView, UserGroupUserListView

urlpatterns = patterns('keys.views',

    # Home page

    url(
        r"^$",
        "home",
        name = "home"
    ),

    # User management

    url(
        r"^users/list$",
        ListView.as_view(
            queryset = User.objects.all(),
            context_object_name = "users"
        ),
        name = "users_list"
    ),

    url(
        r"^users/create",
        CreateView.as_view(
            model = User,
            success_url = "/users/list"
        ),
        name = "users_create"
    ),

    url(
        r"^users/edit/(?P<pk>.*)$",
        UpdateView.as_view(
            model = User,
            success_url = "/users/list"
        ),
        name = "users_edit"
    ),

    url(
        r'^users/delete/(?P<pk>.*)$',
        DeleteView.as_view(
            model = User,
            success_url = "/users/list"
        ),
        name = 'users_delete'
    ),

    url(
        r"^users/keys/(?P<user>.*)/list$",
        UserKeyListView.as_view(),
        name = "users_keys_list"
    ),

    url(
        r"^users/keys/(?P<user>.*)/create$",
        UserKeyCreateView.as_view(),
        name = "users_keys_create"
    ),

    url(
        r"^users/keys/(?P<user>.*)/edit/(?P<pk>.*)$",
        UserKeyUpdateView.as_view(),
        name = "users_keys_edit"
    ),

    url(
        r"^users/keys/(?P<user>.*)/delete/(?P<pk>.*)$",
        UserKeyDeleteView.as_view(),
        name = "users_keys_delete"
    ),

    url(
        r"^users/groups/(?P<user>.*)/list$",
        UserGroupListView.as_view(),
        name = "users_groups_list"
    ),

    url(
        r"^users/groups/(?P<user>.*)/assign$",
        UserGroupAssignView.as_view(),
        name = "users_groups_assign"
    ),

    url(
        r"^users/groups/(?P<user>.*)/unassign/(?P<pk>.*)$",
        UserGroupUnassignView.as_view(),
        name = "users_groups_unassign"
    ),

    # User-Group management

    url(
        r"^usergroups/list$",
        ListView.as_view(
            queryset = UserGroup.objects.all(),
            context_object_name = "usergroups"
        ),
        name = "usergroups_list"
    ),

    url(
        r"^usergroups/create$",
        CreateView.as_view(
            model = UserGroup,
            success_url = "/usergroups/list"
        ),
        name = "usergroups_create"
    ),

    url(
        r"^usergroups/edit/(?P<pk>.*)$",
        UpdateView.as_view(
            model = UserGroup,
            success_url = "/usergroups/list"
        ),
        name = "usergroups_edit"
    ),

    url(
        r"^usergroups/delete/(?P<pk>.*)$",
        DeleteView.as_view(
            model = UserGroup,
            success_url = "/usergroups/list"
        ),
        name = "usergroups_delete"
    ),

    url(
        r"^usergroups/users/(?P<usergroup>.*)/list$",
        UserGroupUserListView.as_view(),
        name = "usergroups_users_list"
    ),

    # Host management

    url(
        r'^hosts/list$',
        ListView.as_view(
            queryset = Host.objects.all(),
            context_object_name = "hosts"
        ),
        name="hosts_list"
    ),

    url(
        r'^hosts/create$',
        CreateView.as_view(
            model = Host,
            success_url = "/hosts/list"
        ),
        name = "hosts_create"
    )

    #url(r'^hosts/list$', 'list_hosts', name='list_hosts'),
    #url(r'^apply$', 'apply', name='apply')
    # url(r'^skd/', include('skd.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    #url(r'^admin/', include(admin.site.urls)),
)
