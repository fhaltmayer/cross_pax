import threading   
import time
import json

def start_thread():
    temp_list = []
    threads = []
    stop_threads = False
    for x in range(10):
        y = threading.Thread(target=thread_function, args=(temp_list,x, lambda: stop_threads))
        y.start()
        threads.append(y)
    time.sleep(5)
    # for x in threads:
    # 	x.join()
    print(temp_list)

    def thread_function(list, my_count):
    if my_count == 3:
        time.sleep(10)
    list.append(my_count)

    if __name__ == "__main__":
    # start_thread()
    key = "poop"
    val = 2
    proposal_number = 3
    print(json.dumps({"key": key, "val": val, "proposal_number": proposal_number}))
