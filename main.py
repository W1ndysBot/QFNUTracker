# script/QFNU_JWC_Tracker/main.py

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
from app.switch import load_switch, save_switch

# 数据存储路径，实际开发时，请将QFNU_JWC_Tracker替换为具体的数据存放路径
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "QFNU_JWC_Tracker",
)


# 检查是否是群主
def is_group_owner(role):
    return role == "owner"


# 检查是否是管理员
def is_group_admin(role):
    return role == "admin"


# 检查是否有权限（管理员、群主或root管理员）
def is_authorized(role, user_id):
    is_admin = is_group_admin(role)
    is_owner = is_group_owner(role)
    return (is_admin or is_owner) or (user_id in owner_id)


# 查看功能开关状态
def load_function_status(group_id):
    return load_switch(group_id, "教务处公告监控")


# 保存功能开关状态
def save_function_status(group_id, status):
    save_switch(group_id, "教务处公告监控", status)


# 目标网站地址
url = "http://47.104.173.131/%E9%80%9A%E7%9F%A5%EF%BC%88%E6%97%A7%EF%BC%89-%E6%9B%B2%E9%98%9C%E5%B8%88%E8%8C%83%E5%A4%A7%E5%AD%A6%E6%95%99%E5%8A%A1%E5%A4%84.html#/"

# 用于存储上一次页面内容的变量
last_content = None


def fetch_content():
    global last_content
    response = requests.get(url)
    response.encoding = "utf-8"  # 确保正确的编码
    soup = BeautifulSoup(response.text, "html.parser")

    # 更新以匹配网页中的公告列表结构
    found_content = soup.find("ul", {"class": "n_listxx1"})
    current_content = found_content.encode("utf-8") if found_content else None

    if last_content is None:
        last_content = current_content
        return None  # 第一次运行时不返回任何内容

    if current_content != last_content:
        last_content = current_content
        return current_content
    return None


# 群消息处理函数
async def handle_QFNU_JWC_Tracker_group_message(websocket, msg):
    try:
        user_id = msg.get("user_id")
        group_id = msg.get("group_id")
        raw_message = msg.get("raw_message")
        role = msg.get("sender", {}).get("role")

        is_authorized_qq = is_authorized(role, user_id)

        if raw_message == "qfnujwc-on" and is_authorized_qq:
            save_function_status(group_id, True)
            await send_group_msg(
                websocket,
                group_id,
                "教务处公告监控已开启",
            )
            return

        if raw_message == "qfnujwc-off" and is_authorized_qq:
            save_function_status(group_id, False)
            await send_group_msg(
                websocket,
                group_id,
                "教务处公告监控已关闭",
            )
            return

        if load_function_status(group_id):
            updated_content = fetch_content()
            if updated_content:
                soup = BeautifulSoup(updated_content, "html.parser")
                announcements = soup.find_all("li")
                if announcements:
                    announcement = announcements[0]  # 获取最新的一个公告
                    title = announcement.find("a").text.strip()
                    link = "https://jwc.qfnu.edu.cn/" + announcement.find("a")["href"]
                    summary = announcement.find("p").text.strip()
                    await send_group_msg(
                        websocket,
                        group_id,
                        f"曲阜师范大学教务处公告有新内容啦：\n标题：{title}\n摘要：{summary}\n链接：{link}\n\n机器人播报技术支持：https://github.com/W1ndys-bot/W1ndys-Bot",
                    )

    except Exception as e:
        logging.error(
            f"处理QFNU_JWC_Tracker群消息失败: {e}"
        )  # 注意：QFNU_JWC_Tracker 是具体功能，请根据实际情况修改
        return


async def QFNUJWCTracker_main(websocket, msg):
    # 确保数据目录存在
    os.makedirs(DATA_DIR, exist_ok=True)

    # 无限循环，每分钟执行一次
    while True:
        logging.info("执行监控url:{}".format(url))
        await handle_QFNU_JWC_Tracker_group_message(websocket, msg)
        logging.info("执行完成，暂停60秒")
        await asyncio.sleep(60)  # 暂停60秒
