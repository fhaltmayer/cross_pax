import os
import requests
import json
import time
def test_broadcast(local):

    address = local + ":" + str(8082) + "/kv-store/test_POST"
    print("sending to ip: " + address)
    response = requests.post(address, json = {"val": "val"})
    print(response)
    time.sleep(1)
    # address = local + ":" + str(8082) + "/kv-store/test_POST"
    # print("sending to ip: " + address)
    # response = requests.post(address, json = {"val": "val2"})
    # print(response)

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