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


debug_recieved_msg = []
debug_sent_msg = []
debug_threads = []
debug_val_log = []

logs_lock = threading.Lock()
val_log = {}
paxos_log = {}
next_free = 0




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
    global majority
    global debug_recieved_msg
    global debug_sent_msg
    global debug_threads
    global debug_val_log
    global val_log
    # global proposal_number
    return flask.jsonify({
                        # "my_id": my_id, 
                        # "my_ip": my_ip, 
                        # "majority": majority, 
                        # "view": view, 
                        "log": val_log, 
                        # "debug_sent_msg": debug_sent_msg, 
                        # "debug_recieved_msg": debug_recieved_msg, 
                        # "debug_threads": debug_threads, 
                        # "debug_val_log": debug_val_log 
                        })

@app.route('/kv-store/test_recieve', methods = ['POST'])
def test_recieve():
    global debug_recieved_msg
    global debug_val_log
    global logs_lock
    global paxos_log
    global val_log
    msg = None

    res = request.get_json()
    debug_recieved_msg.append((res, time.time()))
    
    if res["msg"] == "prepare":

        inc_pn = res["proposal_number"]

        location = res["location"]

        with logs_lock:
            if location not in paxos_log:
                paxos_log[location] = {"base_proposal": 0, "min_proposal": -1, "accepted_val": None, "accepted_proposal": -1,  "lock": threading.Lock()}

        with paxos_log[location]["lock"]:
            
            if inc_pn < paxos_log[location]["min_proposal"]:
                msg = {"location": location, "result": "nack", "min_proposal": paxos_log[location]["min_proposal"]}

            elif inc_pn > paxos_log[location]["min_proposal"]:
                paxos_log[location]["min_proposal"] = inc_pn

                if paxos_log[location]["min_proposal"]//100 > paxos_log[location]["base_proposal"]:
                    paxos_log[location]["base_proposal"] = paxos_log[location]["min_proposal"]//100

                msg = {"location": location, "result": "promise"}

                
                if paxos_log[location]["accepted_proposal"] > -1:
                    msg = {"location": location, "result": "accepted", "accepted_proposal": paxos_log[location]["accepted_proposal"], "accepted_val": paxos_log[location]["accepted_val"]}

        # Seperated msg send due to not wanting to hold lock during message blocking
        return flask.jsonify(msg)

    if res["msg"] == "accept":
        
        inc_pn = res["proposal_number"]
        
        location = res["location"]

        with logs_lock:
            if location not in paxos_log:
                paxos_log[location] = {"base_proposal": 0, "min_proposal": -1, "accepted_val": None, "accepted_proposal": -1,  "lock": threading.Lock()}

        
        with paxos_log[location]["lock"]:
            if inc_pn >= paxos_log[location]["min_proposal"]:
                paxos_log[location]["accepted_proposal"] = inc_pn
                paxos_log[location]["accepted_val"] = res["val"]
                paxos_log[location]["min_proposal"] = inc_pn
                val_log[location] = res["val"]
                
                if paxos_log[location]["min_proposal"]//100 > paxos_log[location]["base_proposal"]:
                    paxos_log[location]["base_proposal"] = paxos_log[location]["min_proposal"]//100
                   
                debug_val_log.append((paxos_log[location]["accepted_proposal"], paxos_log[location]["accepted_val"], "accepted"))

            msg = {"location": location,"result": paxos_log[location]["min_proposal"]}

        return flask.jsonify(msg)




@app.route('/kv-store/test_POST', methods = ['POST'])
def test_POST():
    global val_log
    global paxos_log
    global next_free
    res = request.get_json()
    val = res["val"]

    successful_log_entry = False

    while not successful_log_entry:

        redo = True
        decided_val = None

        with logs_lock:
            while next_free in val_log or next_free in paxos_log:
                next_free += 1
            paxos_log[next_free] = {"base_proposal": 0, "min_proposal": -1, "accepted_val": None, "accepted_proposal": -1,  "lock": threading.Lock()}

        while redo:
            proposal_number, decided_val = prepare(next_free, val)
            redo = accept(next_free, proposal_number, decided_val)
        
        if val != decided_val:
            pass
        else:
            successful_log_entry = True
            
    return flask.jsonify({"result": "success", "val": val}) 

def prepare(location, val):
    global view
    global debug_sent_msg
    global paxos_log

    outcome = False
    already_accepted = False
    accepted_val = None
    proposal_number = None
    backoff = 0
    while not outcome:
        sleep_time = backoff*2
        time.sleep(sleep_time)
        # add exponential backoff here
        with paxos_log[location]["lock"]:
            paxos_log[location]["base_proposal"] += 1
            # calculation based on having 100 nodes
            proposal_number = (paxos_log[location]["base_proposal"]) * 100 + my_id 
       
        msg = {"location": location, "msg": "prepare", "proposal_number": proposal_number, "val": val}
        debug_sent_msg.append((msg, time.time()))

        outcomes = []
        threads = []
        stop_threads = False

        for address in view:
            thread = threading.Thread(target=prepare_thread, args=(msg, "http://" + address + "/kv-store/test_recieve", outcomes, lambda: stop_threads))
            threads.append(thread)
            thread.start()

        already_accepted = False
        accepted_val = None

        # Decide how long to loop waiting to see if there is a larger accepted val
        wait_response = True
        count = 5
        # Use this area for seeing if i need to rerun the entire process with a larger proposal number, add checks to see if ive gotten stuff about
        while wait_response and count > 0: 
            
            time.sleep(.1)
            
            outcomes.sort(reverse=True)
            

            if len(outcomes) > 0 and outcomes[0][0] > -1:
                already_accepted = True
                prev_accepted_val = outcomes[0][1]

            if len(outcomes) - outcomes.count((-1, "nack")) >= majority:
                stop_threads = True
                outcome = True
                wait_response = False

            elif outcomes.count((-1, "nack")) >= majority:
                stop_threads = True
                wait_reponse = False
            count -=1
        backoff += 1
    if already_accepted:
        return proposal_number, prev_accepted_val
    else:
        return proposal_number, val



def prepare_thread(msg, address, outcomes, stop_threads):
    # global paxos_log
    
    success = False
    while (not stop_threads) or (not success):
        res = requests.post(address, json = msg, timeout=.25)
        if res:
            res = res.json()
            if res["result"] == "nack":
                # with base_proposal_lock:
                #     if base_proposal < res["min_proposal"]//100:
                #         base_proposal = res["min_proposal"]//100
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

def accept(location, proposal_number, val):
    global view
    global paxos_log
    global val_log
    global debug_sent_msg
    global debug_val_log

    
    # add exponential backoff here
  
    msg = {"location": location, "msg": "accept", "proposal_number": proposal_number, "val": val}
    debug_sent_msg.append((msg, time.time()))
    outcomes = []
    threads = []
    stop_threads = False

    for address in view:
        thread = threading.Thread(target=accept_thread, args=(msg, "http://" + address + "/kv-store/test_recieve", outcomes, lambda: stop_threads))
        threads.append(thread)
        thread.start()


    # Decide how long to loop waiting to see if there is a larger accepted val
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
        debug_val_log.append((location, proposal_number, val, "to be accepted"))
        with paxos_log[location]["lock"]:
            paxos_log[location]["accepted_val"] = val
            paxos_log[location]["accepted_proposal"] = proposal_number
            debug_val_log.append((paxos_log[location]["accepted_proposal"], paxos_log[location]["accepted_val"], "accepted"))
            val_log[location] = val
    else:
        debug_val_log.append((location, proposal_number, val, "rejected"))

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
    app.run(host='0.0.0.0', threaded = True)#, use_reloader=False)


# def startup():
#     

# In multi-paxos, peers can lag behind as you noticed. If you read the values from a quorum though you're guaranteed to see the most recent value, the trick is figuring out which one that is. Not all applications need this but if yours does, a very simple augmentation is sufficient. Just use a tuple instead of the raw value where the first item is an update counter and the second is the raw value. Each time a peer tries to update the value, it also updates the counter. So when you read from a quorum, the tuple with the highest update counter is guaranteed to be the most recent value.
# We are going to be running state machine, all continuous actions below x are commited. 
# Figure out how to store max accepted in a dictionary. 

# curl -X PUT -H "Content-Type: application/json" -d '{"key":"value"}' http://localhost:8083/kv-store/key
# http://www.beyondthelines.net/algorithm/multi-paxos/