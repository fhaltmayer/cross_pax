import flask
from flask import request
import os
import requests
import time
import threading
from kv_log import KV

from apscheduler.schedulers.background import BackgroundScheduler

app = flask.Flask(__name__)
app.config["DEBUG"] = True

my_ip = ""
my_port = ""
key_value = {}
view = []
kv_log = KV()
proposal_number = 0 
# request_count_lock = threading.Lock()
# add decimal to proposal on each send. 



def get_ips():
    global my_ip
    global my_port
    global view
    global proposal_number
    my_ip = os.environ['IPPORT']
    my_port = my_ip.split(":")[1]
    other_ip = os.environ['VIEW']
    ips = other_ip.split(',')
    for x in ips:
        if x != my_ip:
            view.append(x)


@app.route('/', methods = ['GET'])
def home():
    global view 
    global my_port
    global proposal_number
    return "proposal_number: " + str(proposal_number) + " View: " + str(view)

@app.route('/kv-store/<key>', methods = ['GET'])
def get_req(key):
    global kv_log
    return kv_log.debug_vals()

@app.route('/kv-store/<key>', methods = ['PUT'])
def put_req(key):
    global kv_log
    req = request.get_json()
    val = req["val"]
    spot = kv_log.get_next()
    kv_log.update_log(spot, 'put', key, val)
    return kv_log.debug_vals()

@app.route('/kv-store/<key>', methods = ['DEL'])
def del_req(key):
    global kv_log
    req = request.get_json()
    val = req["val"]
    spot = kv_log.get_next()
    kv_log.update_log(spot, 'del', key)
    return kv_log.debug_vals()

@app.route('/kv-store/update', methods = ['GET'])
def update_req():
    global kv_log
    kv_log.update_kv_store()
    return kv_log.debug_vals()

@app.route('/kv-store/pax_inc', methods = ['GET'])
def incoming_req():
    global kv_log
    kv_log.update_kv_store()
    return kv_log.debug_vals()




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
# Figure out how to store max accepted in a dictionary. 

# curl -X PUT -H "Content-Type: application/json" -d '{"key":"value"}' http://localhost:8083/kv-store/key