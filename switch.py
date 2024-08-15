import os
import sys

# 添加项目根目录到sys.path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from app.switch import load_switch, save_switch


# 功能开关状态
def load_function_status(group_id, site_name):
    return load_switch(group_id, f"{site_name}监控")


def save_function_status(group_id, status, site_name):
    save_switch(group_id, f"{site_name}监控", status)
