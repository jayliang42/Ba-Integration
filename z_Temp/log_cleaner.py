import os
import time
import configparser

def clean_logs():
    config = configparser.ConfigParser()
    config.read('config/config.ini')

    log_file = config['log']['log_file']
    retention_days = int(config['log']['retention_days'])

    if os.path.exists(log_file):
        file_age = time.time() - os.path.getmtime(log_file)
        if file_age > retention_days * 86400:  # 转换为秒
            os.remove(log_file)
