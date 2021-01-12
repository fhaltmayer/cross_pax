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

base_proposal = 0
base_proposal_lock = threading.Lock()

min_proposal = -1
min_proposal_lock = threading.Lock()

accepted_val = None
accepted_val_lock = threading.Lock()

accepted_proposal = -1
accepted_proposal_lock = threading.Lock()

test_val = None
test_comes = []




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
    majority = len(view)// 2


@app.route('/', methods = ['GET'])
def home():
    global view 
    global my_id
    global my_ip
    global test_val
    global test_comes
    global accepted_val
    global accepted_proposal
    # global proposal_number
    proposal_number = 0
    info = flask.jsonify({"my_id": my_id, "my_ip": my_ip, "view": view, "test_val": test_val, "outcomes": test_comes, "accepted_val": accepted_val, "accepted_proposal": accepted_proposal})
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
    global min_proposal
    global accepted_proposal
    global accepted_proposal_lock
    global accepted_val
    global accepted_val_lock

    msg = None
    res = request.get_json()
    
    if res["msg"] == "prepare":

        with accepted_val_lock:
            with accepted_proposal_lock:
                if accepted_proposal > -1:
                    msg = {"result": "accepted", "accepted_proposal": accepted_proposal, "accepted_val": accepted_val}
        
        if msg != None:
            return flask.jsonify(msg)

        inc_pn = res["proposal_number"]
        
        with min_proposal_lock:
            if inc_pn < min_proposal:
                msg = {"result": "nack", "min_proposal": min_proposal}

            elif inc_pn > min_proposal:
                min_proposal = inc_pn
                msg = {"result": "promise"}

        

        return flask.jsonify(msg)

    if res["msg"] == "accept":


        
        inc_pn = res["proposal_number"]
        
        with min_proposal_lock:
            
            if inc_pn >= min_proposal:
                with accepted_val_lock:
                    with accepted_proposal_lock:
                       accepted_proposal = inc_pn
                       accepted_val = res["val"]
                       min_proposal = inc_pn

            msg = {"result": min_proposal}


        

        return flask.jsonify(msg)




@app.route('/kv-store/test_POST', methods = ['POST'])
def test_POST():

    res = request.get_json()
    val = res["val"]
    redo = True
    
    
    while redo:
        proposal_number, accept_val = prepare(val)
        redo = accept(base_proposal, accept_val)
    
    return flask.jsonify({"Success":1}) 

def prepare(val):
    global base_proposal
    global view
    outcome = False
    already_accepted = False
    accepted_val = None
    proposal_number = None
    while not outcome:

        # add exponential backoff here
        with base_proposal_lock:
            base_proposal += 1

        # calculation based on having 100 nodes
        proposal_number = (base_proposal) * 100 + my_id       

        msg = {"msg": "prepare", "proposal_number": proposal_number, "val": val}
        

        outcomes = []
        threads = []
        stop_threads = False

        for address in view:
            thread = threading.Thread(target=prepare_thread, args=(msg, "http://" + address + "/kv-store/test_recieve", outcomes, lambda: stop_threads))
            threads.append(thread)
            thread.start()

        already_accepted = False
        accepted_val = None

        # Decide how long to loop waiting to see if there is a larger accepted value
        wait_response = True

        # Use this area for seeing if i need to rerun the entire process with a larger proposal number, add checks to see if ive gotten stuff about
        while wait_response: 
            
            time.sleep(.1)
            
            outcomes.sort(reverse=True)
            global test_comes
            test_comes.append(outcomes)

            if len(outcomes) > 0 and outcomes[0][0] > -1:
                already_accepted = True
                accepted_val = outcomes[0][1]

            if len(outcomes) - outcomes.count((-1, "nack")) >= majority:
                stop_threads = True
                outcome = True
                wait_response = False

            elif outcomes.count((-1, "nack")) >= majority:
                stop_threads = True
                wait_reponse = False
    
    if already_accepted:
        return proposal_number, accepted_val
    else:
        return proposal_number, val



def prepare_thread(msg, address, outcomes, stop_threads):
    global base_proposal
    global base_proposal_lock  
    
    success = False
    while (not stop_threads) or (not success):
        res = requests.post(address, json = msg, timeout=1)
        if res:
            res = res.json()
            if res["result"] == "nack":
                with base_proposal_lock:
                    if base_proposal < res["min_proposal"]//100:
                        base_proposal = res["min_proposal"]//100

                outcomes.append((-1, "nack"))
                success = True

            elif res["result"] == "accepted":
                outcomes.append((res["accepted_proposal"], res["accepted_val"]))
                success = True

            elif res["result"] == "promise":
                outcomes.append((-1, "promise"))
                success = True
            else:
                print("Dont understand prepare message")
                success = True

def accept(proposal_number, val):
    global view
    global accepted_val_lock
    global accepted_val
    global accepted_proposal_lock
    global accepted_proposal

    
    # add exponential backoff here
  
    msg = {"msg": "accept", "proposal_number": proposal_number, "val": val}
    
    outcomes = []
    threads = []
    stop_threads = False

    for address in view:
        thread = threading.Thread(target=accept_thread, args=(msg, "http://" + address + "/kv-store/test_recieve", outcomes, lambda: stop_threads))
        threads.append(thread)
        thread.start()


    # Decide how long to loop waiting to see if there is a larger accepted value
    wait_response = True
    redo = False

    # Use this area for seeing if i need to rerun the entire process with a larger proposal number, add checks to see if ive gotten stuff about
    while wait_response: 
        
        time.sleep(.1)

        if len(outcomes) >= majority:
            if "reject" in outcomes:
                redo = True
            stop_threads = True
            outcome = True
            wait_response = False

    if not redo:
        with accepted_val_lock:
            accepted_val = val
            with accepted_proposal_lock:
                accepted_proposal = proposal_number
    return redo


def accept_thread(msg, address, outcomes, stop_threads):  
    success = False
    while (not stop_threads) or (not success):
        res = requests.post(address, json = msg, timeout=1)
        if res:
            res = res.json()
            if res["result"] > msg["proposal_number"]:
                outcomes.append("reject")
                success = True

            elif res["result"] <= msg["proposal_number"]:
                success = True
                outcomes.append("accept")
           
            else:
                print("Dont understand prepare message")
                success = True







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