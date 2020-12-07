import requests, json, datetime, queue
from aviso_admin.compactor import Compactor
from aviso_admin.cleaner import Cleaner
from aviso_admin.monitoring.collectors.etcd_collectors import StoreSizeCollector
from aviso_admin.monitoring.etcd_monitor import EtcdMetricType
from aviso_admin import config

"""
This test simulates the store size cycle day by day including:
- notification submission of dissemination keys
- daily compaction 
- daily key deletion
It is not performing submission of mars keys. These anyway account for a small percentage of the total.
"""

frontend_url_api = "http://127.0.0.1:8080/api/v1"
ret_period = 15 # days
run_days = 60  # days
DATE_FORMAT = "%Y%m%d"
starting_day_s = "20201101"


def conf() -> config.Config:  # this automatically configure the logging
    c = config.Config(conf_path="tests/config.yaml")
    return c

def get_current_server_rev():
    compactor = Compactor(conf().compactor)
    rev = compactor.get_current_server_rev()
    return rev

def compact(rev):
    compactor = Compactor(conf().compactor)
    # compact revision
    return compactor.compact(rev)

def delete_dissemination_keys(date, destination):
    config = conf().cleaner
    cleaner = Cleaner(config)
    # delete dissemination keys
    return cleaner.delete_keys(date, destination)

def delete_destination_keys(date):
    config = conf().cleaner
    cleaner = Cleaner(config)
    # delete destinations
    return cleaner.delete_destination_keys(date)

def store_size():
    collector = StoreSizeCollector(EtcdMetricType.etcd_store_size, member_urls=["http://localhost:2379"])
    size = collector.store_size("http://localhost:2379")
    return size 

def submit_notification(destination, target, date):
    body = {
        "type": "aviso",  # aviso type indicates how to interpret the "data" payload
        "data": {  # this is aviso specific
            "event": "dissemination",
            "request": {
                "target": target,
                "class": "od",
                "date": date,
                "destination": destination,
                "domain": "g",
                "expver": "1",
                "step": "2",
                "stream": "enfo",
                "time": "0",
            },
            "location": "s3://data.ecmwf.int/diss/foo/bar/20190810/xyz",  # location on ceph or s3
        },
        "datacontenttype": "application/json",
        "id": "0c02fdc5-148c-43b5-b2fa-cb1f590369ff",
        # UUID random generated by client (maybe reused if request is the same)
        "source": "/host/user",  # together with 'id', uniquely identifies a request
        "specversion": "1.0",
        "time": "2020-03-02T13:34:40.245Z",  # optional, but recommended
    }
    resp = requests.post(f"{frontend_url_api}/notification", json=body)
    return resp.ok

def defrag():
    compactor = Compactor(conf().compactor)
    return compactor.defrag()

# Simulate daily cycle
s_day = datetime.datetime.strptime(starting_day_s, DATE_FORMAT)
curr_rev = get_current_server_rev()
#print(f"Deframentation: {defrag()}")
#print(f"Starting rev {curr_rev}")
#print(f"Starting store size {store_size()}")
print(store_size())
rev_history = queue.Queue()
for day in range(run_days):
    date = s_day + datetime.timedelta(days=day)
    date_s = date.strftime(DATE_FORMAT)
    #print(f"Starting cycle for day {date_s}")

    # submit notifications
    for d in range(50):
        for t in range(60):
            submit_notification(f"DEST{d}", f"T{t}", date_s)
    
    # create the history
    curr_rev = get_current_server_rev()
    #print(f"Current rev {curr_rev}")
    rev_history.put(curr_rev)
    
    if rev_history.qsize() > ret_period:
        # first compact
        old_rev = rev_history.get()
        #print(f"Compacting {old_rev}")
        r = compact(old_rev)
        #print(r)
        # delete keys
        date = date - datetime.timedelta(days=ret_period)
        #print(f"Deleting keys for {date}")
        r = delete_destination_keys(date)
        #print(r)
        tot = 0
        for d in range(50):
            tot += delete_dissemination_keys(date, f"DEST{d}")
        #print(f"Total number of keys deleted {tot}")
        # defrag
        #r = defrag()
        #print(f"Deframentation: {r}")
    print(store_size())
    #print(f"Current store size {store_size()}") 
        
print("End")