import os
import sys
import logging

# 添加项目根目录到sys.path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from app.scripts.QFNUTracker.monitor_announcements import monitor_announcements
from app.scripts.QFNUTracker.switch import load_function_status, save_function_status
from app.scripts.QFNUTracker.auth import is_authorized
from app.api import send_group_msg


jwc_url = "https://jwc.qfnu.edu.cn/tz_j_.htm"

last_jwc_content = None
last_jwc_check_time = None


# 处理开关
async def handle_QFNUTracker_group_message(websocket, msg):
    try:
        user_id = msg.get("user_id")
        group_id = str(msg.get("group_id"))
        raw_message = msg.get("raw_message")
        role = str(msg.get("sender", {}).get("role"))
        message_id = str(msg.get("message_id"))
        if is_authorized(role, user_id):
            if raw_message == "qfnujwcon":
                if load_function_status(group_id, "QFNU教务处"):
                    await send_group_msg(
                        websocket,
                        group_id,
                        "[CQ:reply,id="
                        + message_id
                        + "]QFNU教务处公告监控已经在运行，无需重复开启",
                    )
                    return
                else:
                    save_function_status(group_id, True, "QFNU教务处")
                    logging.info(f"已开启群 {group_id} 的QFNU教务处公告监控任务")
                    await send_group_msg(
                        websocket,
                        group_id,
                        "[CQ:reply,id=" + message_id + "]QFNU教务处公告监控已开启",
                    )
                    return

            if raw_message == "qfnujwcoff":
                if load_function_status(group_id, "QFNU教务处"):
                    save_function_status(group_id, False, "QFNU教务处")
                    logging.info(f"已取消群 {group_id} 的QFNU教务处公告监控任务")
                    await send_group_msg(
                        websocket,
                        group_id,
                        "[CQ:reply,id=" + message_id + "]QFNU教务处公告监控已关闭",
                    )
                    return
                else:
                    await send_group_msg(
                        websocket,
                        group_id,
                        "[CQ:reply,id="
                        + message_id
                        + "]QFNU教务处公告监控未开启，无需重复关闭",
                    )
                    return

    except Exception as e:
        logging.error(f"处理QFNU_JWC_Tracker群消息失败: {e}")


async def start_monitoring(websocket):
    global last_jwc_content, last_jwc_check_time
    last_jwc_content, last_jwc_check_time = await monitor_announcements(
        websocket, jwc_url, last_jwc_content, "QFNU教务处", last_jwc_check_time
    )
