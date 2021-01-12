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
    address = local + ":" + str(8082) + "/kv-store/test_POST"
    print("sending to ip: " + address)
    response = requests.post(address, json = {"val": "val2"})
    print(response)

if __name__ == "__main__":

    local = "http://127.0.0.1"
    name = "paxos"
    internal_port = 5000
    external_port = 8080
    ip = "10.0.0."
    net = "mynet"

    test_broadcast(local)