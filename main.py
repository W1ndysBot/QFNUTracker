import os
import sys
import re
import asyncio  # 引入asyncio库
import time  # 引入time库

# 添加项目根目录到sys.path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from app.switch import get_all_group_switches
from app.api import send_group_msg
from app.scripts.QFNUTracker.jwc_gg_j import (
    start_monitoring as jwc_gg_j_start_monitoring,
    handle_QFNUTracker_group_message as jwc_gg_j_handle_group_message,
)
from app.scripts.QFNUTracker.jwc_tz_j import (
    start_monitoring as jwc_tz_j_start_monitoring,
)

from app.scripts.QFNUTracker.zcc_zbgg import (
    start_monitoring as zcc_zbgg_start_monitoring,
    handle_QFNUTracker_group_message as zcc_zbgg_handle_group_message,
)

from app.scripts.QFNUTracker.zcc_zbgg1 import (
    start_monitoring as zcc_zbgg1_start_monitoring,
)


async def start_qfnu_tracker(websocket):

    await jwc_gg_j_start_monitoring(websocket)
    await jwc_tz_j_start_monitoring(websocket)
    await zcc_zbgg_start_monitoring(websocket)
    await zcc_zbgg1_start_monitoring(websocket)


# QFNU定制服务
async def QFNU(websocket, group_id, message_id):
    message = (
        f"[CQ:reply,id={message_id}]\n"
        + """
QFNU定制服务

曲阜师范大学公告监控
qfnujwc-on 开启教务处监控
qfnujwc-off 关闭教务处监控
qfnuzcc-on 开启资产处监控
qfnuzcc-off 关闭资产处监控
更多内容更新中...（鸽）

技术支持：W1ndys
"""
    )
    await send_group_msg(websocket, group_id, message)


async def handle_QFNUTracker_group_message(websocket, msg):
    await jwc_gg_j_handle_group_message(websocket, msg)
    await zcc_zbgg_handle_group_message(websocket, msg)
    raw_message = msg.get("raw_message")
    group_id = msg.get("group_id")
    message_id = msg.get("message_id")
    if raw_message == "qfnu":
        await QFNU(websocket, group_id, message_id)
