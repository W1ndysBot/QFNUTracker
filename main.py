import logging
import os
import sys
import asyncio
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# 添加项目根目录到sys.path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from app.config import owner_id
from app.api import *
from app.switch import load_switch, save_switch, get_all_group_switches

# 数据存储路径，实际开发时，请将QFNU_JWC_Tracker替换为具体的数据存放路径
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "QFNUJWCTracker",
)

# 目标网站地址
url = "https://jwc.qfnu.edu.cn/tz_j_.htm"

# 用于存储上一次页面内容的变量
last_content = None


# 检查权限
def is_group_owner(role):
    return role == "owner"


def is_group_admin(role):
    return role == "admin"


def is_authorized(role, user_id):
    return is_group_admin(role) or is_group_owner(role) or (user_id in owner_id)


# 功能开关状态
def load_function_status(group_id):
    return load_switch(group_id, "教务处公告监控")


def save_function_status(group_id, status):
    save_switch(group_id, "教务处公告监控", status)


# 获取网页内容
def fetch_content():
    global last_content
    response = requests.get(url)
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")
    found_content = soup.find("ul", {"class": "n_listxx1"})
    current_content = found_content.encode("utf-8") if found_content else None

    if last_content is None:
        last_content = current_content
        return None

    if current_content != last_content:
        last_content = current_content
        return current_content
    return None


# 监控教务处公告
last_check_time = {}


async def monitor_jwc_announcements(websocket, group_id):
    global last_check_time
    current_time = datetime.now()

    # 检查当前时间的分钟数是否是5的倍数，表示每五分钟检查一次
    if current_time.minute % 5 != 0:
        return

    # 检查是否在同一分钟内已经检查过
    if (
        group_id in last_check_time
        and last_check_time[group_id].minute == current_time.minute
    ):
        return

    last_check_time[group_id] = current_time
    logging.info(f"群 {group_id} 执行QFNU教务处公告监控")
    updated_content = fetch_content()
    if updated_content:
        logging.info(f"群 {group_id} 检测到教务处公告有更新")
        soup = BeautifulSoup(updated_content, "html.parser")
        announcements = soup.find_all("li")
        if announcements:
            announcement = announcements[0]
            title = announcement.find("a").text.strip()
            link = "https://jwc.qfnu.edu.cn/" + announcement.find("a")["href"]
            summary = announcement.find("p").text.strip()
            await send_group_msg(
                websocket,
                group_id,
                f"曲阜师范大学教务处公告有新内容啦：\n标题：{title}\n摘要：{summary}\n链接：{link}\n\n机器人播报技术支持：https://github.com/W1ndys-bot/W1ndys-Bot",
            )


# 群消息处理函数
async def handle_QFNUJWCTracker_group_message(websocket, msg):
    try:
        user_id = msg.get("user_id")
        group_id = str(msg.get("group_id"))
        raw_message = msg.get("raw_message")
        role = str(msg.get("sender", {}).get("role"))
        message_id = str(msg.get("message_id"))

        if is_authorized(role, user_id):
            if raw_message == "qfnujwc-on":
                if load_function_status(group_id):
                    await send_group_msg(
                        websocket,
                        group_id,
                        "[CQ:reply,id="
                        + message_id
                        + "]QFNU教务处公告监控已经在运行，无需重复开启",
                    )
                    return

                else:
                    save_function_status(group_id, True)
                    await monitor_jwc_announcements(websocket, group_id)
                    logging.info(f"已开启群 {group_id} 的QFNU教务处公告监控任务")
                    await send_group_msg(
                        websocket,
                        group_id,
                        "[CQ:reply,id=" + message_id + "]QFNU教务处公告监控已开启",
                    )

                    return

            if raw_message == "qfnujwc-off":
                if load_function_status(group_id):
                    save_function_status(group_id, False)
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


# 程序开机自动执行的函数，每个心跳周期检查一次
async def start_qfnujwc_tracker(websocket):
    all_switches = get_all_group_switches()
    for group_id, switches in all_switches.items():
        group_id = str(group_id)
        if switches.get("教务处公告监控"):
            await monitor_jwc_announcements(websocket, group_id)
