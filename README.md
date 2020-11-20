# GramAddict
![Python](https://img.shields.io/badge/built%20with-Python3-red.svg)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat)

[español](https://github.com/GramAddict/bot/blob/master/res/README_es.md) | [português](https://github.com/GramAddict/bot/blob/master/res/README_pt_BR.md)

Liking and following automatically on your Android phone/tablet. No root required: it works on [uiautomator2](https://github.com/openatx/uiautomator2), which is a faster and more efficient fork of the official Android UI testing framework [UI Automator](https://developer.android.com/training/testing/ui-automator). This is a completely free and open source project that is forked from the freemium project [Insomniac](https://github.com/alexal1/Insomniac/). You can check them out, but you'll probably like us better. 😊

<img src="https://github.com/GramAddict/bot/raw/master/res/demo.gif">

## Requirements

- Python 3.6+

### How to install
1. Clone project: `git clone https://github.com/GramAddict/bot.git gramaddict`
2. Go to GramAddict folder: `cd gramaddict`
3. (Optionally) Use virtualenv or similar to make a virtual environment `virtualenv -p python3 .venv` and enter the virtual environment `source .venv/bin/activate`
4. Install required libraries: `pip3 install -r requirements.txt`
5. Download and unzip [Android platform tools](https://developer.android.com/studio/releases/platform-tools), move them to a directory where you won't delete them accidentally, e.g.
```
mkdir -p ~/Library/Android/sdk
mv <path-to-downloads>/platform-tools/ ~/Library/Android/sdk
```
6. [Add platform-tools path to the PATH environment variable](https://github.com/GramAddict/bot/wiki/Adding-platform-tools-to-the-PATH-environment-variable). If you do it correctly, terminal / command prompt command `adb devices` will print `List of devices attached`
7. Run the script `python3 run.py --blogger-followers username`

### How to install on Raspberry Pi OS
1. Update apt-get: `sudo apt-get update`
2. Install ADB and Fastboot: `sudo apt-get install -y android-tools-adb android-tools-fastboot`
3. Clone project: `git clone https://github.com/GramAddict/bot.git gramaddict`
4. Go to GramAddict folder: `cd gramaddict`
5. (Optionally) Use virtualenv or similar to make a virtual environment `virtualenv -p python3 .venv` and enter the virtual environment `source .venv/bin/activate`
6. Install required libraries: `pip3 install -r requirements.txt`
7. Run the script `python3 run.py --blogger-followers username`


### Get started
1. Connect Android device to your computer with a USB cable
2. Enable [Developer options](https://developer.android.com/studio/debug/dev-options#enable) on the device
>On Android 4.1 and lower, the Developer options screen is available by default. On Android 4.2 and higher, you must enable this screen. To enable developer options, tap the Build Number option 7 times. You can find this option in one of the following locations, depending on your Android version:
>
> Android 9 (API level 28) and higher: Settings > About Phone > Build Number
>
> Android 8.0.0 (API level 26) and Android 8.1.0 (API level 26): Settings > System > About Phone > Build Number
>
> Android 7.1 (API level 25) and lower: Settings > About Phone > Build Number
3. Switch on **USB debugging** (and **Install apps via USB** if there is such option) on the Developer options screen.
4. Device will ask you to allow computer connection. Press "Connect"
5. Type `adb devices` in terminal. It will display attached devices. There should be exactly one device. Then run the script (it works on Python 3):
```
cd <path-to-project>/gramaddict
python run.py --blogger-followers <username1> <username2> ...
```
Make sure that the screen is turned on and device is unblocked. You don't have to open Instagram app, script opens it and closes when it's finished. Just make sure that Instagram app is installed. If everything's fine, script will open each blogger's followers and like their posts.

### Usage
Full list of command line arguments:
```
  --blogger-followers username1 [username2 ...]
                        list of usernames with whose followers you want to
                        interact
  --hashtag-likers hashtag1 [hashtag2 ...]
                        list of hashtags with whose post likers you want to
                        interact
  --likes-count 2-4     number of likes for each interacted user, 2 by
                        default. It can be a number (e.g. 2) or a range (e.g.
                        2-4)
  --stories-count 2-4   number of stories for each interacted user, 2 by
                        default. It can be a number (e.g. 2) or a range (e.g.
                        2-4)
  --total-likes-limit 300
                        limit on total amount of likes during the session, 300
                        by default
  --interactions-count 60-80
                        number of interactions per each blogger, 70 by
                        default. It can be a number (e.g. 70) or a range (e.g.
                        60-80). Only successful interactions count
  --repeat 120-180      repeat the same session again after N minutes after
                        completion, disabled by default. It can be a number of
                        minutes (e.g. 180) or a range (e.g. 120-180)
  --follow-percentage 50
                        follow given percentage of interacted users, 0 by
                        default
  --follow-limit 50     limit on amount of follows during interaction with
                        each one user's followers, disabled by default
  --unfollow 100-200    unfollow at most given number of users. Only users
                        followed by this script will be unfollowed. The order
                        is from oldest to newest followings. It can be a
                        number (e.g. 100) or a range (e.g. 100-200)
  --unfollow-non-followers 100-200
                        unfollow at most given number of users, that don't
                        follow you back. Only users followed by this script
                        will be unfollowed. The order is from oldest to newest
                        followings. It can be a number (e.g. 100) or a range
                        (e.g. 100-200)
  --unfollow-any 100-200
                        unfollow at most given number of users. The order is
                        from oldest to newest followings. It can be a number
                        (e.g. 100) or a range (e.g. 100-200)
  --min-following 100   minimum amount of followings, after reaching this
                        amount unfollow stops
  --device 2443de990e017ece
                        device identifier. Should be used only when multiple
                        devices are connected at once
  --screen-sleep        turns on the phone screen when the script is running and 
                        off when when it's ended or sleeping (e.g. when using with
                        --repeat) - disable the passcode for unlocking the phone
                        if you want to use that function!
```

### FAQ
- How to stop the script? _Ctrl+C (control+C for Mac)_
- Can I prevent my phone from falling asleep while the script is working? _Yes. Settings -> Developer Options -> Stay awake._
- With the new feature _--screen-sleep_ you can forget about keeping your screen always on: the script will turn it on and off for you.
  Attention: this function is intended to work only if you don't have a passcode for unlock your phone!
- [How to connect Android phone via WiFi?](https://github.com/GramAddict/bot/wiki/Connect-Android-phone(s)-via-WiFi)
- [How to run on 2 or more devices at once?](https://github.com/GramAddict/bot/wiki/Running-script-on-multiple-devices-at-once)
- [Script crashes with **OSError: RPC server not started!** or **ReadTimeoutError**](https://github.com/GramAddict/bot/wiki/Problems-with-adb-connection:-what-to-do)

### Features in progress
- [x] Follow private accounts
- [x] Filter by followers/followings count, ratio, business/non-business
- [x] Screen-sleep for turning on and off your phone screen
- [x] Interaction by hashtags
- [x] Randomize the single click for a better human-like behaviour
- [ ] Add random actions to behave more like a human (watch your own feed, stories, etc.)
- [ ] Commenting during interaction

### Why GramAddict?
There already is [InstaPy](https://github.com/timgrossmann/InstaPy), which works on Instagram web version. Unfortunately, Instagram bots detection system has become very suspicious to browser actions. Now InstaPy and similar scripts work at most an hour, then Instagram blocks possibility to do any actions, and if you continue using InstaPy, it may ban your account. There is also [Insomniac](https://github.com/alexal1/Insomniac/) which is the origin of this project, but there were issues that cropped up when the project organizers decided to monetize it. We wanted to keep this project completely free and open source so we forked it!

Our objective is to make a free solution for mobile devices. Instagram can't distinguish bot from a human when it comes to your phone. However, even a human can reach limits when using the app, so don't fail to be careful. Always set `--total-likes-limit` to 300 or less. Also it's better to use `--repeat` to act periodically for 2-3 hours, because Instagram keeps track of how long the app works.

### Community
We have a [Discord server](https://discord.gg/9MTjgs8g5R) which is the most convenient place to discuss all bugs, new features, Instagram limits, etc. 

<p>
  <a href="https://discord.gg/9MTjgs8g5R">
    <img hspace="3" alt="Discord Server" src="https://github.com/GramAddict/bot/raw/master/res/discord.png" height=84/>
  </a>
</p>
