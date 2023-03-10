import Pyro4
import threading
import time

@Pyro4.expose
class JustHungryBackendServer(object):
    def __init__(self, server_id, is_active=True, daemon=None):
        self.server_id = server_id
        self.is_active = is_active
        self.daemon = daemon
        self.shutdown_flag = False
        self.order_history = []

    def process_order(self, order_details):
        if not self.is_active:
            return "Sorry, this server is not active."

        # Process the order here and return the response
        response = "Your order of " + order_details + " has been received."
        self.order_history.append(order_details)
        return response
    
    def get_order_history(self):
        return self.order_history
    
    def activate(self):
        self.is_active = True
        return "Server activated."
    
    def deactivate(self):
        self.is_active = False
        return "Server deactivated."
    
    def is_alive(self):
        return True

    @Pyro4.oneway # in case call returns much later than daemon shutdown
    def Shutdown(self):
        print("Shutting down the backend server {self.server_id}")
        self.shutdown_flag = True

# Locate the Pyro name server
ns = Pyro4.locateNS()
print("Name server URI:", str(ns))

# We will pre-emptively remove all the registered objects from the name server
# Get a list of all the registered Pyro4 objects
all_objects = ns.list()

# Remove each registered object from the name server
for obj in all_objects:
    ns.remove(obj)

# Create and register multiple backend server objects with the name server
num_servers = 3
server_objects = []
for i in range(num_servers):
    daemon = Pyro4.Daemon()
    server = JustHungryBackendServer(i, False, daemon)
    uri = daemon.register(server, objectId="JustHungryBackendServer" + str(i))
    ns.register("JustHungryBackendServer" + str(i), uri)
    server_objects.append(server)
    print("Backend server " + str(server.server_id) + " URI:", uri)

# Activate the first backend server
server_objects[0].activate()
print("Server " + str(server_objects[0].server_id) + " activated.")

# Start the event loop for each backend server
for server in server_objects:
    daemon_thread = threading.Thread(target=server.daemon.requestLoop)
    daemon_thread.start()

# Monitor the servers and activate a standby server if the active server fails
while True and not server_objects[0].shutdown_flag:
    time.sleep(5)
    active_server = None
    for server in server_objects:
        if server.is_active and server.is_alive():
            active_server = server
            break
    
    if not active_server:
        print("Active server failed. Activating a standby server.")
        serverActivated = False
        for i in range(num_servers):
            try:
                server_objects[i].activate()
                print("Server " + str(i) + " activated.")
                serverActivated = True
                break
            except:
                print("Server " + str(i) + " failed to activate.")
                continue
        
        # If no server could be activated, then shutdown the system
        if not serverActivated:
            print("No server could be activated. Shutting down the system.")
            for server in server_objects:
                server.Shutdown()
            break

# Unregister the backend server objects from the name server
for i in range(num_servers):
    ns.remove("JustHungryBackendServer" + str(i))

# Close the Pyro Daemon for each backend server object
for server in server_objects:
    server.daemon.close()

