import uiautomator2 as u2

d = u2.connect()
d.service("uiautomator").stop()
d.service("uiautomator").start()
