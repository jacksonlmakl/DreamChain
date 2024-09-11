import socket
import pickle
from threading import Thread
from .dreamchain import DreamChainNode, DreamChain # Assuming DreamChain and start_server are in dreamchain.py

class MasterNode:
    def __init__(self, port=5000):
        self.blockchain = DreamChain(port)
        self.port = port

        # Start the server to accept incoming requests
        server_thread = Thread(target=start_server, args=(self.blockchain,))
        server_thread.start()

        print(f"Master node is running on port {self.port}")

if __name__ == '__main__':
    # Create and run the master node on port 5000
    master_node = MasterNode(5000)

    # The server thread will keep the program running, no need for manual looping.
