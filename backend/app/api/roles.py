from fastapi import Depends, HTTPException, status

from app.api.auth import UserInfo, get_current_user

# student and admin roles (backlog item 4)

# the only two roles the users table allows
STUDENT = 'student'
ADMIN = 'admin'
ALL_ROLES = (STUDENT, ADMIN)


# builds a check that only lets in users who have one of the allowed roles
def require_role(*allowed_roles: str):
    def check_role(user: UserInfo = Depends(get_current_user)) -> UserInfo:
        # logged in but wrong role is 403, not logged in at all is still 401 from get_current_user
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Your account does not have permission to do this',
            )
        return user

    return check_role


# endpoints add one of these, for example user: UserInfo = Depends(require_admin)
require_student = require_role(STUDENT)
require_admin = require_role(ADMIN)