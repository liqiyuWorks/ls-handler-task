# python generator.py -q nc2redis:gfs --file_path /Users/jiufangkeji/Documents/JiufangCodes/nc2redis/data/2022052200
# python3 generator.py -q nc2redis:gfs --file_path /hpcdata/data_service/forecast/GFS/2022060618
import argparse
import os.path
import redis
import json
import subprocess

def get_files(file_path, filter_re):
    cmd = '/usr/bin/find {} -type f -name "{}"'.format(file_path, filter_re)
    print('cmd {}'.format(cmd))
    res = subprocess.getstatusoutput(cmd)
    if res[0] != 0 or len(res[1]) == 0:
        print('execute {} result {}'.format(cmd, res))
        return []
    files = res[1].split('\n')
    return files


def get_preday_files(file_path, filter_re):
    files = get_files(file_path, filter_re)
    pre_files = []
    for file in files:
        file_name = os.path.basename(file)
        splits = file_name.rstrip(".nc").split('_')
        pre_day = splits[-2]
        cur_day = splits[-1].strip('R')
        if pre_day < cur_day:
            pre_files.append(file)
    return pre_files

class GenGfsDaily:
    def run(self):
        queue = os.getenv('QUEUE', "nc2redis:gfs")
        redis_host = os.getenv('REDIS_HOST', "124.70.86.179")
        redis_port = os.getenv('REDIS_PORT', "21600")
        redis_password = os.getenv('REDIS_PASSWORD', "")
        cur_year = os.getenv('CUR_YEAR', "no")
        file_path = os.getenv('FILE_PATH', None)
        file_re = os.getenv('FILE_RE', "*")
        rds = redis.Redis(host=redis_host, port=redis_port, db=0, password=redis_password,
                        decode_responses=True)
        if cur_year == "yes":
            files = get_preday_files(file_path, file_re)
        else:
            files = get_files(file_path, file_re)
        sorted_files = sorted(files)
        for file in sorted_files:
            task = {
                'task_type': queue,
                'input_file': file
            }
            queue_len = rds.rpush(queue, json.dumps(task))
            print("queue {} length {}, new task {}".format(queue, queue_len, task))

        rds.close()