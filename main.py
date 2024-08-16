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


async def handle_QFNUTracker_group_message(websocket, msg):
    await jwc_gg_j_handle_group_message(websocket, msg)
    await zcc_zbgg_handle_group_message(websocket, msg)
