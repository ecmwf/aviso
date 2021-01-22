from pyaviso import NotificationManager

# define function to be called
def do_something(notification):
    print(f"Notification for step {notification['request']['step']} received")
    # now do something useful with it ...

# define the trigger
trigger = {"type": "function", "function": do_something}

# create a event listener request that uses that trigger
request = {"key1": "value1", "key2": "20210101", "key3": "a"}
listeners = {"listeners": [{"event": "generic1", "request": request, "triggers": [trigger]}]}

# run it
aviso = NotificationManager()
aviso.listen(listeners=listeners)