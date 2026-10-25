#!/bin/bash
cd -- "$(dirname -- "$0")" || exit 1
if ! command -v python3 >/dev/null 2>&1; then
  echo '需要 Python 3。请安装后重新打开。安装地址：https://www.python.org/downloads/macos/'
  read -r -p '按回车退出。'
  exit 1
fi
python3 editor/server.py
read -r -p '编辑器已关闭。按回车退出。'
