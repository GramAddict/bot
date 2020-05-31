def double_click(device, *args, **kwargs):
    config = device.server.jsonrpc.getConfigurator()
    config['actionAcknowledgmentTimeout'] = 40
    device.server.jsonrpc.setConfigurator(config)
    device(*args, **kwargs).click()
    device(*args, **kwargs).click()
    config['actionAcknowledgmentTimeout'] = 3000
    device.server.jsonrpc.setConfigurator(config)
