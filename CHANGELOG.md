# Changelog
## 3.2.5 (2023-07-23)
### Fix
- account selection with the little arrow instead of clicking on the account name
### Others
- display a warning if the user tries to use an untested version of IG
## 3.2.4 (2023-04-07)
### Fix
- fix selecting account if you have a lof of them, and it's not visible
- screen timeout checking for 'always on devices' (for example emulators)
### Others
- config loader in 'extra' folder
## 3.2.3 (2022-06-23)
### Others
- allow to pass device to dump
- allot to don't to kill the demon while dumping
## 3.2.2 (2022-04-28)
### Fix
- deprecated method uiautomator2 side that cause that error:
  >AttributeError: 'Session or Device' object has no attribute '_is_alive'
## 3.2.1 (2022-03-25)
### Fix
- default value for `unfollow-delay` was an integer instead of a string
- story_watcher returned Optional\[Union\[bool, int]] instead of int
## 3.2.0 (2022-03-23)
### New Features
- `unfollow` and `unfollow-non-followers` now check for when you last interacted with each user. Using the argument `unfollow-delay` you can specify the number of days that have to have passed since the last interaction
- after watching a story, the bot will now like it
- with `count-app-crashes` you can tell the bot to count app crashes as a crash for `total-crashes-limit` (default False)
- using the argument `remove-followers-from-file`, the bot can now remove followers following you from a *.txt
### Fix
- when interacting with the last picture of a profile, the bot could crash
- following suggested people instead of target account
- missing block detection for full screen mode (video)
- profile is loaded false negative
- avoid re-watching content if like fails
### Performance improvements
- new way to search for targets in search menu
- no need to see limits for PM if you're not sending them
- code has been cleaned and some functions have been merged
- inspect current view for list of users, this will avoid pressing on bottom bar
- set the screen timeout to 5 minutes if it's less than this value to avoid screen off issues
- store the target source in json instead of a duplicate of the username
- store request and followed status in json (it uses to be only followed)
- using `app_current` instead `info` for checking if the app is opened
- check for crash dialog when app crashes
- check if it's a live video before opening a story
- for actions with files (`interact-from-file`, `unfollow-form-file` and `remove-followers-from-file`) the script will look inside your account folder and no longer where you start the bot from
### Others
- bump version of UIA2
- trim logs in crash reports
- put your username inside the config when creating it with `gramaddict init username`
- default value for `can-reinteract-after` is now "None" instead of "-1"
- better logs when skipping profiles
## 3.1.5 (2022-02-07)
### Fix
- `app_id` was None for them who used the tool in a fancy way (without using config files)
## 3.1.4 (2022-02-07)
### Fix
- avoid a problem with `check_if_crash_popup_is_there` and `choose_cloned_app` being decorated before starting IG
## 3.1.3 (2022-02-06)
### Fix
- missing parenthesis in calling a method
## 3.1.2 (2022-02-06)
### Fix
- find the profile icon even with the different interface
- wrong arguments for stop_bot function
- workaround for avoiding story watching crash due to a bug of UIA2
### Performance improvements
- check if IG is opened when we try to find an element, raise an exception if it's not true (I used a decorator, for fun :D)
- simplify some functions
### Others
- move close_keyboard method to universal class
- a lot of typos
- some types hint
## 3.1.1 (2022-02-01)
### Fix
- inconsistent way to store datetime in json
## 3.1.0 (2022-01-31)
### New Features
- new argument `dont-type` allows writing text by pasting it instead of typing it
- you can go next line in your PM by adding `\n` in the text
### Fix
- the bot wasn't able to confirm the like if the button was not visible in the view
### Others
- don't show countdown in debug mode
## 3.0.5 (2022-01-26)
### Fix
- avoid pressing on music tab instead of hashtags (this bug was only for small screens)
### Others
- the bot restarts after a crash, except for some scenarios that will be highlighted
## 3.0.4 (2022-01-17)
### Fix
- carousel mid-point calculation was wrong (typo)
## 3.0.3 (2022-01-17)
### Fix
- in the new version (217..) the element for sorting following list has changed
### Performance improvements
-  better info when min-following is used in unfollow actions, or you're trying to unfollow more people than the number you're following
-  handle of malformed data in telegram-reports
## 3.0.2 (2022-01-10)
### Fix
- "back" in "Follow Back" is not uppercase anymore
### Performance improvements
- better handling for not loaded profiles
## 3.0.1 (2022-01-05)
### Fix
- missing argument in analytics report

### Others
- new logo for the readme.md
- added some useful info for the user

## 3.0.0 (2022-01-05)
### New Features

- use the cloned app instead the official, if the dialog box get displayed (this is currently supporter for MIUI devices)
- new filter options: *interact_if_public* and *interact_if_private*
- *interact_only_private* has been removed, delete it from your filters.yml

### Performance improvements

- limit check was wrong in interact_blogger plugin
- feed job was ignoring limits
- don't throw an error if config files \*.yaml instead of \*.yml are used
- likes_limit was referring to total_likes_limit and not current_likes_limit (that caused an error if you specify an interval)

### Performance improvements

- jobs have been split in "active-" and "unfollow-" jobs. That means, for example, that the bot won't stop the activity if it reached the likes limit, and you scheduled to unfollow.
- you can pass how many users have to be processed when working with \*.text (unfollow-from-list and interact-from-list)
- bot flow improved
- feed job improvements
- looking for description improvements
- better handle of empty biographies
- showing session ending conditions at bot start
- countdown before starting, so you can check that everything is ok (filters and ending conditions)
- before starting, the bot will tell you the filters you are going to use (there is no spell check there, if you wrote them wrong they will be displayed there but not get considered)
- disable head notifications while the bot is running
- removed unnecessary argument in check_limit function
- removed some unnecessary classes in story view
- move Filter instance outside of plugins
## 2.10.6 (2021-11-24)

#### Performance improvements

* the parsing of the number of posts / followers / following could fail for someone

Full set of changes: [`2.10.4...2.10.6`](https://github.com/GramAddict/bot/compare/2.10.4...2.10.6)
## 2.10.5 (2021-11-18)

#### Fixes

* 'NoneType' object has no attribute '_is_post_liked'
#### Others

* removed a typo

Full set of changes: [`2.10.4...2.10.5`](https://github.com/GramAddict/bot/compare/2.10.4...2.10.5)

## 2.10.4 (2021-11-08)

#### Fixes

* scraped is now counted as successful interaction

Full set of changes: [`2.10.3...2.10.4`](https://github.com/GramAddict/bot/compare/2.10.3...2.10.4)

## 2.10.3 (2021-11-06)

#### Fixes

* the bot did not inform about the skip in case of the filter on mutual friends or on the link in bio
* false positive for link check in bio

Full set of changes: [`2.10.2...2.10.3`](https://github.com/GramAddict/bot/compare/2.10.2...2.10.3)

## 2.10.2 (2021-11-06)

#### Fixes

* link in bio object exists even if it's empty

Full set of changes: [`2.10.1...2.10.2`](https://github.com/GramAddict/bot/compare/2.10.1...2.10.2)

## 2.10.1 (2021-10-31)

#### Fixes

* someone in the world has a " ’ " as thousands separator instead of " , "

Full set of changes: [`2.10.0...2.10.1`](https://github.com/GramAddict/bot/compare/2.10.0...2.10.1)

## 2.10.0 (2021-10-27)

#### New Features

* you can control if comment carousels
* support for connect_adb_wifi uia2 method
* support for watching videos and check for already liked posts
#### Fixes

* trying to close the android pop-up if ig crashes
* looking for the like button on the following video instead of the one being played
* comment fails on some media types
* checking media_type could fail
* empty files in unfollow from list job
* unfollow from list loop
* removed unexpected keyword argument in getFollowinCount method
* method connect_adb_wifi contained some errors
* was being imported nan by numpy instead of the math module
* ig is not opened but the bot tries to do operations
#### Performance improvements

* video recording
* posts-from-file job improved and fixed
* little improvements to the module mode

Full set of changes: [`2.9.2...2.10.0`](https://github.com/GramAddict/bot/compare/2.9.2...2.10.0)

## 2.9.2 (2021-10-06)

#### Fixes

* other incompatibilities in the latest IG version

Full set of changes: [`2.9.1...2.9.2`](https://github.com/GramAddict/bot/compare/2.9.1...2.9.2)

## 2.9.1 (2021-10-06)

#### New Features

* module version thanks to @patbengr
* if a username in *.txt file is not found, it will be appended to a *_not_found.txt
* from now, you can customize the session ending conditions
#### Fixes

* compatibility with IG: 208.0.0.32.135
* cannot check the language of Ig if not at the top of the account
* handle an exception in case you start the bot without specifying the config file
* it could happen that you are not at the top of your main profile in some circumstances
#### Performance improvements

* clean code for open and close ig

Full set of changes: [`2.9.0...2.9.1`](https://github.com/GramAddict/bot/compare/2.9.0...2.9.1)

## 2.9.0 (2021-08-25)

#### New Features

* new argument to control how many skips in jobs with posts (e.g.: hashtag-post-top) are allowed before moving to another source / job
* new job to unfollow people who are following you
* new filter for skipping accounts with banned biography language
#### Performance improvements

* improved readability of the code and correct some typos
* moving sibling folders of run.py will no longer executed automatically

Full set of changes: [`2.8.0...2.9.0`](https://github.com/GramAddict/bot/compare/2.8.0...2.9.0)

## 2.8.0 (2021-08-04)

#### New Features

* new filters: 'skip_if_link_in_bio: true/false' and 'mutual_friends: a_number' min count
* new feature added: pre- and post-script execution

Full set of changes: [`2.7.7...2.8.0`](https://github.com/GramAddict/bot/compare/2.7.7...2.8.0)

## 2.7.7 (2021-08-03)

#### Fixes

* place first post not found [#208](https://github.com/GramAddict/bot/issues/208)
* replace detect-block with disable-block-detection
#### Performance improvements

* removed unneeded class and sort imports

Full set of changes: [`2.7.6...2.7.7`](https://github.com/GramAddict/bot/compare/2.7.6...2.7.7)

## 2.7.6 (2021-07-31)

#### Fixes

* missing resource id for sorting following list

Full set of changes: [`2.7.5...2.7.6`](https://github.com/GramAddict/bot/compare/2.7.5...2.7.6)

## 2.7.5 (2021-07-30)

#### New Features

* new argument "detect_block: true/false" to enable/ disable block check after every action
#### Fixes

* a better way to sort following list [#207](https://github.com/GramAddict/bot/issues/207)
#### Performance improvements

* add debug info for swipes
#### Refactorings

* sort imports

Full set of changes: [`2.7.4...2.7.5`](https://github.com/GramAddict/bot/compare/2.7.4...2.7.5)

## 2.7.4 (2021-07-25)

#### Fixes

* support for Ig v. 197.0.0.26.119

Full set of changes: [`2.7.3...2.7.4`](https://github.com/GramAddict/bot/compare/2.7.3...2.7.4)

## 2.7.3 (2021-07-14)

#### Fixes

* sometimes the bot press on 'Switch IME' instead of open your profile
* automatic change in English locale stopped working

Full set of changes: [`2.7.2...2.7.3`](https://github.com/GramAddict/bot/compare/2.7.2...2.7.3)

## 2.7.2 (2021-07-14)

#### Fixes

* bug in open post container when someone in your 'following list' has also liked the post
#### Performance improvements

* lowered a little the swipe up in sorting `Following accounts`

Full set of changes: [`2.7.1...2.7.2`](https://github.com/GramAddict/bot/compare/2.7.1...2.7.2)

## 2.7.1 (2021-07-13)

#### New Features

* you can dump your current screen with that command `gramaddict dump`
#### Performance improvements

* we don't need to click on an obj if we are already on it

Full set of changes: [`2.7.0...2.7.1`](https://github.com/GramAddict/bot/compare/2.7.0...2.7.1)

## 2.7.0 (2021-07-12)

#### New Features

* you can use spintax for comments and PM from now
#### Fixes

* forgot to remove 'time_left' when calling print_telegram_reports at the end of all sessions
* in config-examples forgot 'comment_blogger' and fix typo in 'comment_blogger_following'

Full set of changes: [`2.6.5...2.7.0`](https://github.com/GramAddict/bot/compare/2.6.5...2.7.0)

## 2.6.5 (2021-07-06)

#### Fixes

* the count of items in the carousels stopped at the first match
* from now on, every type of interaction is counted as successful and not just likes

Full set of changes: [`2.6.4...2.6.5`](https://github.com/GramAddict/bot/compare/2.6.4...2.6.5)

## 2.6.4 (2021-07-01)

#### Fixes

* telegram-reports when out of working hours crashed
#### Performance improvements

* improve update checking
#### Docs

* text improvement and typo corrections

Full set of changes: [`2.6.3...2.6.4`](https://github.com/GramAddict/bot/compare/2.6.3...2.6.4)

## 2.6.3 (2021-06-26)

#### Fixes

* time left in telegram-reports was wrong

Full set of changes: [`2.6.2...2.6.3`](https://github.com/GramAddict/bot/compare/2.6.2...2.6.3)

## 2.6.2 (2021-06-25)

#### Fixes

* there was a problem with likers list
* there was a problem with the way I moved the reports at the end of sessions
#### Performance improvements

* the bot can recognize hashtag suggestions in feed
* telegram-reports improved
#### Docs

* typo in readme

Full set of changes: [`2.6.1...2.6.2`](https://github.com/GramAddict/bot/compare/2.6.1...2.6.2)

## 2.6.1 (2021-06-24)

#### Performance improvements

* we can use an entry point from now
#### Docs

* correct a typo in telegram-reports
* improved the README

Full set of changes: [`2.6.0...2.6.1`](https://github.com/GramAddict/bot/compare/2.6.0...2.6.1)

## 2.6.0 (2021-06-24)

#### New Features

* you can run GramAddict from the command line for initializing your account folder with all the files needed
* add support for allow re-interaction after a given amount of hours
#### Fixes

* too many `filters.yml is not loaded`
* telegram-reports typo in report
* add support for viewers count where likes count is missing
* browse the carousel could fail in some circumstances
#### Docs

* completely rewrote the README.md
#### Others

* donation alert when bot stops by pressing CTRL+C
