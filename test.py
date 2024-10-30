# read files from current_files directory

import os
import sys


def read_files():
    current_files = os.listdir('current_files/02')
    return current_files


print(read_files())
