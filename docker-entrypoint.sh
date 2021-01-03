#!/bin/bash

adb kill-server;
adb start-server;
adb wait-for-device;
echo "Check if you need to authorized this container on your phone"
sleep 15s;
adb devices;

python3 run.py --config config.yml;