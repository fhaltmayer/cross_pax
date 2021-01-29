import redis
import json
import threading

class Log(object):
    def __init__(self, my_id, my_ip, view, majority, host='localhost', port=6379, server_limit = 100, ):
        self.r = redis.Redis(host=host, port=port, db=0)
        self.r.set("last_used","-1")
        self.r.set("server_limit", str(server_limit))
        self.my_id = my_id
        self.my_ip = my_ip
        self.r.hset("view", mapping = view)
        self.r.set("majority", str(majority))
        self.r.set("leader", my_ip)

    def get_lock(self, location):
        getting_lock = True

        while getting_lock:
            if self.r.setnx(str(location) + ".lock", "1") == 1:
                getting_lock = False

    # def get_min_proposal(self, location)

    def release_lock(self, location):
        self.r.delete(str(location) + ".lock")

    def get_next_loc(self):

        self.get_lock("-1")
        last_used = int(self.r.get("last_used"))
        next_free = last_used + 1

        while self.r.exists(str(next_free)) and not (self.r.hexists(str(next_free), "value") == "N"):
            next_free += 1

        self.r.set("last_used", str(next_free))

        self.release_lock("-1")

        return next_free

    def update_leader(self, view):
        self.get_lock("leader_elect")

        for x in view:
            self.r.hset("view", x, view[x])
        new_leader = (None, -1)
        for x in self.r.hkeys("view"):
            if int(self.r.hget("view", x)) > new_leader[1]:
                new_leader = (x.decode("utf-8"), int(self.r.hget("view", x)))

        self.r.set("leader", new_leader[0])
        
        self.release_lock("leader_elect")
        




    def prepare_loc(self, location):
        self.get_lock(location)
        returnal = False
        if self.r.exists(str(location)) == 0:
            maps = {"base_proposal": "0", "min_proposal": "-1", "accepted_val": "N", "accepted_proposal": "-1", "already_accepted": "-1"}
            self.r.hset(str(location), mapping=maps)
            returnal = True
        self.release_lock(location)
        return returnal

    def get_proposal(self, location):
        self.get_lock(location)
        base = int(self.r.hget(str(location), "base_proposal"))
        base += 1
        server_limit = int(self.r.get("server_limit"))
        self.r.hset(str(location), "base_proposal", str(base))
        self.release_lock(location)
        return base * server_limit + int(self.my_id)

    # def base_prop_update(self, location, new):
    #     self.get_lock(location)
    #     base = int(self.r.hget(str(location), "base_proposal"))
    #     if base < new:
    #         self.r.hset(str(location), "base_proposal", str(new))
    #     self.release_lock(location)

    def update_value(self, location, proposal, value):
        self.get_lock(location)

        min_proposal = int(self.r.hget(str(location), "min_proposal"))

        if proposal == min_proposal:
            self.r.hset(str(location), "accepted_val", str(value))
            self.r.hset(str(location), "accepted_proposal", str(proposal))
            self.r.hset(str(location), "already_accepted", str(True))
            self.release_lock(location)
            return True
        else:
            self.release_lock(location)
            return False

if __name__== "__main__":
    # print("wtf")
    temp = Log(my_id=2, server_limit=100)
    temp.r.flushall()
    temp = Log(my_id=2, server_limit=100)
    # temp.r.flushall()
    # print("wtf2")
    # print(temp.get_next_loc())

    # temp.r.flushall()
    def conc(redis):
        loc = redis.get_next_loc()
        print(loc)
        redis.prepare_loc(loc)
    threads = []
    for x in range(10):
        thread = threading.Thread(target=conc, args=(temp,))
        thread.start()
        threads.append(thread)
    for x in threads:
        x.join()
    temp.update_value(0,-1,"oogabooga")
    print(temp.get_proposal(0))

    for x in temp.r.scan_iter(_type="HASH"):
        print(temp.r.hgetall(x))

    # print(temp.r.hget("1", "accepted_val"))

    
# Continue work at accept

