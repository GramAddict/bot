from random import randint
from time import sleep

COLOR_HEADER = '\033[95m'
COLOR_OKBLUE = '\033[94m'
COLOR_OKGREEN = '\033[92m'
COLOR_WARNING = '\033[93m'
COLOR_FAIL = '\033[91m'
COLOR_ENDC = '\033[0m'
COLOR_BOLD = '\033[1m'
COLOR_UNDERLINE = '\033[4m'


def double_click(device, *args, **kwargs):
    config = device.server.jsonrpc.getConfigurator()
    config['actionAcknowledgmentTimeout'] = 40
    device.server.jsonrpc.setConfigurator(config)
    device(*args, **kwargs).click()
    device(*args, **kwargs).click()
    config['actionAcknowledgmentTimeout'] = 3000
    device.server.jsonrpc.setConfigurator(config)


def random_sleep():
    delay = randint(1, 4)
    print "Sleep for " + str(delay) + (delay == 1 and " second" or " seconds")
    sleep(delay)
