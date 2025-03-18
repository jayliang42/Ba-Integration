# Version 2, add price refresh date and integrated to rsrvTxt2.

# Next version will leverage PostgreSQL to manage json files and extra data.
# Also create log packaging script, periodically packaging the past logs.

cronjob

*/30 * * * * cd /Users/liangzhisong/Dropbox/script/Bara\ Integration && /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 "/Users/liangzhisong/Dropbox/script/Bara Integration/bara_integrationV2.py" >> "/Users/liangzhisong/Dropbox/script/Bara Integration/logs/bara_integrationV2_$(date +\%Y-\%m-\%d).log" 2>&1

0 23 * * * cd /Users/liangzhisong/Dropbox/script/Bara\ Integration && /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 "/Users/liangzhisong/Dropbox/script/Bara Integration/daily_check.py" >> "/Users/liangzhisong/Dropbox/script/Bara Integration/logs/daily_check.log" 2>&1
```
Bara Integration
├─ Config
│  └─ config.ini
├─ README.md
├─ allstar_login_credentials.py
├─ bara_api.py
├─ bara_integrationV2.py
├─ credentials.py
├─ current_files
│  ├─ 01
│  │  ├─ ITM12NEO52RSW250210133657.json
│  │  ├─ ITM12NEO52RSW250210203325.json
│  │  ├─ ITM12NEO52RSW250211020829.json
│  │  ├─ ITM12NEO52RSW250211133230.json
│  │  ├─ ITM12NEO52RSW250212021026.json
│  │  ├─ ITM12NEO52RSW250212133359.json
│  │  ├─ ITM12NEO52RSW250212203438.json
│  │  ├─ ITM12NEO52RSW250213021228.json
│  │  ├─ ITM12NEO52RSW250213133300.json
│  │  ├─ ITM12NEO52RSW250213203244.json
│  │  ├─ ITM12NEO52RSW250214133417.json
│  │  ├─ ITM12NEO52RSW250214203226.json
│  │  ├─ ITM12NEO52RSW250215013120.json
│  │  ├─ ITM12NEO52RSW250217020240.json
│  │  ├─ ITM12NEO52RSW250217133833.json
│  │  ├─ PRM12NEO52RSW250212022518.json
│  │  ├─ PRM12NEO52RSW250212204832.json
│  │  ├─ PRM12NEO52RSW250213204707.json
│  │  ├─ PRM12NEO52RSW250214021802.json
│  │  ├─ PRM12NEO52RSW250214134654.json
│  │  ├─ PRM12NEO52RSW250214204518.json
│  │  ├─ PRM12NEO52RSW250215134520.json
│  │  ├─ PRM12NEO52RSW250217134624.json
│  │  ├─ history
│  │  └─ pending_promo
│  │     └─ pending_promo.json
│  ├─ 02
│  │  ├─ ITM12NEO52DUG250210133659.json
│  │  ├─ ITM12NEO52DUG250210203327.json
│  │  ├─ ITM12NEO52DUG250211020831.json
│  │  ├─ ITM12NEO52DUG250211133232.json
│  │  ├─ ITM12NEO52DUG250212021026.json
│  │  ├─ ITM12NEO52DUG250212133359.json
│  │  ├─ ITM12NEO52DUG250212203438.json
│  │  ├─ ITM12NEO52DUG250213021225.json
│  │  ├─ ITM12NEO52DUG250213133300.json
│  │  ├─ ITM12NEO52DUG250213203244.json
│  │  ├─ ITM12NEO52DUG250214133418.json
│  │  ├─ ITM12NEO52DUG250214203227.json
│  │  ├─ ITM12NEO52DUG250215013121.json
│  │  ├─ ITM12NEO52DUG250217020240.json
│  │  ├─ ITM12NEO52DUG250217133834.json
│  │  ├─ PRM12NEO52DUG250212022520.json
│  │  ├─ PRM12NEO52DUG250212204830.json
│  │  ├─ PRM12NEO52DUG250213204708.json
│  │  ├─ PRM12NEO52DUG250214021801.json
│  │  ├─ PRM12NEO52DUG250214134654.json
│  │  ├─ PRM12NEO52DUG250214204518.json
│  │  ├─ PRM12NEO52DUG250215134520.json
│  │  ├─ PRM12NEO52DUG250217134624.json
│  │  ├─ history
│  │  │  └─ 20250208.zip
│  │  └─ pending_promo
│  │     └─ pending_promo.json
│  └─ 03
│     ├─ ITM12NEO52RSW250210133657.json
│     ├─ ITM12NEO52RSW250210203325.json
│     ├─ ITM12NEO52RSW250211020829.json
│     ├─ ITM12NEO52RSW250211133230.json
│     ├─ ITM12NEO52RSW250212021026.json
│     ├─ ITM12NEO52RSW250212133359.json
│     ├─ ITM12NEO52RSW250212203438.json
│     ├─ ITM12NEO52RSW250213021228.json
│     ├─ ITM12NEO52RSW250213133300.json
│     ├─ ITM12NEO52RSW250213203244.json
│     ├─ ITM12NEO52RSW250214133417.json
│     ├─ ITM12NEO52RSW250214203226.json
│     ├─ ITM12NEO52RSW250215013120.json
│     ├─ ITM12NEO52RSW250217020240.json
│     ├─ ITM12NEO52RSW250217133833.json
│     ├─ PRM12NEO52RSW250212022518.json
│     ├─ PRM12NEO52RSW250212204832.json
│     ├─ PRM12NEO52RSW250213204707.json
│     ├─ PRM12NEO52RSW250214021802.json
│     ├─ PRM12NEO52RSW250214134654.json
│     ├─ PRM12NEO52RSW250214204518.json
│     ├─ PRM12NEO52RSW250215134520.json
│     ├─ PRM12NEO52RSW250217134624.json
│     ├─ history
│     │  └─ 20250208.zip
│     └─ pending_promo
│        └─ pending_promo.json
├─ daily_check.py
├─ data_process_helper.py
├─ historical_files
│  ├─ 01.txt
│  ├─ 02.txt
│  └─ 03.txt
├─ keymap
│  ├─ ITM_keymap.json
│  ├─ PRM_keymap.json
│  └─ hs_datatype_keymap.json
├─ log_cleaner.py
├─ log_helper.py
├─ refresh_date.py
```