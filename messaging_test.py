import os
import requests
import json
import time
import threading
import random
def test_broadcast(local):
    

    threads = []

    def concurrent(address):
        
        print("sending to ip: " + address)
        msg = {"val": str(random.randint(0,1000))}
        response = requests.post(address, json = msg)
        response = response.json()
        if "result" in response:
            print(address, "success")
        else:
            print(address, "failure")

    address = local + ":" + str(8082) + "/kv-store/test_POST"
    address2 = local + ":" + str(8083) + "/kv-store/test_POST"
    for x in range(10):
        thread = threading.Thread(target=concurrent, args=(address,))
        thread.start()
        threads.append(thread)
        # thread = threading.Thread(target=concurrent, args=(address2,))
        # thread.start()
        # threads.append(thread)
        
    # random.shuffle(threads)
    # for x in threads:
        # x.start()
    for x in threads:
        x.join()

    return "done"

if __name__ == "__main__":

    local = "http://127.0.0.1"
    name = "paxos"
    internal_port = 5000
    external_port = 5000
    ip = "10.0.0."
    net = "mynet"

    test_broadcast(local)

# sudo docker run -p 5000:5000 -e VIEW=10.0.0.249:8082 -e IPPORT=10.0.0.153:5000 paxos
# sudo docker run -p 5000:5000 -e VIEW=10.0.0.153:5000 -e IPPORT=10.0.0.249:5000 paxos

# sudo docker run -p 8082:5000 --ip=10.0.0.2 --net=mynet  -e VIEW=10.0.0.2:5000,10.0.0.3:5000 -e IPPORT=10.0.0.2:5000 paxos
# sudo docker run -p 8083:5000 --ip=10.0.0.3 --net=mynet  -e VIEW=10.0.0.2:5000,10.0.0.3:5000 -e IPPORT=10.0.0.3:5000 paxos