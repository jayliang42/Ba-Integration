 # 每小时执行一次
 0 * * * * cd "/Users/liangzhisong/Dropbox/script/Bara Integration" && /Library/ Frameworks/Python.framework/Versions/3.10/bin/python3 "bara_integrationV2.py"   >> "/Users/liangzhisong/Dropbox/script/Bara Integration/logs/                   bara_integrationV2/bara_integrationV2_$(date '+\%Y-\%m-\%d').log" 2>&1

 # 每天晚上 11 点执行一次
 0 23 * * * cd "/Users/liangzhisong/Dropbox/script/Bara Integration" && /        Library/Frameworks/Python.framework/Versions/3.10/bin/python3 "daily_check.py"  >> "/Users/liangzhisong/Dropbox/script/Bara Integration/logs/daily_check/       daily_check.log" 2>&1

 # 每月的第一天执行一次，压缩上个月的日志
 #1 0 1 * * cd "/Users/liangzhisong/Dropbox/script/Bara Integration/logs" &&     tar -czf "integration_$(date '+\%Y-\%m').tar.gz" -C "/Users/liangzhisong/       Dropbox/script/Bara Integration/logs/integration/bak" .