import flask
import os
import requests
import time
import threading
import json
import random
# from kv_log import KV
from flask import request
from redis_commands import Log
# from apscheduler.schedulers.background import BackgroundScheduler

app = flask.Flask(__name__)
app.config["DEBUG"] = True

my_id = None
my_ip = None
view = []
majority = None
largest_id = None
log = None




def startup():
    global my_id
    global my_ip
    global view
    global majority
    global log


    my_ip = os.environ['IPPORT']
    my_id = my_ip.split(":")[0]
    my_id = int(my_id.split(".")[-1])
    other_ip = os.environ['VIEW']
    ips = other_ip.split(',')
    for x in ips:
        view.append(x)
    majority = len(view)// 2
    log = Log(my_id)
    log.r.set("created_loc_pax", "Created entry from paxos request:")
    log.r.set("created_locs_client", "Created entry from client request:")
    log.r.set("accepted_recieve", "Accepted Already recieved:")
    log.r.set("accept_sent_sent", "Accepted Already sent out:")
    log.r.set("promise_own", "I promise my own: ")



    # Might break with multithreaded process
    # def heartbeat(view, timeout):
    #     for x in view:
    #         address = "http://" + x + "/heartbeat"
    #         res = requests.get(address, timeout = timeout)
    #         if res:



    # scheduler = BackgroundScheduler()
    # scheduler.add_job(func=heartbeat, trigger="interval", seconds=3)
    # scheduler.start()

       


@app.route('/', methods = ['GET'])
def home():
    global log

    print(flush=True)

    returnal = {}

    for x in log.r.scan_iter(_type="HASH"):
        returnal[int(x)] = str(log.r.hgetall(x))

    returnal[-1] = str(log.r.get("created_loc_pax"))
    returnal[-2] = str(log.r.get("created_locs_client"))
    returnal[-3] = str(log.r.get("accept_recieve"))
    returnal[-4] = str(log.r.get("accept_sent"))
    returnal[-5] = str(log.r.get("promise_own"))

    return flask.jsonify(returnal)

@app.route('/kv-store/heartbeat', methods = ['GET'])
def heartbeat():
    return "Success"

@app.route('/kv-store/prepare_recieval', methods = ['POST'])
def prepare_recieval():
    res = request.get_json()

    msg = common_prepare(res)

    return flask.jsonify(msg)

def common_prepare(res):
    global log

    msg = None

    
    inc_pn = res["proposal_number"]

    location = res["location"]
    
    created = log.prepare_loc(location)

    if created:
        log.r.append("created_loc_pax", " " + str(location))

    log.get_lock(location)

    min_proposal = int(log.r.hget(str(location), "min_proposal"))

    print("prepare recieved: ", inc_pn, min_proposal, flush=True)

    # Test if == or >= necessary
    if inc_pn >= min_proposal:

        msg = {"location": location, "result": "nack", "min_proposal": min_proposal}

    else:

        log.r.hset(str(location), "min_proposal", str(inc_pn))
        base = int(log.r.hget(str(location), "base_proposal"))
        already_accepted = int(log.r.hget(str(location),"already_accepted"))
        server_limit = int(log.r.get("server_limit"))

        # Test to see if worth catching up base proposal
        # if min_proposal//server_limit > base:

        #     log.r.hset(str(location), "base_proposal", str(min_proposal//server_limit))

        if already_accepted == 1:

            accepted_proposal = int(log.r.hget(str(location), "accepted_proposal"))
            accepted_val = log.r.hget(str(location), "accepted_val").decode('utf-8')

            msg = {"location": location, "result": "accepted", "accepted_proposal": accepted_proposal, "accepted_val": accepted_val}
            log.r.append("accept_sent", " " + str(location))

        else:

            msg = {"location": location, "result": "promise"}

    log.release_lock(location)

    return msg


@app.route('/kv-store/accept_recieval', methods = ['POST'])
def accept_recieval():
    global log

    res = request.get_json()    

    msg = common_accept(res)

    return flask.jsonify(msg)

def common_accept(res):

    inc_pn = res["proposal_number"]
    
    location = res["location"]

    msg = {"location": location,"result": "denied"}

    log.get_lock(location)

    min_proposal = int(log.r.hget(str(location), "min_proposal"))
    
    print("accepted recieved: ", inc_pn, min_proposal, flush=True)

    # Test if == or >=
    if inc_pn >= min_proposal:

        log.r.hset(str(location), "accepted_proposal", str(inc_pn))
        log.r.hset(str(location), "accepted_val", str(res["val"]))
        log.r.hset(str(location), "already_accepted", str(1))

        base = int(log.r.hget(str(location), "base_proposal"))
        server_limit = int(log.r.get("server_limit"))

        # Test if necessary to catch up base
        # if min_proposal//server_limit > base:

        #     log.r.hset(str(location), "base_proposal", str(min_proposal//server_limit))
           

        msg = {"location": location,"result": "accepted"}

    log.release_lock(location)

    return msg



@app.route('/kv-store/test_POST', methods = ['POST'])
def test_POST():
    global log
    
    res = request.get_json()
    val = res["val"]

    successful_log_entry = False


    while not successful_log_entry:

        redo = True
        decided_val = None

        next_loc = log.get_next_loc()
        created = log.prepare_loc(next_loc)

        if created:
            log.r.append("created_locs_client", " " + str(next_loc))

        while redo:
            proposal_number, decided_val = prepare(next_loc, val)
            redo = accept(next_loc, proposal_number, decided_val)
        
        if val == decided_val:
            successful_log_entry = True
        
            
            
    return flask.jsonify({"result": "success", "val": val}) 

def prepare(location, val):
    global view
    global log
    global my_id
    global majority

    outcome = False
    already_accepted = False
    accepted_val = None
    proposal_number = None
    backoff = False
    exponent = 1

    while not outcome:

        # add exponential backoff here
        if backoff:
            print("backing off exponent:", exponent, flush=True)
            time.sleep(random.random()*5*exponent)
            exponent += 1
        
        proposal_number = log.get_proposal(location)
       
        msg = {"location": location, "msg": "prepare", "proposal_number": proposal_number}
        outcomes = []
        threads = []
        stop_threads = False

        for address in view:
            thread = threading.Thread(target=prepare_thread, args=(msg, address, outcomes, lambda: stop_threads, location) )
            threads.append(thread)
            thread.start()

        already_accepted = False
        accepted_val = None

        # Decide how long to loop waiting to see if there is a larger accepted val
        wait_response = True
        count = 5
        loop_sleep = .5

        while wait_response and count > 0: 
            
            time.sleep(loop_sleep)
            
            outcomes.sort(reverse=True)

            if len(outcomes) - outcomes.count((-1, "nack")) > majority:
                if outcomes[0][0] > -1:
                    already_accepted = True
                    prev_accepted_val = outcomes[0][1]
                    log.r.append("accept_recieve", "At_Loc:" + str(location) + " " + str(prev_accepted_val))

                stop_threads = True
                outcome = True
                wait_response = False

            elif outcomes.count((-1, "nack")) > majority:
                stop_threads = True
                wait_reponse = False
            else:
                count -=1
        print(len)

        stop_threads = True

        backoff = True

        # log.r.delete(outcomes)

    if already_accepted:
        return proposal_number, prev_accepted_val
    else:
        return proposal_number, val



def prepare_thread(msg, address, outcomes, stop_threads, location):
    global my_ip
    global log

    if address == my_ip:



        res = common_prepare(msg)

        if res["result"] == "nack":
            outcomes.append((-1, "nack"))
            log.r.append("promise_own", " no-" + str(location))



        elif res["result"] == "accepted":
            outcomes.append((res["accepted_proposal"], res["accepted_val"]))
            # log.r.append("promise_own", "At_Loc:" + str(location) + " " + str(prev_accepted_val))

        elif res["result"] == "promise":
            outcomes.append((-1, "promise"))
            log.r.append("promise_own", " yes-" + str(location))


        else:
            print("Dont understand prepare message")

    else:
        success = False
        count = 3
        while  (not stop_threads()) and (not success):
            try:
                res = requests.post("http://" + address + "/kv-store/prepare_recieval", json = msg, timeout=.25)
            except:
                res = None
            if res:
                res = res.json()
                if res:
                    if res["result"] == "nack":
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
            else:
                count -= 1
                if count < 0:
                    outcomes.append((-1, "nack"))
                    success = True


      
        # time.sleep(.1)


def accept(location, proposal_number, val):
    global view
    global log
    global majority

    
    # add exponential backoff here
  
    msg = {"location": location, "msg": "accept", "proposal_number": proposal_number, "val": val}

    outcomes = []
    threads = []
    stop_threads = False

    for address in view:
        thread = threading.Thread(target=accept_thread, args=(msg, address, outcomes, lambda: stop_threads))
        threads.append(thread)
        thread.start()


    # Decide how long to loop waiting to see if there is a larger accepted val
    wait_response = True
    redo = False


    # Use this area for seeing if i need to rerun the entire process with a larger proposal number, add checks to see if ive gotten stuff about
    # Add a countdown for lost messages so it does not block
    count = 5
    while wait_response: 

        time.sleep(.5)
        if "reject" in outcomes:
            redo = True
            stop_threads = True
            outcome = True
            wait_response = False

        elif len(outcomes) > majority:
            stop_threads = True
            outcome = True
            wait_response = False
        else:
            count -= 1
            if count == 0:
                redo = True
                wait_response = False
    return redo


def accept_thread(msg, address, outcomes, stop_threads):  
    global my_ip

    if address == my_ip:

        res = common_accept(msg)

        if res["result"] =="rejected":
            outcomes.append("reject")

        elif res["result"] == "accepted":
            outcomes.append("accept")

    else:
        success = False
        count = 3
        while (not stop_threads()) and (not success):
            try:
                res = requests.post("http://" + address + "/kv-store/accept_recieval", json = msg, timeout=.25)
            except:
                res = None
            if res:
                res = res.json()
                if res["result"] =="rejected":
                    success = True
                    outcomes.append("reject")

                elif res["result"] == "accepted":
                    success = True
                    outcomes.append("accept")
            else:
                count -= 1
                if count < 0:
                    success = True
                    outcomes.append("reject")






if __name__ == "__main__":
    startup()
    app.run(host='0.0.0.0', threaded = True)#, use_reloader=False)


# In multi-paxos, peers can lag behind as you noticed. If you read the values from a quorum though you're guaranteed to see the most recent value, the trick is figuring out which one that is. Not all applications need this but if yours does, a very simple augmentation is sufficient. Just use a tuple instead of the raw value where the first item is an update counter and the second is the raw value. Each time a peer tries to update the value, it also updates the counter. So when you read from a quorum, the tuple with the highest update counter is guaranteed to be the most recent value.
# We are going to be running state machine, all continuous actions below x are commited.

# Figure out how to store max accepted in a dictionary. 

# curl -X PUT -H "Content-Type: application/json" -d '{"key":"value"}' http://localhost:8083/kv-store/key
# http://www.beyondthelines.net/algorithm/multi-paxos/