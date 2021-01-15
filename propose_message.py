class Propose_Msg:
	def __init__(self, n, val):   
        self.kv_store = {}
        self.log = {}
        self.

        self.log_start = 0
        self.last_free = 0
        self.latest_write = -1

        self.commit_lock = threading.Lock()
        self.last_free_lock = threading.Lock()
        self.latest_write_lock = threading.Lock()

    # do mutext check
    def get_next(self):
        with self.last_free_lock:
            while(self.last_free in self.log and self.log[self.last_free] != 1):
                self.last_free += 1
            self.log[self.last_free] = -1
            self.last_free += 1
            return self.last_free - 1


    def get_latest_write(self):
        return self.latest_write

    # use a mutex lock
    #
    def update_kv_store(self):
        
        if self.commit_lock.acquire(blocking=False):
            
            def apply_event(event):
                action, key, val = event
                if action == "put":
                    self.kv_store[key] = val
                elif action == "del":
                    del self.kv_store[key]

            while(self.log_start in self.log and self.log[self.log_start] != -1):
                apply_event(self.log[self.log_start])
                
                del self.log[self.log_start]
                
                self.log_start += 1
            self.commit_lock.release()

    def update_log(self, location, action, key, val = None):
        self.log[location] = (action, key, val)
        with self.latest_write_lock:
            if self.latest_write < location:
                self.latest_write = location

    # Need to test edges cases to see if this is even needed.
    # def release_hold(self, location):
    #     with self.last_free_lock

    def debug_vals(self):
        debug = ("KV_store: " + str(self.kv_store) + '\n' +  
                "log: " + str(self.log) + '\n' + 
                "log_start: " + str(self.log_start) + '\n' +
                "last_free: " + str(self.last_free) + '\n' +
                "latets_write: " + str(self.latest_write))
        return debug

if __name__ == "__main__":
    test = KV()
    nex = test.get_next()
    print(nex)
    lat = test.get_latest_write()
    print(lat)
    test.update_log(nex, "put", "key", "val")
    test.update_log(10, "put", "key2", "val2")
    nex = test.get_next()
    test.update_log(nex, "put", "key1", "val1")
    nex = test.get_next()
    test.update_log(nex, "del", "key1", "val1")

    print(test.debug_vals())
    test.update_kv_store()
    print(test.debug_vals())