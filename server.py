import flask
import os
import requests
import time
import threading
from kv_log import kv

from apscheduler.schedulers.background import BackgroundScheduler

app = flask.Flask(__name__)
app.config["DEBUG"] = True

my_ip = ""
key_value = {}
view = {}
state_log = {}
kv_log = kv()
# request_count_lock = threading.Lock()



def get_ips():
    my_ip = os.environ['IPPORT']
    other_ip = os.environ['VIEW']
    ips = other_ip.split(',')
    for x in ips:
        if x != my_ip:
            view.append(x)


@app.route('/', methods = ['GET'])
def home():
    global view 
    return str(view)

@app.route('/kv-store/', methods = ['GET'])
def req():
    global kv 
    return kv.debug_vals()

@app.route('/kv-store/add', methods = ['PUT'])
def req():
    global view 
    global key_value


# def sched_request():
#     global my_ip 
#     global other_ip
#     x = requests.get("http://" + other_ip + ":5000" + '/request')



# if other_ip != False:
#     scheduler = BackgroundScheduler()
#     scheduler.add_job(func=sched_request, trigger="interval", seconds=3)
#     scheduler.start()

   
if __name__ == "__main__":
    get_ips()
    app.run(host='0.0.0.0', threaded = True)#, use_reloader=False)


# def startup():
#     

# In multi-paxos, peers can lag behind as you noticed. If you read the values from a quorum though you're guaranteed to see the most recent value, the trick is figuring out which one that is. Not all applications need this but if yours does, a very simple augmentation is sufficient. Just use a tuple instead of the raw value where the first item is an update counter and the second is the raw value. Each time a peer tries to update the value, it also updates the counter. So when you read from a quorum, the tuple with the highest update counter is guaranteed to be the most recent value.
# We are going to be running state machine, all continuous actions below x are commited. 