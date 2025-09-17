#!/usr/bin/python3
import os

os.execve('/usr/bin/git', ['git', 'log'], {})
