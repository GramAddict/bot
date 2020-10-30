# GramAddict
![Python](https://img.shields.io/badge/built%20with-Python3-red.svg)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat)

[español](https://github.com/alexal1/Insomniac/blob/master/res/README_es.md) | [português](https://github.com/alexal1/Insomniac/blob/master/res/README_pt_BR.md)

Liking and following automatically on your Android phone/tablet. No root required: it works on [UI Automator](https://developer.android.com/training/testing/ui-automator), which is an official Android UI testing framework.

<img src="https://raw.githubusercontent.com/alexal1/Insomniac/master/res/demo.gif">

### How to install
1. Clone project: `git clone https://github.com/alexal1/Insomniac.git`
2. Go to Insomniac folder: `cd Insomniac`
3. Install required libraries: `pip3 install -r requirements.txt`
4. Download and unzip [Android platform tools](https://developer.android.com/studio/releases/platform-tools), move them to a directory where you won't delete them accidentally, e.g.
```
mkdir -p ~/Library/Android/sdk
mv <path-to-downloads>/platform-tools/ ~/Library/Android/sdk
```
5. [Add platform-tools path to the PATH environment variable](https://github.com/alexal1/Insomniac/wiki/Adding-platform-tools-to-the-PATH-environment-variable). If you do it correctly, terminal / command prompt command `adb devices` will print `List of devices attached`

### How to install on Raspberry Pi OS
1. Update apt-get: `sudo apt-get update`
2. Install ADB and Fastboot: `sudo apt-get install -y android-tools-adb android-tools-fastboot`
3. Clone project: `git clone https://github.com/alexal1/Insomniac.git`
4. Go to Insomniac folder: `cd Insomniac`
5. Install required libraries: `pip3 install -r requirements.txt`

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
  --likes-count 2-4     number of likes for each interacted user, 2 by
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
  --old                 add this flag to use an old version of uiautomator.
                        Use it only if you experience problems with the
                        default version
```

### FAQ
- How to stop the script? _Ctrl+C (control+C for Mac)_
- Can I prevent my phone from falling asleep while the script is working? _Yes. Settings -> Developer Options -> Stay awake._
- [How to connect Android phone via WiFi?](https://www.patreon.com/posts/connect-android-38655552)
- [How to run on 2 or more devices at once?](https://www.patreon.com/posts/38683736)
- [Script crashes with **OSError: RPC server not started!** or **ReadTimeoutError**](https://www.patreon.com/posts/problems-with-to-38702683)
- [Private accounts are always skipped. How to follow them too?](https://www.patreon.com/posts/enable-private-39097751) **(please join Patreon $10 tier)**
- [Filter by followers/followings count, ratio, business/non-business](https://www.patreon.com/posts/38826184) **(please join Patreon $10 tier)**
- [Can I automate removing mass followers from my account? Yes.](https://www.patreon.com/posts/40514622) **(please join Patreon $10 tier)**

### Analytics
There also is an analytics tool for this bot. It is a script that builds a report in PDF format. The report contains account's followers growth graphs for different periods. Liking, following and unfollowing actions' amounts are on the same axis to determine bot effectiveness. The report also contains stats of sessions length for different configurations that you've used. All data is taken from `sessions.json` file that's generated during bot's execution.
<img src="https://raw.githubusercontent.com/alexal1/Insomniac/master/res/analytics_sample.png">

### Features in progress
- [x] Follow given percentage of interacted users by `--follow-percentage 50`
- [x] Unfollow given number of users (only those who were followed by the script) by `--unfollow 100`
- [x] Unfollow given number of non-followers (only those who were followed by the script) by `--unfollow-non-followers 100`
- [x] Support intervals for likes and interactions count like `--likes-count 2-3`
- [ ] Add random actions to behave more like a human (watch your own feed, stories, etc.)
- [ ] Interaction by hashtags
- [ ] Commenting during interaction

### Why GramAddict?
There already is [InstaPy](https://github.com/timgrossmann/InstaPy), which works on Instagram web version. Unfortunately, Instagram bots detection system has become very suspicious to browser actions. Now InstaPy and similar scripts work at most an hour, then Instagram blocks possibility to do any actions, and if you continue using InstaPy, it may ban your account. There is also [Insomniac](https://github.com/alexal1/Insomniac/) which is the origin of this project, but they decided to charge a monthly fee for features that used to be free and we wanted to keep this project completely free and open source.

That's why need arised in a solution for mobile devices. Instagram can't distinguish bot from a human when it comes to your phone. However, even a human can reach limits when using the app, so don't fail to be careful. Always set `--total-likes-limit` to 300 or less. Also it's better to use `--repeat` to act periodically for 2-3 hours, because Instagram keeps track of how long the app works.

### Community
We have a [Discord server](https://discord.gg/9MTjgs8g5R) which is the most convenient place to discuss all bugs, new features, Instagram limits, etc. 

<p>
  <a href="https://discord.gg/9MTjgs8g5R">
    <img hspace="3" alt="Discord Server" src="https://raw.githubusercontent.com/alexal1/Insomniac/master/res/discord.png" height=84/>
  </a>
</p>
