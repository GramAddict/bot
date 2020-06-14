<img align="left" width="80" height="80" src="https://raw.githubusercontent.com/alexal1/Insomniac/master/res/icon.jpg" alt="Insomniac">

# Insomniac
![GitHub tag (latest by date)](https://img.shields.io/github/v/tag/alexal1/Insomniac?label=latest%20version)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat)

Liking followers of specific users automatically on your Android phone/tablet. No root required: it works on [UI Automator](https://developer.android.com/training/testing/ui-automator), which is an official Android UI testing framework.

### How to install
1. Clone project: `git clone https://github.com/alexal1/Insomniac.git`
2. Install [uiautomator](https://github.com/xiaocong/uiautomator): `pip3 install uiautomator`
3. Download and unzip [Android platform tools](https://developer.android.com/studio/releases/platform-tools), move them to a directory where you won't delete them accidentally, e.g.
```
mkdir -p ~/Library/Android/sdk
mv <path-to-downloads>/platform-tools/ ~/Library/Android/sdk
```
4. Add platform-tools path to environment variables. E.g. on Mac you have to add the following line to .bash_profile:<br>`export PATH=~/Library/Android/sdk/platform-tools/:$PATH`<br>If you do it correctly, terminal command `adb devices` will print `List of devices attached`

### Get started
Connect Android device to your computer with a USB cabel. Enable developer's mode on the device, then enable USB debugging in developer settings. Device will ask you to allow computer connection, press "Connect" or similar. We're almost done: type `adb devices` in terminal. It will display attached devices. There should be exactly one device. Then run the script (it works on Python 3):
```
cd <path-to-project>/Insomniac
python3 insomniac.py --bloggers <username1> <username2> ...
```
Make sure that the screen is turned on and device is unblocked. You don't have to open Instagram app, script opens it and closes when it's finished. Just make sure that Instagram app is installed. If everything's fine, script will open each blogger's followers and like their posts.

### Usage
Full list of command line arguments:
```
  --bloggers username1 [username2 ...]
                        list of usernames with whose followers you want to
                        interact
  --likes-count 2       count of likes for each interacted user, 2 by default
  --total-likes-limit 1000
                        limit on total amount of likes during the session,
                        1000 by default
  --interactions 100    number of interactions per each blogger, 100 by
                        default
  --repeat 180          repeat the same session again after N minutes after
                        completion, disabled by default
```

### Features in progress
- [ ] Follow given percentage of interacted users by `--follow-percentage 50`
- [ ] Unfollow given number of users (only those who were followed by the script) by `--unfollow 100`
- [ ] Unfollow given number of non-followers (only those who were followed by the script) by `--unfollow-non-followers 100`
- [ ] Add random actions to behave more like a human (watch your own feed, stories, etc.)
- [ ] Support intervals for likes and interactions count like `--likes-count 2-3`
- [ ] Interaction by hashtags
- [ ] Commenting during interaction

### Why Insomniac?
There already is [InstaPy](https://github.com/timgrossmann/InstaPy), which works on Instagram web version. Unfortunately, Instagram bots detection system has become very suspicious to browser actions. Now InstaPy and similar scripts work at most an hour, then Instagram blocks possibility to do any actions, and if you continue using InstaPy, it may ban your account.

That's why need arised in a solution for mobile devices. Instagram can't distinguish bot from a human when it comes to your phone. However, even a human can reach limits when using the app, so don't fail to be careful. Always set `--total-likes-limit` to 1000 or less. Also it's better to use `--repeat` to act periodically by 2-3 hours, because Instagram keeps track of how long the app works.

### Community
 Join our Telegram group

<a href="https://t.me/insomniac_chat">
  <img hspace="3" alt="Telegram Group" src="https://raw.githubusercontent.com/alexal1/Insomniac/master/res/telegram.png" width=214/>
</a>
