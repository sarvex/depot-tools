# Copyright 2010 Google Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, 
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

from boto.gs.user import User
from boto.exception import InvalidAclError

ACCESS_CONTROL_LIST = 'AccessControlList'
ALL_AUTHENTICATED_USERS = 'AllAuthenticatedUsers'
ALL_USERS = 'AllUsers'
DISPLAY_NAME = 'DisplayName'
DOMAIN = 'Domain'
EMAIL_ADDRESS = 'EmailAddress'
ENTRY = 'Entry'
ENTRIES = 'Entries'
GROUP_BY_DOMAIN = 'GroupByDomain'
GROUP_BY_EMAIL = 'GroupByEmail'
GROUP_BY_ID = 'GroupById'
ID = 'ID'
NAME = 'Name'
OWNER = 'Owner'
PERMISSION = 'Permission'
SCOPE = 'Scope'
TYPE = 'type'
USER_BY_EMAIL = 'UserByEmail'
USER_BY_ID = 'UserById'


CannedACLStrings = ['private', 'public-read', 'project-private',
                    'public-read-write', 'authenticated-read',
                    'bucket-owner-read', 'bucket-owner-full-control']
"""A list of Google Cloud Storage predefined (canned) ACL strings."""

SupportedPermissions = ['READ', 'WRITE', 'FULL_CONTROL']
"""A list of supported ACL permissions."""

class ACL:

    def __init__(self, parent=None):
        self.parent = parent
        self.entries = []

    @property
    def acl(self):
        return self

    def __repr__(self):
        # Owner is optional in GS ACLs.
        if hasattr(self, 'owner'):
            entries_repr = [f'Owner:{self.owner.__repr__()}']
        else:
            entries_repr = ['']
        if acl_entries := self.entries:
            entries_repr.extend(e.__repr__() for e in acl_entries.entry_list)
        return f"<{', '.join(entries_repr)}>"

    # Method with same signature as boto.s3.acl.ACL.add_email_grant(), to allow
    # polymorphic treatment at application layer.
    def add_email_grant(self, permission, email_address):
        entry = Entry(type=USER_BY_EMAIL, email_address=email_address,
                      permission=permission)
        self.entries.entry_list.append(entry)

    # Method with same signature as boto.s3.acl.ACL.add_user_grant(), to allow
    # polymorphic treatment at application layer.
    def add_user_grant(self, permission, user_id):
        entry = Entry(permission=permission, type=USER_BY_ID, id=user_id)
        self.entries.entry_list.append(entry)

    def add_group_email_grant(self, permission, email_address):
        entry = Entry(type=GROUP_BY_EMAIL, email_address=email_address,
                      permission=permission)
        self.entries.entry_list.append(entry)

    def add_group_grant(self, permission, group_id):
        entry = Entry(type=GROUP_BY_ID, id=group_id, permission=permission)
        self.entries.entry_list.append(entry)

    def startElement(self, name, attrs, connection):
        if name.lower() == OWNER.lower():
            self.owner = User(self)
            return self.owner
        elif name.lower() == ENTRIES.lower():
            self.entries = Entries(self)
            return self.entries
        else:
            return None

    def endElement(self, name, value, connection):
        if name.lower() == OWNER.lower():
            pass
        elif name.lower() != ENTRIES.lower():
            setattr(self, name, value)

    def to_xml(self):
        s = f'<{ACCESS_CONTROL_LIST}>'
        # Owner is optional in GS ACLs.
        if hasattr(self, 'owner'):
            s += self.owner.to_xml()
        if acl_entries := self.entries:
            s += acl_entries.to_xml()
        s += f'</{ACCESS_CONTROL_LIST}>'
        return s


class Entries:

    def __init__(self, parent=None):
        self.parent = parent
        # Entries is the class that represents the same-named XML
        # element. entry_list is the list within this class that holds the data.
        self.entry_list = []

    def __repr__(self):
        entries_repr = [e.__repr__() for e in self.entry_list]
        return f"<Entries: {', '.join(entries_repr)}>"

    def startElement(self, name, attrs, connection):
        if name.lower() != ENTRY.lower():
            return None
        entry = Entry(self)
        self.entry_list.append(entry)
        return entry

    def endElement(self, name, value, connection):
        if name.lower() != ENTRY.lower():
            setattr(self, name, value)

    def to_xml(self):
        s = f'<{ENTRIES}>'
        for entry in self.entry_list:
            s += entry.to_xml()
        s += f'</{ENTRIES}>'
        return s
        

# Class that represents a single (Scope, Permission) entry in an ACL.
class Entry:

    def __init__(self, scope=None, type=None, id=None, name=None,
                 email_address=None, domain=None, permission=None):
        if not scope:
            scope = Scope(self, type, id, name, email_address, domain)
        self.scope = scope
        self.permission = permission

    def __repr__(self):
        return f'<{self.scope.__repr__()}: {self.permission.__repr__()}>'

    def startElement(self, name, attrs, connection):
        if name.lower() == SCOPE.lower():
            # The following if statement used to look like this: 
            #   if not TYPE in attrs:
            # which caused problems because older versions of the 
            # AttributesImpl class in the xml.sax library neglected to include 
            # a __contains__() method (which Python calls to implement the 
            # 'in' operator). So when you use the in operator, like the if
            # statement above, Python invokes the __getiter__() method with
            # index 0, which raises an exception. More recent versions of 
            # xml.sax include the __contains__() method, rendering the in 
            # operator functional. The work-around here is to formulate the
            # if statement as below, which is the legal way to query 
            # AttributesImpl for containment (and is also how the added
            # __contains__() method works). At one time gsutil disallowed
            # xmlplus-based parsers, until this more specific problem was 
            # determined.
            if TYPE not in attrs:
                raise InvalidAclError(f'Missing "{TYPE}" in "{SCOPE}" part of ACL')
            self.scope = Scope(self, attrs[TYPE])
            return self.scope
        elif name.lower() != PERMISSION.lower():
            return None

    def endElement(self, name, value, connection):
        if name.lower() == SCOPE.lower():
            pass
        elif name.lower() == PERMISSION.lower():
            value = value.strip()
            if value not in SupportedPermissions:
                raise InvalidAclError(f'Invalid Permission "{value}"')
            self.permission = value
        else:
            setattr(self, name, value)

    def to_xml(self):
        s = f'<{ENTRY}>'
        s += self.scope.to_xml()
        s += f'<{PERMISSION}>{self.permission}</{PERMISSION}>'
        s += f'</{ENTRY}>'
        return s

class Scope:

    # Map from Scope type.lower() to lower-cased list of allowed sub-elems.
    ALLOWED_SCOPE_TYPE_SUB_ELEMS = {
        ALL_AUTHENTICATED_USERS.lower() : [],
        ALL_USERS.lower() : [],
        GROUP_BY_DOMAIN.lower() : [DOMAIN.lower()],
        GROUP_BY_EMAIL.lower() : [
            DISPLAY_NAME.lower(), EMAIL_ADDRESS.lower(), NAME.lower()],
        GROUP_BY_ID.lower() : [DISPLAY_NAME.lower(), ID.lower(), NAME.lower()],
        USER_BY_EMAIL.lower() : [
            DISPLAY_NAME.lower(), EMAIL_ADDRESS.lower(), NAME.lower()],
        USER_BY_ID.lower() : [DISPLAY_NAME.lower(), ID.lower(), NAME.lower()]
    }

    def __init__(self, parent, type=None, id=None, name=None,
                 email_address=None, domain=None):
        self.parent = parent
        self.type = type
        self.name = name
        self.id = id
        self.domain = domain
        self.email_address = email_address
        if self.type.lower() not in self.ALLOWED_SCOPE_TYPE_SUB_ELEMS:
            raise InvalidAclError(f'Invalid {SCOPE} {TYPE} "{self.type}" ')

    def __repr__(self):
        named_entity = None
        if self.id:
            named_entity = self.id
        elif self.email_address:
            named_entity = self.email_address
        elif self.domain:
            named_entity = self.domain
        return f'<{self.type}: {named_entity}>' if named_entity else f'<{self.type}>'

    def startElement(self, name, attrs, connection):
        if (
            name.lower()
            not in self.ALLOWED_SCOPE_TYPE_SUB_ELEMS[self.type.lower()]
        ):
            raise InvalidAclError(
                f'Element "{name}" not allowed in {SCOPE} {TYPE} "{self.type}" '
            )
        return None

    def endElement(self, name, value, connection):
        value = value.strip()
        if name.lower() == DOMAIN.lower():
            self.domain = value
        elif name.lower() == EMAIL_ADDRESS.lower():
            self.email_address = value
        elif name.lower() == ID.lower():
            self.id = value
        elif name.lower() == NAME.lower():
            self.name = value
        else:
            setattr(self, name, value)

    def to_xml(self):
        s = f'<{SCOPE} type="{self.type}">'
        if self.type.lower() in [
            ALL_AUTHENTICATED_USERS.lower(),
            ALL_USERS.lower(),
        ]:
            pass
        elif self.type.lower() == GROUP_BY_DOMAIN.lower():
            s += f'<{DOMAIN}>{self.domain}</{DOMAIN}>'
        elif self.type.lower() in [GROUP_BY_EMAIL.lower(), USER_BY_EMAIL.lower()]:
            s += f'<{EMAIL_ADDRESS}>{self.email_address}</{EMAIL_ADDRESS}>'
            if self.name:
                s += f'<{NAME}>{self.name}</{NAME}>'
        elif self.type.lower() in [GROUP_BY_ID.lower(), USER_BY_ID.lower()]:
            s += f'<{ID}>{self.id}</{ID}>'
            if self.name:
                s += f'<{NAME}>{self.name}</{NAME}>'
        else:
            raise InvalidAclError('Invalid scope type "%s" ', self.type)

        s += f'</{SCOPE}>'
        return s
