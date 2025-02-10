# Version 2, add price refresh date and integrated to rsrvTxt2.

# Next version will leverage PostgreSQL to manage json files and extra data.
# Also create log packaging script, periodically packaging the past logs.

cronjob

*/30 * * * * cd /Users/liangzhisong/Dropbox/script/Bara\ Integration && /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 "/Users/liangzhisong/Dropbox/script/Bara Integration/bara_integrationV2.py" >> "/Users/liangzhisong/Dropbox/script/Bara Integration/logs/bara_integrationV2_$(date +\%Y-\%m-\%d).log" 2>&1

0 23 * * * cd /Users/liangzhisong/Dropbox/script/Bara\ Integration && /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 "/Users/liangzhisong/Dropbox/script/Bara Integration/daily_check.py" >> "/Users/liangzhisong/Dropbox/script/Bara Integration/logs/daily_check.log" 2>&1