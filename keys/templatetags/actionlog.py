from django import template
from django.core.urlresolvers import reverse
from django.template.defaultfilters import stringfilter

register = template.Library()

@register.filter()
@stringfilter
def actionlogize(value):
    """
    Converts an ActionLog-Actionkey into a translateable, human string
    """

    dictionary = {

        "DELETE_ACTIONLOG": "Deleted the action-Log.",
        "APPLY": "Applied pending changes.",
        "CREATE_USER": "Created a user.",
        "UPDATE_USER": "Updated a user.",
        "DELETE_USER": "Deleted a user.",
        "CREATE_KEY": "Created a key.",
        "UPDATE_KEY": "Updated a key.",
        "DELETE_KEY_FROM_USER": "Deleted a key from a user.",
        "CREATE_USERGROUP": "Created a usergroup.",
        "UPDATE_USERGROUP": "Updated a usergroup.",
        "DELETE_USERGROUP": "Deleted a usergroup.",
        "ASSIGN_USERINGROUP": "Assigned a user to a usergroup.",
        "UNASSIGN_USERINGROUP": "Remove a user from a usergroup.",
        "ASSIGN_USERGROUPINHOSTGROUP": "Associated a a hostgroup with a "
                                       "usergroup",
        "UNASSIGN_USERGROUPINHOSTGROUP": "Removed the association of a "
                                         "hostgroup with a usergroup.",
        "CREATE_HOST": "Created a host.",
        "UPDATE_HOST": "Updated a host.",
        "DELETE_HOST": "Deleted a host.",
        "CREATE_HOSTGROUP": "Created a hostgroup.",
        "UPDATE_HOSTGROUP": "Updated a hostgroup.",
        "DELETE_HOSTGROUP": "Deleted a hostgroup.",
        "ASSIGN_HOSTINGROUP": "Assigned a host to a hostgroup.",
        "UNASSIGN_HOSTINGROUP": "Removed a host from a hostgroup."

    }

    if value in dictionary:
        return dictionary[value]

    else:
        return value

@register.tag()
def get_actionobject(parser, token):
    try:
        tag_name, action, object_id, object_id2 = token.split_contents()

    except ValueError:
        raise template.TemplateSyntaxError("%r tag requires the action-code "
                                           "and both object-ids " %
                                           token.contents.split()[0]
        )

    return GetActionObjectNode(action, object_id, object_id2)

class GetActionObjectNode(template.Node):

    def __init__(self, action, object_id, object_id2):
        self.action = template.Variable(action)
        self.object_id = template.Variable(object_id)
        self.object_id2 = template.Variable(object_id2)

    def render(self, context):
           
        try:
        
            action = self.action.resolve(context)
            
        except template.VariableDoesNotExist:
            
            action = ""

        try:

            object_id = self.object_id.resolve(context)

        except template.VariableDoesNotExist:

            object_id = ""

        try:

            object_id2 = self.object_id2.resolve(context)

        except template.VariableDoesNotExist:

            object_id2 = ""
            
        dictionary = {

            "CREATE_USER": {
                "view": "users_edit",
                "params": {
                    "pk": object_id
                }
            },
            "UPDATE_USER": {
                "view": "users_edit",
                "params": {
                    "pk": object_id
                }
            },
            "CREATE_KEY": {
                "view": "users_keys_edit",
                "params": {
                    "pk": object_id,
                    "user": object_id2
                }
            },
            "UPDATE_KEY": {
                "view": "users_keys_edit",
                "params": {
                    "pk": object_id,
                    "user": object_id2
                }
            },
            "CREATE_USERGROUP": {
                "view": "usergroups_edit",
                "params": {
                    "pk": object_id
                }
            },
            "UPDATE_USERGROUP": {
                "view": "usergroups_edit",
                "params": {
                    "pk": object_id
                }
            },
            "ASSIGN_USERINGROUP": {
                "view": "users_groups_list",
                "params": {
                    "user": object_id
                }
            },
            "UNASSIGN_USERINGROUP": {
                "view": "users_groups_list",
                "params": {
                    "user": object_id
                }
            },
            "ASSIGN_USERGROUPINHOSTGROUP": {
                "view": "usergroups_hostgroups_list",
                "params": {
                    "usergroup": object_id
                }
            },
            "UNASSIGN_USERGROUPINHOSTGROUP": {
                "view": "usergroups_hostgroups_list",
                "params": {
                    "usergroup": object_id
                }
            },
            "CREATE_HOST": {
                "view": "hosts_edit",
                "params": {
                    "pk": object_id
                }
            },
            "UPDATE_HOST": {
                "view": "hosts_edit",
                "params": {
                    "pk": object_id
                }
            },
            "CREATE_HOSTGROUP": {
                "view": "hostgroups_edit",
                "params": {
                    "pk": object_id
                }
            },
            "UPDATE_HOSTGROUP": {
                "view": "hostgroups_edit",
                "params": {
                    "pk": object_id
                }
            },
            "ASSIGN_HOSTINGROUP": {
                "view": "hosts_groups_list",
                "params": {
                    "host": object_id
                }
            },
            "UNASSIGN_HOSTINGROUP": {
                "view": "hosts_groups_list",
                "params": {
                    "host": object_id
                }
            }

        }

        if action in dictionary:

            return reverse(
                dictionary[action]["view"],
                kwargs = dictionary[action]["params"]
            )

        else:

            return ""
