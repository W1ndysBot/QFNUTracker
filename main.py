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
jwc_url = "https://jwc.qfnu.edu.cn/tz_j_.htm"
zcc_url = "https://zcc.qfnu.edu.cn/ztzx/zbgg.htm"

last_jwc_content = None
last_zcc_content = None


# 检查权限
def is_group_owner(role):
    return role == "owner"


def is_group_admin(role):
    return role == "admin"


def is_authorized(role, user_id):
    return is_group_admin(role) or is_group_owner(role) or (user_id in owner_id)


# 功能开关状态
def load_function_status(group_id, site_name):
    return load_switch(group_id, f"{site_name}公告监控")


def save_function_status(group_id, status, site_name):
    save_switch(group_id, f"{site_name}公告监控", status)


# 获取网页内容
def fetch_content(url, last_content):
    try:
        response = requests.get(url)
        response.encoding = "utf-8"
        soup = BeautifulSoup(response.text, "html.parser")
        found_content = soup.find("ul", {"class": "n_listxx1"})
        current_content = found_content.encode("utf-8") if found_content else None

        if last_content is None:
            return current_content, None

        if current_content != last_content:
            return current_content, current_content
        return last_content, None
    except requests.RequestException as e:
        logging.error(f"获取{url}网页内容失败: {e}")
        return last_content, None


# 监控教务处公告
last_jwc_check_time = None
last_zcc_check_time = None


async def monitor_announcements(
    websocket, url, last_content, site_name, last_check_time
):
    current_time = datetime.now()

    # 检查当前时间的分钟数是否是5的倍数，表示每五分钟检查一次
    if current_time.minute % 1 != 0:
        return last_content, last_check_time

    # 检查是否在同一分钟内已经检查过
    if last_check_time and last_check_time.minute == current_time.minute:
        return last_content, last_check_time

    last_check_time = current_time
    last_content, updated_content = fetch_content(url, last_content)
    logging.info(f"执行{site_name}公告监控")
    if updated_content:
        logging.info(f"检测到{site_name}公告有更新")
        soup = BeautifulSoup(updated_content, "html.parser")
        announcements = soup.find_all("li")
        if announcements:
            announcement = announcements[0]
            title = announcement.find("a").text.strip()
            link = url + announcement.find("a")["href"]
            summary = announcement.find("p").text.strip()
            all_switches = get_all_group_switches()
            for group_id, switches in all_switches.items():
                if switches.get(f"{site_name}公告监控"):
                    logging.info(
                        f"检测到{site_name}公告有更新，向群 {group_id} 发送公告"
                    )
                    await send_group_msg(
                        websocket,
                        group_id,
                        f"{site_name}公告有新内容啦：\n标题：{title}\n摘要：{summary}\n链接：{link}\n\n机器人播报技术支持：https://github.com/W1ndys-bot/W1ndys-Bot",
                    )
    return last_content, last_check_time


async def monitor_jwc_announcements(websocket):
    global last_jwc_content, last_jwc_check_time
    last_jwc_content, last_jwc_check_time = await monitor_announcements(
        websocket, jwc_url, last_jwc_content, "QFNU教务处", last_jwc_check_time
    )


async def monitor_zcc_announcements(websocket):
    global last_zcc_content, last_zcc_check_time
    last_zcc_content, last_zcc_check_time = await monitor_announcements(
        websocket, zcc_url, last_zcc_content, "QFNU资产处", last_zcc_check_time
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

            if raw_message == "qfnujwc-off":
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

            if raw_message == "qfnuzcc-on":
                if load_function_status(group_id, "QFNU资产处"):
                    await send_group_msg(
                        websocket,
                        group_id,
                        "[CQ:reply,id="
                        + message_id
                        + "]QFNU资产处公告监控已经在运行，无需重复开启",
                    )
                    return
                else:
                    save_function_status(group_id, True, "QFNU资产处")
                    logging.info(f"已开启群 {group_id} 的QFNU资产处公告监控任务")
                    await send_group_msg(
                        websocket,
                        group_id,
                        "[CQ:reply,id=" + message_id + "]QFNU资产处公告监控已开启",
                    )
                    return

            if raw_message == "qfnuzcc-off":
                if load_function_status(group_id, "QFNU资产处"):
                    save_function_status(group_id, False, "QFNU资产处")
                    logging.info(f"已取消群 {group_id} 的QFNU资产处公告监控任务")
                    await send_group_msg(
                        websocket,
                        group_id,
                        "[CQ:reply,id=" + message_id + "]QFNU资产处公告监控已关闭",
                    )
                    return
                else:
                    await send_group_msg(
                        websocket,
                        group_id,
                        "[CQ:reply,id="
                        + message_id
                        + "]QFNU资产处公告监控未开启，无需重复关闭",
                    )
                    return

    except Exception as e:
        logging.error(f"处理QFNU_JWC_Tracker群消息失败: {e}")


# 程序开机自动执行的函数，每个心跳周期检查一次
async def start_qfnujwc_tracker(websocket):
    all_switches = get_all_group_switches()
    for group_id, switches in all_switches.items():
        if switches.get("QFNU教务处公告监控"):
            await monitor_jwc_announcements(websocket)
        if switches.get("QFNU资产处公告监控"):
            await monitor_zcc_announcements(websocket)
