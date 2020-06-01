<img align="left" width="80" height="80" src="https://raw.githubusercontent.com/alexal1/Insomniac/master/res/icon.jpg" alt="Insomniac">

# Insomniac
Liking followers of specific users automatically on your Android phone/tablet. No root required: it works on [UI Automator](https://developer.android.com/training/testing/ui-automator), which is an official Android UI testing framework.

### How to install
1. Clone project: `git clone https://github.com/alexal1/Insomniac.git`
2. Install [uiautomator](https://github.com/xiaocong/uiautomator): `pip install uiautomator`
3. Download and unzip [Android platform tools](https://developer.android.com/studio/releases/platform-tools), move them to a directory where you won't delete them accidentally, e.g.
```
mkdir -p ~/Library/Android/sdk
mv <path-to-downloads>/platform-tools/ ~/Library/Android/sdk
```
4. Add platform-tools to the PATH: `export PATH=$PATH:~/Library/Android/sdk/platform-tools/`

### Get started
Connect Android device to your computer and run `adb devices`. It will display attached devices. There should be exactly one device. Then run the script (it works on Python 2.7):
```
cd <path-to-project>/Insomniac
python insomniac.py --bloggers <username1> <username2> ...
```
Make sure that Instagram is already opened on the attached device: the script can't itself open Instagram. If everything's fine, script will open each blogger's followers and like their posts.

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
```

### Why Insomniac?
There already is [InstaPy](https://github.com/timgrossmann/InstaPy), which works on Instagram web version. Unfortunately, Instagram team improved their bots detection system. Now Instapy and similar scripts work at most an hour, then Instagram blocks possibility to do any actions, and if you continue using Instapy, it may ban your account.

That's why need arised in better solution, which completely acts like a human. Insomniac can't be distinguished from human, because it does exactly same things. Homever, don't fail to be careful and always set `--total-likes-limit` to 1000 or less.
