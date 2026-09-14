"""

Account roles and document-party roles.

There are exactly two account roles. `lawyer` is the primary authority — owner
of the books and documents they upload, and the one who runs the admin panel;
there is no separate admin tier above it. `user` is a client: read-only, and
only on documents they have been whitelisted on.

"""

ROLE_LAWYER = "lawyer"
ROLE_USER = "user"

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
