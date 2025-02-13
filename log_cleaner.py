import os
import tarfile
from datetime import datetime

# get script dir
script_dir = os.path.dirname(os.path.abspath(__file__))
log_dir = os.path.join(script_dir, "logs", "integration")
backup_dir = os.path.join(script_dir, "logs")

# Get current year and date
date_str = datetime.now().strftime("%Y-%m")
backup_file = os.path.join(backup_dir, f"integration_{date_str}.tar.gz")

# compress
with tarfile.open(backup_file, "w:gz") as tar:
    tar.add(log_dir, arcname="integration")

print(f"Backup created: {backup_file}")
