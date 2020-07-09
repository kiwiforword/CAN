""" **************** zcanpro模块说明 ****************

# ZCANPRO程序中提供了zcanpro模块，使用"import zcanpro"导入至自定义的脚本中即可使用。

# 提供的接口如下：
1. buses = zcanpro.get_buses()
    获取ZCANPRO程序已经启动的总线信息(即打开的设备CAN通道)。
    * buses: 为总线信息列表，如
    [
        {
            "busID": 101,       # 总线ID
            "devType": 1,       # 设备类型
            "devIndex": 0,      # 设备索引号
            "chnIndex": 0       # 通道索引号
        },
        ...
    ]

2. result, frms = zcanpro.receive(busID)
    获取指定总线的数据。
    * busID: 指定总线ID, 整数类型
    * result: 返回执行结果，整数类型，0-失败, 1-成功
    * frms: 返回获取的数据列表， 如
    [
        {
            "can_id": 101,              # 帧ID
            "is_canfd": 1,              # 是否为CANFD数据, 0-CAN, 1-CANFD
            "canfd_brs": 1,             # CANFD加速, 0-不加速, 1-加速
            "data": [0, 1, 2, 3, 4],    # 数据
            "timestamp_us": 666666      # 时间戳, 微妙
        },
        ...
    ]

3. result = zcanpro.transmit(busID, frms)
    发送数据至指定总线。
    * busID: 指定总线ID, 整数类型
    * frms: 指定数据列表，同zcanpro.receive
    * result: 返回执行结果, 整数类型，0-失败, 1-成功

4. zcanpro.write_log(msg)
    显示日志信息，ZCANPRO程序会在界面上显示该信息，便于跟踪脚本运行过程。
    * msg 日志信息，字符串类型

5. zcanpro.uds_init(udsCfg)
    初始化UDS诊断服务。
    * udsCfg: UDS服务配置参数, 字典类型, 如
    {
        "response_timeout_ms": 3000,    # 响应超时时间(ms)
        "use_canfd": 0,                 # 是否使用CANFD, 0-CAN, 1-CANFD
        "trans_ver": 0                  # 传输协议版本, 0-ISO15765_2 2004格式, 1-ISO15765_2 2016新增格式
    }

6. response = zcanpro.uds_request(busID, req)
    请求UDS服务，返回响应数据。
    * busID: 指定总线ID, 整数类型
    * req: 请求数据，字典类型，如
    {
        "src_addr": 0x700,              # 源地址
        "dst_addr": 0x701,              # 目标地址
        "suppress_response" :0,         # 是否抑制响应, 0-不抑制, 1-抑制
        "sid": 0x19,                    # UDS服务号
        "data":[0x02, 0xFF]             # UDS服务数据
    }
    * response: 返回的响应结果，字典类型，如
    {
        "result": 1,                    # 响应状态, 0-失败, 1-成功
        "result_msg": "ok",             # 响应结果字符串，如果响应失败，指示失败原因
        "data":[0x59, 0x02, 0x1D, 0xAE] # 响应数据，响应成功时为积极响应或者消极响应数据
    }

7. zcanpro.uds_deinit()
    关闭UDS服务，释放资源。

"""

""" **************** 扩展脚本文件编写说明 ****************

# 扩展脚本文件（即提供给ZCANPRO程序执行的脚本）必须提供以下接口供ZCANPRO程序调用。

1. z_main()
    入口函数，ZCANPRO程序运行扩展脚本时会首先调用该函数，该函数退出时即为扩展脚本运行结束。
    编写时，请注意不要让该函数执行死循环，确保其能正常运行结束，或者接收到ZCANPRO程序发送的停止运行命令后能正常退出。

2. z_notify(type, obj)
    事件通知函数，ZCANPRO程序会在产生相应事件的时候调用该接口通知运行的脚本。
    * type: 事件类型，字符串类型，目前支持的类型如下
        a) "stop": 停止脚本运行，接收到该命令后应让z_main函数立即运行结束。

"""


# 以下示例程序，展示总线0的数据转发至总线1

import time
import zcanpro

stopTask = False

def z_notify(type, obj):
    zcanpro.write_log("Notify " + str(type) + " " + str(obj))
    if type == "stop":
        zcanpro.write_log("Stop...")
        global stopTask
        stopTask = True

def z_main():
    buses = zcanpro.get_buses()
    zcanpro.write_log("Get buses: " + str(buses))

    if len(buses) >= 2:
        global stopTask
        stopTask = False
        while not stopTask:
            result, frms = zcanpro.receive(buses[0]["busID"])
            if not result:
                zcanpro.write_log("Receive error!")
            elif len(frms) > 0:
                zcanpro.write_log("Received " + str(len(frms)))
                result = zcanpro.transmit(buses[1]["busID"], frms)
                if not result:
                    zcanpro.write_log("Transmit error!")
            time.sleep(0.01)


# 以下示例，展示扩展脚本请求UDS诊断服务

def test_uds(busID):
    udsCfg = {
        "response_timeout_ms": 3000,
        "use_canfd": 0,
        "trans_ver": 0
    }
    zcanpro.uds_init(udsCfg)

    req = {
        "src_addr": 0x700,
        "dst_addr": 0x701,
        "suppress_response" :0,
        "sid": 0x19,
        "data":[0x02, 0xFF]
    }

    global stopTask
    stopTask = False
    while not stopTask:
        zcanpro.write_log("[UDS Tx] " + ("%02X " % req["sid"]) + " ".join('{:02X}'.format(a) for a in req["data"]))
        response = zcanpro.uds_request(busID, req)
        if not response["result"]:
            zcanpro.write_log("Request error! " + response["result_msg"])
        else:
            zcanpro.write_log("[UDS Rx] " + " ".join('{:02X}'.format(a) for a in response["data"]))
        time.sleep(1)

    zcanpro.uds_deinit()

"""
def z_main():
    buses = zcanpro.get_buses()
    zcanpro.write_log("Get buses: " + str(buses))
    if len(buses) >= 1:
        test_uds(buses[0]["busID"])
"""










