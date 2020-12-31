#!/bin/bash

adb devices;
echo "Check if you need to authorized this container on your phone"
sleep 15s;
adb devices;

python3 run.py --config config.yml;