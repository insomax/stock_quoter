#!/usr/bin/python
# -*- coding: utf-8 -*-

import websocket
import threading
import ssl

from log import *
from message import *
import config


class WebsockClient():
    def __init__(self, conf):
        self.conf = conf
        self.init(conf.WEBSOCKET_PATH,
                  conf.SYMBOL,
                  conf.SUBSCRIBE,
                  conf.HEARTBEAT,
                  conf.PARSER,
                  conf.ENABLE_RECONNECT,
                  conf.ENABLE_TRACE,
                  conf.HEARTBEAT_INTERVAL)

    def init(self, url, symbol,
             subscribe='subscribe',
             heartbeat='heartbeat',
             parser='service_route',
             enable_reconnect = True,
             enable_trace = False,
             heartbeat_interval=1):
        self.url = url
        self.symbol = symbol
        self.MSG = Message()
        self.enable_reconnect = enable_reconnect
        self.enable_trace = enable_trace
        self.req_ws = None
        self.is_available = False
        self.is_stop = True
        self.wsapp = None
        self.heartbeat_timer_thread = None
        self.event = None
        self.heartbeat_interval = heartbeat_interval
        # 调用订阅函数
        self.subscribe = subscribe
        # 发送心跳函数
        self.heartbeat = heartbeat
        # 调用解析处理函数
        self.parser = parser

    # 接收消息
    def on_message(self, ws, message):
        # TODO 接收消息自定义处理
        if self.parser:
            hasattr(self, self.parser)
            func = getattr(self.MSG, self.parser)
            func(ws, message, self.conf)

    def on_pong(self, ws, message):
        DEBUG_LOG("Recieved Pong ...")

    def send_heartbeat(self, interval, event):
        while not self.is_stop:
            DEBUG_LOG("### send heartbeat ###")
            if self.heartbeat:
                hasattr(self, self.heartbeat)
                func = getattr(self.MSG, self.heartbeat)
                func(self.req_ws)
            event.wait(interval)

    # 连接断开
    def close(self):
        self.wsapp.close()
        if self.heartbeat_timer_thread and self.heartbeat_timer_thread.isAlive():
            self.event.set()
            self.heartbeat_timer_thread.join()

    # 发生错误
    def on_error(self, ws, error):
        # TODO 填写因发送异常，连接断开的处理操作
        ERROR_LOG("websocket error, rason:%s" % ws.on_error.__dict__)
        self.is_stop = True
        self.close()

    def reconnect(self, ws):
        # TODO 填写连接断开的处理操作
        DEBUG_LOG("### reconnecting ... ###")
        self.close()
        self.run()
        DEBUG_LOG("### reconnected again ###")

    # 连接断开
    def on_close(self, ws, manually=False):
        # TODO 填写连接断开的处理操作f
        if not manually:
            if self.is_stop:
                DEBUG_LOG("### already stop, do not reconnect ###")
                return
            DEBUG_LOG("### closed ###")
            if self.enable_reconnect:
              self.reconnect(ws)
            return

        DEBUG_LOG("### manually closed ###")
        self.is_stop = True
        self.close()
    
    def start_heartbeat_timer(self):
        self.event = threading.Event()
        self.heartbeat_timer_thread = threading.Thread(name='heartbeat_timer',
                                                        target=self.send_heartbeat,
                                                        args=(self.heartbeat_interval,
                                                              self.event))
        self.heartbeat_timer_thread.setDaemon(True)
        self.heartbeat_timer_thread.start()

    # 建立连接
    def on_open(self, ws):
        # 建连发送auth
        DEBUG_LOG("### opened ###")
        self.req_ws = ws
        self.is_available = True
        self.is_stop = False
        if self.heartbeat_interval:
            #enable_multithread for timer read and write
            self.wsapp.sock.lock = threading.Lock()
            self.wsapp.sock.readlock = threading.Lock()
            self.start_heartbeat_timer()
        if self.subscribe:
            hasattr(self, self.subscribe)
            func = getattr(self.MSG, self.subscribe)
            func(ws, self.symbol)

    def run(self):
        if self.enable_trace:
            websocket.enableTrace(True)
        self.wsapp = websocket.WebSocketApp(self.url,
                                            on_message=lambda ws, message: self.on_message(ws, message),
                                            on_pong=lambda ws, message: self.on_pong(ws, message),
                                            on_error=lambda ws, error: self.on_error(ws, error),
                                            on_close=lambda ws: self.on_close(ws),
                                            on_open=lambda ws: self.on_open(ws))
        self.wsapp.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

    def get_ws(self):
        return self.req_ws


if __name__ == '__main__':
    conf = config.Config()
    LOG_INIT()
    wsc = WebsockClient(conf)
    wsc.run();
