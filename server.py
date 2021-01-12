import flask
import os
import requests
import time
import threading
import json

from kv_log import KV
from flask import request
from apscheduler.schedulers.background import BackgroundScheduler

app = flask.Flask(__name__)
app.config["DEBUG"] = True

my_id = None
my_ip = None
view = []
majority = None
kv_log = KV()
proposal_number = 0 
min_proposal = 0
test_val = {}



def startup():
    global my_id
    global my_ip
    global view
    global majority

    my_ip = os.environ['IPPORT']
    my_id = my_ip.split(":")[0]
    my_id = int(my_id.split(".")[-1])
    other_ip = os.environ['VIEW']
    ips = other_ip.split(',')
    for x in ips:
        if x != my_ip:
            view.append(x)
    majority = len(view)// 2 + 1


@app.route('/', methods = ['GET'])
def home():
    global view 
    global my_id
    global my_ip
    global test_val
    # global proposal_number
    proposal_number = 0
    info = flask.jsonify({"my_id": my_id, "my_ip": my_ip, "view": view, "test_val": test_val})
    return info

# @app.route('/kv-store/<key>', methods = ['GET'])
# def get_req(key):
#     global kv_log
#     return kv_log.debug_vals()

# @app.route('/kv-store/<key>', methods = ['PUT'])
# def put_req(key):
#     global kv_log
#     req = request.get_json()
#     val = req["val"]
#     spot = kv_log.get_next()
#     kv_log.update_log(spot, 'put', key, val)
#     return kv_log.debug_vals()

# @app.route('/kv-store/<key>', methods = ['DEL'])
# def del_req(key):
#     global kv_log
#     req = request.get_json()
#     val = req["val"]
#     spot = kv_log.get_next()
#     kv_log.update_log(spot, 'del', key)
#     return kv_log.debug_vals()

# @app.route('/kv-store/update', methods = ['GET'])
# def update_req():
#     global kv_log
#     kv_log.update_kv_store()
#     return kv_log.debug_vals()

@app.route('/kv-store/test_recieve', methods = ['POST'])
def test_recieve():
    global test_val
    res = request.get_json()
    key = res["key"]
    val = res["val"]
    test_val["key"] = val
    return flask.jsonify({"status_code": 200})


@app.route('/kv-store/test_POST', methods = ['POST'])
def test_POST():
    global min_proposal
    global majority
    global test_val
    global view


    outcome = False
    outcomes = []
    res = request.get_json()
    key = res["key"]
    val = res["val"]
    test_val["key"] = val
    


    while not outcome:

        min_proposal += 1
        proposal_number = (min_proposal) * 100 + my_id       

        msg = {"key": key, "val": val, "proposal_number": proposal_number}

        outcomes = []
        threads = []
        stop_threads = False
        for address in view:
            thread = threading.Thread(target=test_broad_thread, args=(msg, "http://" + address + "/kv-store/test_recieve", outcomes, lambda: stop_threads))
            threads.append(thread)
            thread.start()
        # Use this area for seeing if i need to rerun the entire process with a larger proposal number, add checks to see if ive gotten stuff about
        for x in range(3):
            time.sleep(.25)
            if outcomes.count(200) > majority:
                stop_threads = True
                outcome = True

    # min_proposal += 1
    # proposal_number = (min_proposal) * 100 + my_id       
    # stop_threads = False
    # msg = {"key": key, "val": val, "proposal_number": proposal_number}
    # outcomes = []
    # threads = []
    # count = 0
    # for address in view:
    #     count += 1
    #     thread = threading.Thread(target=test_broad_thread, args=(msg, "http://" + address + "/kv-store/test_recieve", outcomes, lambda: stop_threads))
    #     threads.append(thread)
    #     thread.start()

    # time.sleep(1)
    # for x in threads:
    #     x.join()
    return flask.jsonify({"outcomes": outcome})            


def test_broad_thread(msg, address, outcomes, stop_threads):
    success = False
    while (not stop_threads) or (not success):
        response = requests.post(address, json = msg, timeout=1)
        if response:
            outcomes.append(200)
            success = True


def prepare(key, val, proposal_number):
    outcome = False
    outcome_content = 0
    msg = json.dumps({"key": key, "val": val, "proposal_number": proposal_number})
    while not outcome:
        requests = []
        threads = []
        stop_threads = False
        for address in view:
            thread = threading.Thread(target=thread_function, args=((key, val, proposal_number), address, lambda: stop_threads))
            threads.append(thread)
            thread.start()

def prepare_thread():  
    requests.post(url)







# def sched_request():
#     global my_ip 
#     global other_ip
#     x = requests.get("http://" + other_ip + ":5000" + '/request')



# if other_ip != False:
#     scheduler = BackgroundScheduler()
#     scheduler.add_job(func=sched_request, trigger="interval", seconds=3)
#     scheduler.start()

   
if __name__ == "__main__":
    startup()
    app.run(host='0.0.0.0', threaded = False)#, use_reloader=False)


# def startup():
#     

# In multi-paxos, peers can lag behind as you noticed. If you read the values from a quorum though you're guaranteed to see the most recent value, the trick is figuring out which one that is. Not all applications need this but if yours does, a very simple augmentation is sufficient. Just use a tuple instead of the raw value where the first item is an update counter and the second is the raw value. Each time a peer tries to update the value, it also updates the counter. So when you read from a quorum, the tuple with the highest update counter is guaranteed to be the most recent value.
# We are going to be running state machine, all continuous actions below x are commited. 
# Figure out how to store max accepted in a dictionary. 

# curl -X PUT -H "Content-Type: application/json" -d '{"key":"value"}' http://localhost:8083/kv-store/key