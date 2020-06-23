<img align="left" width="80" height="80" src="https://raw.githubusercontent.com/alexal1/Insomniac/master/res/icon.jpg" alt="Insomniac">

# Insomniac
![GitHub tag (latest by date)](https://img.shields.io/github/v/tag/alexal1/Insomniac?label=latest%20version)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat)

Liking and following automatically on your Android phone/tablet. No root required: it works on [UI Automator](https://developer.android.com/training/testing/ui-automator), which is an official Android UI testing framework.

### How to install
1. Clone project: `git clone https://github.com/alexal1/Insomniac.git`
2. Install [uiautomator](https://github.com/xiaocong/uiautomator) and [colorama](https://pypi.org/project/colorama/): `pip3 install uiautomator colorama`
3. Download and unzip [Android platform tools](https://developer.android.com/studio/releases/platform-tools), move them to a directory where you won't delete them accidentally, e.g.
```
mkdir -p ~/Library/Android/sdk
mv <path-to-downloads>/platform-tools/ ~/Library/Android/sdk
```
4. Add platform-tools path to environment variables. E.g. on Linux/macOS you have to add the following line to .bash_profile:<br>`export PATH=~/Library/Android/sdk/platform-tools/:$PATH`<br>If you do it correctly, terminal command `adb devices` will print `List of devices attached`

### How to install on Raspberry Pi OS
1. Update apt-get: `sudo apt-get update`
2. Install ADB and Fastboot: `sudo apt-get install -y android-tools-adb android-tools-fastboot`
3. Clone project: `git clone https://github.com/alexal1/Insomniac.git`
4. Install [uiautomator](https://github.com/xiaocong/uiautomator) and [colorama](https://pypi.org/project/colorama/): `pip3 install uiautomator colorama`

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
3. Switch on **USB debugging** (or **Install apps via USB** or similar) in developer settings
4. Device will ask you to allow computer connection. Press "Connect"
5. Type `adb devices` in terminal. It will display attached devices. There should be exactly one device. Then run the script (it works on Python 3):
```
cd <path-to-project>/Insomniac
python3 insomniac.py --interact <username1> <username2> ...
```
Make sure that the screen is turned on and device is unblocked. You don't have to open Instagram app, script opens it and closes when it's finished. Just make sure that Instagram app is installed. If everything's fine, script will open each blogger's followers and like their posts.

### Usage
Full list of command line arguments:
```
  --interact username1 [username2 ...]
                        list of usernames with whose followers you want to
                        interact
  --likes-count 2       number of likes for each interacted user, 2 by default
  --total-likes-limit 1000
                        limit on total amount of likes during the session,
                        1000 by default
  --interactions-count 100
                        number of interactions per each blogger, 100 by
                        default
  --repeat 180          repeat the same session again after N minutes after
                        completion, disabled by default
  --follow-percentage 50
                        follow given percentage of interacted users, 0 by
                        default
  --unfollow 100        unfollow at most given number of users. Only users
                        followed by this script will be unfollowed. The order
                        is from oldest to newest followings
```

### Features in progress
- [x] Follow given percentage of interacted users by `--follow-percentage 50`
- [x] Unfollow given number of users (only those who were followed by the script) by `--unfollow 100`
- [ ] Unfollow given number of non-followers (only those who were followed by the script) by `--unfollow-non-followers 100`
- [ ] Add random actions to behave more like a human (watch your own feed, stories, etc.)
- [ ] Support intervals for likes and interactions count like `--likes-count 2-3`
- [ ] Interaction by hashtags
- [ ] Commenting during interaction

### Why Insomniac?
There already is [InstaPy](https://github.com/timgrossmann/InstaPy), which works on Instagram web version. Unfortunately, Instagram bots detection system has become very suspicious to browser actions. Now InstaPy and similar scripts work at most an hour, then Instagram blocks possibility to do any actions, and if you continue using InstaPy, it may ban your account.

That's why need arised in a solution for mobile devices. Instagram can't distinguish bot from a human when it comes to your phone. However, even a human can reach limits when using the app, so don't fail to be careful. Always set `--total-likes-limit` to 300 or less. Also it's better to use `--repeat` to act periodically by 2-3 hours, because Instagram keeps track of how long the app works.

### Community
Join our Telegram group

<a href="https://t.me/insomniac_chat">
  <img hspace="3" alt="Telegram Group" src="https://raw.githubusercontent.com/alexal1/Insomniac/master/res/telegram.png" width=214/>
</a>
