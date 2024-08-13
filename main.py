import logging
import os
import sys
import asyncio
import requests
from bs4 import BeautifulSoup

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
    "QFNU_JWC_Tracker",
)

# 目标网站地址
url = "https://jwc.qfnu.edu.cn/tz_j_.htm"

# 用于存储上一次页面内容的变量
last_content = None

# 用于存储任务
running_tasks = {}


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
async def monitor_jwc_announcements(websocket, group_id, loop):
    if load_function_status(group_id):
        logging.info(f"执行QFNU教务处公告监控")
        updated_content = fetch_content()
        if updated_content:
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

    loop.call_later(
        5,  # 60秒后执行
        lambda: asyncio.create_task(
            monitor_jwc_announcements(websocket, group_id, loop)
        ),
    )


async def job(websocket, group_id):
    task = asyncio.create_task(
        monitor_jwc_announcements(websocket, group_id, asyncio.get_event_loop())
    )
    running_tasks[group_id] = task


# 群消息处理函数
async def handle_QFNUJWCTracker_group_message(websocket, msg):
    try:
        user_id = msg.get("user_id")
        group_id = msg.get("group_id")
        raw_message = msg.get("raw_message")
        role = msg.get("sender", {}).get("role")
        message_id = str(msg.get("message_id"))

        if is_authorized(role, user_id):
            if raw_message == "qfnujwc-on":
                save_function_status(group_id, True)
                task = asyncio.create_task(job(websocket, group_id))
                running_tasks[group_id] = task
                await send_group_msg(
                    websocket,
                    group_id,
                    "[CQ:reply,id=" + message_id + "]QFNU教务处公告监控已开启",
                )
                return

            if raw_message == "qfnujwc-off":
                save_function_status(group_id, False)
                if group_id in running_tasks:
                    running_tasks[group_id].cancel()
                    del running_tasks[group_id]
                    logging.info(f"已取消群 {group_id} 的QFNU教务处公告监控任务")
                await send_group_msg(
                    websocket,
                    group_id,
                    "[CQ:reply,id=" + message_id + "]QFNU教务处公告监控已关闭",
                )
                return

    except Exception as e:
        logging.error(f"处理QFNU_JWC_Tracker群消息失败: {e}")


# 程序开机自动执行的函数
async def start_qfnujwc_tracker(websocket, msg):
    all_switches = get_all_group_switches()
    for group_id, switches in all_switches.items():
        if switches.get("教务处公告监控"):
            logging.info(f"检测到群{group_id}开启了教务处公告监控，开始执行")
        await job(websocket, group_id)
