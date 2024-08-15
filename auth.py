import os
import sys

# 添加项目根目录到sys.path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
from app.config import owner_id


# 检查权限
def is_group_owner(role):
    return role == "owner"


def is_group_admin(role):
    return role == "admin"


def is_authorized(role, user_id):
    return is_group_admin(role) or is_group_owner(role) or (user_id in owner_id)
