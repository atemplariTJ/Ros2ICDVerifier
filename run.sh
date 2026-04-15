#!/bin/bash

# ROS2 환경과 사용자 커스텀 메시지가 빌드된 환경을 불러옵니다.
source /opt/homebrew/Caskroom/miniforge/base/envs/common_ros_env/bin/activate
source icd_ws/install/setup.zsh

# 파이썬 앱 실행
python main.py
