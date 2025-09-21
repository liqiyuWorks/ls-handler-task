

def look_recent_time(now_datetime):
    '''获取最近的 半小时数据'''
    minutes = now_datetime.minute  # 获取当前分钟数
    if minutes < 30:
        target_minute = 0
    else:
        target_minute = 30
        # now += datetime.timedelta(hours=1)  # 如果当前时间已经过了30分钟，则需要寻找下一个半小时

    target_time = now_datetime.replace(minute=target_minute,
                                       second=0, microsecond=0)  # 构造目标时间
    target_time_str = target_time.strftime("%Y%m%d%H%M")

    print(f"距离最近的半小时是 {target_time_str}")
    return target_time_str


