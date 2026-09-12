"""Account roles and document-party roles.

`admin` is the super admin: it carries every lawyer capability plus the
platform-wide ones, so any lawyer check must also pass for an admin.
`lawyer` is the primary authority over documents — owner of the books and
documents they upload.  `user` is a client: read-only, and only on documents
they have been whitelisted on.
"""

ROLE_LAWYER = "lawyer"
ROLE_USER = "user"

# Admin and lawyer are one role now: the lawyer is the primary authority and
# also runs the admin panel (dashboard, users, invitations). These strings are
# still accepted so accounts created before the merge keep working — existing
# rows use "super_admin", which matched neither check previously and left those
# accounts locked out of both lawyer and admin endpoints.
LEGACY_ADMIN_ROLES = ("admin", "super_admin")

# Every role that holds lawyer authority.
LAWYER_ROLES = (ROLE_LAWYER, *LEGACY_ADMIN_ROLES)

# Kept as an alias so older imports resolve; there is no separate admin tier.
ROLE_ADMIN = ROLE_LAWYER

# Roles a user can hold on a single document they do not own.
PARTY_ROLE_VIEWER = "viewer"
PARTY_ROLE_SIGNER = "signer"
PARTY_ROLE_EDITOR = "editor"

PARTY_ROLES = (PARTY_ROLE_VIEWER, PARTY_ROLE_SIGNER, PARTY_ROLE_EDITOR)

# Party roles that may only be granted to a lawyer/admin account.
PRIVILEGED_PARTY_ROLES = (PARTY_ROLE_SIGNER, PARTY_ROLE_EDITOR)

# Party invitations are not access until accepted. A pending invitation grants
# nothing — the document stays invisible to the invitee until they respond.
PARTY_STATUS_PENDING = "pending"
PARTY_STATUS_ACCEPTED = "accepted"
PARTY_STATUS_DECLINED = "declined"

PARTY_STATUSES = (
    PARTY_STATUS_PENDING,
    PARTY_STATUS_ACCEPTED,
    PARTY_STATUS_DECLINED,
)
