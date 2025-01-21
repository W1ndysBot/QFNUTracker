import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import sys
from urllib.parse import urljoin

# 添加项目根目录到sys.path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from app.switch import get_all_group_switches
from app.api import send_group_msg


def get_first_announcement(url):
    try:
        response = requests.get(url, timeout=3)
        response.encoding = "utf-8"
        soup = BeautifulSoup(response.text, "html.parser")
        found_content = soup.find("ul", {"class": "n_listxx1"})

        if found_content and hasattr(found_content, "find_all"):
            announcements = found_content.find_all("li")
        else:
            announcements = None

        if not announcements:
            return None, None, None

        first_announcement = announcements[0]
        title = first_announcement.find("a").text.strip()
        link = urljoin(url, first_announcement.find("a")["href"])
        summary = (
            first_announcement.find("p").text.strip()
            if first_announcement.find("p")
            else ""
        )
        return title, link, summary
    except requests.RequestException as e:
        logging.error(f"获取{url}网页内容失败: {e}")
        return None, None, None


def fetch_content(url, last_title):
    # 使用新函数获取第一个公告
    current_title, link, summary = get_first_announcement(url)
    # logging.info(current_title)
    if last_title is None:
        return current_title, None, link, summary

    if current_title != last_title:
        return current_title, current_title, link, summary
    return last_title, None, None, None


async def monitor_announcements(websocket, url, last_title, site_name, last_check_time):
    current_time = datetime.now()

    # 检查当前时间的分钟数是否是5的倍数，表示每10分钟检查一次
    if current_time.minute % 1 != 0:
        return last_title, last_check_time

    # 检查是否在同一分钟内已经检查过
    if last_check_time and last_check_time.minute == current_time.minute:
        return last_title, last_check_time

    # 添加超时退出的逻辑，这里假设如果超过30分钟没有成功，则退出
    if last_check_time and (current_time - last_check_time).total_seconds() > 1800:
        logging.error(f"{site_name}监控超时，自动退出")
        return last_title, last_check_time  # 可以考虑抛出异常或其他退出方式

    last_title, updated_title, link, summary = fetch_content(url, last_title)
    last_check_time = current_time  # 更新检查时间
    if updated_title:
        logging.info(f"执行{site_name}监控")
        logging.info(f"检测到{site_name}公告有更新")
        title = updated_title
        short_summary = (
            summary[:40] if summary else "获取失败"
        )  # 检查 summary 是否为 None，如果为 None，则返回 "获取失败"
        # logging.info(title)
        # logging.info(link)
        all_switches = get_all_group_switches()
        for group_id, switches in all_switches.items():
            if switches.get(f"{site_name}监控"):
                logging.info(f"检测到{site_name}公告有更新，向群 {group_id} 发送公告")
                await send_group_msg(
                    websocket,
                    group_id,
                    f"{site_name}公告有新内容啦：\n\n标题：{title}\n\n摘要：{short_summary}...\n\n链接：{link}\n\n技术支持：www.w1ndys.top",
                )
    return last_title, last_check_time
