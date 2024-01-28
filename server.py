import requests
import uvicorn
import telebot
import anti_useragent
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis
import sqlite3
import random
import json
import os
import cfg
import time


class PayResult(BaseModel):
    trade_id: str
    order_id: str
    amount: float
    actual_amount: float
    token: str
    block_transaction_id: str
    signature: str
    status: int  # 1: waiting 2: success 3: outdated


APP = FastAPI()
REDIS_CLI = redis.Redis(
    host=cfg.REDIS_HOST, port=cfg.REDIS_PORT, password=cfg.REDIS_PASSWORD
)
BOT = telebot.TeleBot(cfg.TG_BOT_TOKEN, parse_mode="html")


def jbot_add_token(user_id):
    k = f"user-{user_id}"
    user = json.loads(REDIS_CLI.get(k))
    user["balance"] = user["balance"] + 8
    REDIS_CLI.set(name=k, value=json.dumps(user))
    BOT.send_message(chat_id=user_id, text="付款成功！商品已发放，请查收～")


def jbot_set_vip(user_id):
    REDIS_CLI.delete(f"user-{user_id}")
    conn = sqlite3.connect(f"{cfg.PATH_USER_ROOT}/.tg_jav_bot_plus/tg_jav_bot_plus.db")
    conn.cursor().execute("UPDATE t_user SET is_vip=? WHERE user_id=?", (1, user_id))
    conn.commit()
    BOT.send_message(chat_id=user_id, text="付款成功！商品已发放，请查收～")


def jbot_set_svip(user_id):
    REDIS_CLI.set(name=f"svip-{user_id}", value=1)
    BOT.send_message(chat_id=user_id, text="付款成功！商品已发放，请查收～")


def code_service(user_id):
    ts = time.time()
    BOT.send_message(chat_id=cfg.ADMIN_TG_ID, text=f"代码服务: {ts}")
    BOT.send_message(
        chat_id=user_id,
        text=f"{ts}-付款成功！将付款截图和当前消息发给管理员即可～",
        reply_markup=InlineKeyboardMarkup().row(
            InlineKeyboardButton("联系管理员", url=cfg.ADMIN_TG_ACCOUNT)
        ),
    )


@APP.post("/notify")
def notify(res: PayResult):
    order_id = res.order_id
    user_id_item_id = order_id[order_id.rfind("-") + 1 :]
    s = user_id_item_id.find("#")
    user_id = user_id_item_id[:s]
    item_id = int(user_id_item_id[s + 1 :])
    item = cfg.ITEMS[item_id]
    if res.status == 2:
        globals()[item["action"]](user_id)
        return Response("success", status_code=200)
    elif res.status == 3:
        BOT.send_message(user_id, "订单已过期")
        return Response("outdated", status_code=200)


@APP.get("/redirect")
def redirect():
    return Response("success", status_code=200)


if __name__ == "__main__":
    uvicorn.run("server:APP", host="0.0.0.0", port=8081, reload=True)
