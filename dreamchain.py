import socket
import pickle
from threading import Thread
from time import time
import hashlib
import json
from uuid import uuid4

class DreamChain:
    def __init__(self, port):
        self.chain = []
        self.transactions = []
        self.nodes = set()
        self.node_identifier = str(uuid4()).replace('-', '')
        self.port = port

        # Create the genesis block
        self.new_block(previous_hash='1', proof=100)

    def new_block(self, proof, previous_hash=None):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        self.transactions = []
        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, data):
        self.transactions.append({
            'sender': sender,
            'recipient': recipient,
            'data': data,
        })
        return self.last_block['index'] + 1

    @staticmethod
    def hash(block):
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]

    def proof_of_work(self, last_proof):
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1
        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

    def valid_chain(self, chain):
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            if block['previous_hash'] != self.hash(last_block):
                return False
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False
            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):
        new_chain = None
        max_length = len(self.chain)

        for node in self.nodes:
            length, chain = self.get_chain_from_peer(node)
            if chain and length > max_length and self.valid_chain(chain):
                max_length = length
                new_chain = chain

        if new_chain:
            self.chain = new_chain
            return True
        return False

    def get_chain_from_peer(self, node):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(node)
            s.send(b"GET_CHAIN")
            response = s.recv(4096)
            s.close()
            length, chain = pickle.loads(response)
            return length, chain
        except Exception:
            return None, None

    def register_node(self, address):
        self.nodes.add(address)

    def broadcast_block(self, block):
        for node in self.nodes:
            self.send_block_to_peer(node, block)

    def send_block_to_peer(self, node, block):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(node)
            data = pickle.dumps(block)
            s.send(data)
            s.close()
        except Exception:
            pass

def handle_client(client_socket, blockchain):
    request = client_socket.recv(4096)

    if request == b"GET_CHAIN":
        response = pickle.dumps((len(blockchain.chain), blockchain.chain))
        client_socket.send(response)
    elif request == b"GET_NODES":
        # Return list of known nodes
        response = pickle.dumps(list(blockchain.nodes))
        client_socket.send(response)
    else:
        # Receive and add the block
        block = pickle.loads(request)
        blockchain.chain.append(block)
        print(f"Received block {block['index']} from peer and added to the chain.")

    client_socket.close()


def start_server(blockchain):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', blockchain.port))
    server.listen(5)

    while True:
        client, addr = server.accept()
        client_handler = Thread(target=handle_client, args=(client, blockchain))
        client_handler.start()

class Node:
    def __init__(self, port, master_node=None):
        self.blockchain = DreamChain(port)
        self.port = port
        self.master_node = master_node

        # Start the server to accept incoming requests for this node
        server_thread = Thread(target=start_server, args=(self.blockchain,))
        server_thread.start()

        if master_node:
            self.auto_register_with_master(master_node)

    def auto_register_with_master(self, master_node):
        """
        Connect to the master node, get a list of other nodes, and register with them.
        """
        # Step 1: Get list of nodes from master node
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(master_node)
            s.send(b"GET_NODES")
            response = s.recv(4096)
            s.close()
            nodes = pickle.loads(response)
            print(f"Received nodes from master: {nodes}")
        except Exception as e:
            print(f"Error connecting to master node: {e}")
            return

        # Step 2: Register with all nodes (including master)
        for node in nodes:
            if node != ('localhost', self.port):  # Skip self
                self.register_node(node)

        # Finally, register with master node itself
        self.register_node(master_node)

        # Step 3: Resolve conflicts and sync with the latest chain
        self.resolve_conflicts()

    def register_node(self, node_address):
        """
        Register a node in the network.
        """
        self.blockchain.register_node(node_address)
        print(f"Registered with node {node_address}")

    def add_transaction(self, sender, recipient, data):
        """
        Adds a transaction to the blockchain.
        """
        self.blockchain.new_transaction(sender, recipient, data)

    def mine_block(self):
        """
        Mines a block using proof of work and broadcasts the block to peers.
        """
        last_proof = self.blockchain.last_block['proof']
        proof = self.blockchain.proof_of_work(last_proof)
        block = self.blockchain.new_block(proof)
        
        # Broadcast the new block to all registered nodes
        print(f"Broadcasting block {block['index']} to peers...")
        self.blockchain.broadcast_block(block)
        print(f"Block {block['index']} mined and broadcasted.")


    def get_chain(self):
        """
        Fetches the blockchain.
        """
        return self.blockchain.chain

    def resolve_conflicts(self):
        """
        Resolves conflicts in the blockchain by applying the longest valid chain.
        """
        if self.blockchain.resolve_conflicts():
            print("Chain replaced with the longest one.")
        else:
            print("Our chain is authoritative.")

def DreamChainNode(port):
    node = Node(port, ('54.197.152.22', 5000))  # Connect to the master node
    node.resolve_conflicts()  # Ensure the local chain is updated with the master node's chain
    return node

def MasterNode():
    master_node = Node(5000)
    return master_node
    
if __name__ == '__main__':
    # Create a local node that connects to the master node at localhost:5000
    master_node = ('localhost', 5000)
    node = Node(5001, master_node)

    # Add a transaction and mine a block
    node.add_transaction('Alice', 'Bob', '100 coins')
    node.mine_block()

# import socket
# import pickle
# from threading import Thread
# from time import time
# import hashlib
# import json
# from uuid import uuid4

# class DreamChain:
#     def __init__(self, port):
#         self.chain = []
#         self.transactions = []
#         self.nodes = set()
#         self.node_identifier = str(uuid4()).replace('-', '')
#         self.port = port

#         # Create the genesis block
#         self.new_block(previous_hash='1', proof=100)

#     def new_block(self, proof, previous_hash=None):
#         block = {
#             'index': len(self.chain) + 1,
#             'timestamp': time(),
#             'transactions': self.transactions,
#             'proof': proof,
#             'previous_hash': previous_hash or self.hash(self.chain[-1]),
#         }

#         self.transactions = []
#         self.chain.append(block)
#         return block

#     def new_transaction(self, sender, recipient, data):
#         self.transactions.append({
#             'sender': sender,
#             'recipient': recipient,
#             'data': data,
#         })
#         return self.last_block['index'] + 1

#     @staticmethod
#     def hash(block):
#         block_string = json.dumps(block, sort_keys=True).encode()
#         return hashlib.sha256(block_string).hexdigest()

#     @property
#     def last_block(self):
#         return self.chain[-1]

#     def proof_of_work(self, last_proof):
#         proof = 0
#         while self.valid_proof(last_proof, proof) is False:
#             proof += 1
#         return proof

#     @staticmethod
#     def valid_proof(last_proof, proof):
#         guess = f'{last_proof}{proof}'.encode()
#         guess_hash = hashlib.sha256(guess).hexdigest()
#         return guess_hash[:4] == "0000"

#     def valid_chain(self, chain):
#         last_block = chain[0]
#         current_index = 1

#         while current_index < len(chain):
#             block = chain[current_index]
#             if block['previous_hash'] != self.hash(last_block):
#                 return False
#             if not self.valid_proof(last_block['proof'], block['proof']):
#                 return False
#             last_block = block
#             current_index += 1

#         return True

#     def resolve_conflicts(self):
#         new_chain = None
#         max_length = len(self.chain)

#         for node in self.nodes:
#             length, chain = self.get_chain_from_peer(node)
#             if chain and length > max_length and self.valid_chain(chain):
#                 max_length = length
#                 new_chain = chain

#         if new_chain:
#             self.chain = new_chain
#             return True
#         return False

#     def get_chain_from_peer(self, node):
#         try:
#             s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#             s.connect(node)
#             s.send(b"GET_CHAIN")
#             response = s.recv(4096)
#             s.close()
#             length, chain = pickle.loads(response)
#             return length, chain
#         except Exception:
#             return None, None

#     def register_node(self, address):
#         self.nodes.add(address)

#     def broadcast_block(self, block):
#         for node in self.nodes:
#             self.send_block_to_peer(node, block)

#     def send_block_to_peer(self, node, block):
#         try:
#             s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#             s.connect(node)
#             data = pickle.dumps(block)
#             s.send(data)
#             s.close()
#         except Exception:
#             pass

# def handle_client(client_socket, blockchain):
#     request = client_socket.recv(4096)

#     if request == b"GET_CHAIN":
#         response = pickle.dumps((len(blockchain.chain), blockchain.chain))
#         client_socket.send(response)
#     elif request == b"GET_NODES":
#         # Return list of known nodes
#         response = pickle.dumps(list(blockchain.nodes))
#         client_socket.send(response)
#     else:
#         # Receive and add the block
#         block = pickle.loads(request)
#         blockchain.chain.append(block)
#         print(f"Received block {block['index']} from peer and added to the chain.")

#     client_socket.close()


# def start_server(blockchain):
#     server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     server.bind(('0.0.0.0', blockchain.port))
#     server.listen(5)

#     while True:
#         client, addr = server.accept()
#         client_handler = Thread(target=handle_client, args=(client, blockchain))
#         client_handler.start()

# class Node:
#     def __init__(self, port, master_node=None):
#         self.blockchain = DreamChain(port)
#         self.port = port
#         self.master_node = master_node

#         # Start the server to accept incoming requests for this node
#         server_thread = Thread(target=start_server, args=(self.blockchain,))
#         server_thread.start()

#         if master_node:
#             self.auto_register_with_master(master_node)

#     def auto_register_with_master(self, master_node):
#         """
#         Connect to the master node, get a list of other nodes, and register with them.
#         """
#         # Step 1: Get list of nodes from master node
#         try:
#             s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#             s.connect(master_node)
#             s.send(b"GET_NODES")
#             response = s.recv(4096)
#             s.close()
#             nodes = pickle.loads(response)
#             print(f"Received nodes from master: {nodes}")
#         except Exception as e:
#             print(f"Error connecting to master node: {e}")
#             return

#         # Step 2: Register with all nodes (including master)
#         for node in nodes:
#             if node != ('localhost', self.port):  # Skip self
#                 self.register_node(node)

#         # Finally, register with master node itself
#         self.register_node(master_node)

#     def register_node(self, node_address):
#         """
#         Register a node in the network.
#         """
#         self.blockchain.register_node(node_address)
#         print(f"Registered with node {node_address}")

#     def add_transaction(self, sender, recipient, data):
#         """
#         Adds a transaction to the blockchain.
#         """
#         self.blockchain.new_transaction(sender, recipient, data)

#     def mine_block(self):
#         """
#         Mines a block using proof of work and broadcasts the block to peers.
#         """
#         last_proof = self.blockchain.last_block['proof']
#         proof = self.blockchain.proof_of_work(last_proof)
#         block = self.blockchain.new_block(proof)
        
#         # Broadcast the new block to all registered nodes
#         print(f"Broadcasting block {block['index']} to peers...")
#         self.blockchain.broadcast_block(block)
#         print(f"Block {block['index']} mined and broadcasted.")


#     def get_chain(self):
#         """
#         Fetches the blockchain.
#         """
#         return self.blockchain.chain

#     def resolve_conflicts(self):
#         """
#         Resolves conflicts in the blockchain by applying the longest valid chain.
#         """
#         if self.blockchain.resolve_conflicts():
#             print("Chain replaced with the longest one.")
#         else:
#             print("Our chain is authoritative.")

# def DreamChainNode(port):
#     return Node(port, ('54.197.152.22', 5000))
#     # return Node(port, ('localhost', 5000))

# def MasterNode():
#     master_node = Node(5000)
#     return master_node
    
# if __name__ == '__main__':
#     # Create a local node that connects to the master node at localhost:5000
#     master_node = ('localhost', 5000)
#     node = Node(5001, master_node)

#     # Add a transaction and mine a block
#     node.add_transaction('Alice', 'Bob', '100 coins')
#     node.mine_block()


# # import socket
# # import pickle
# # from threading import Thread
# # from time import time
# # import hashlib
# # import json
# # from uuid import uuid4

# # class DreamChain:
# #     def __init__(self, port):
# #         self.chain = []
# #         self.transactions = []
# #         self.nodes = set()
# #         self.node_identifier = str(uuid4()).replace('-', '')
# #         self.port = port

# #         # Create the genesis block
# #         self.new_block(previous_hash='1', proof=100)

# #     def new_block(self, proof, previous_hash=None):
# #         block = {
# #             'index': len(self.chain) + 1,
# #             'timestamp': time(),
# #             'transactions': self.transactions,
# #             'proof': proof,
# #             'previous_hash': previous_hash or self.hash(self.chain[-1]),
# #         }

# #         self.transactions = []
# #         self.chain.append(block)
# #         return block

# #     def new_transaction(self, sender, recipient, data):
# #         self.transactions.append({
# #             'sender': sender,
# #             'recipient': recipient,
# #             'data': data,
# #         })
# #         return self.last_block['index'] + 1

# #     @staticmethod
# #     def hash(block):
# #         block_string = json.dumps(block, sort_keys=True).encode()
# #         return hashlib.sha256(block_string).hexdigest()

# #     @property
# #     def last_block(self):
# #         return self.chain[-1]

# #     def proof_of_work(self, last_proof):
# #         proof = 0
# #         while self.valid_proof(last_proof, proof) is False:
# #             proof += 1
# #         return proof

# #     @staticmethod
# #     def valid_proof(last_proof, proof):
# #         guess = f'{last_proof}{proof}'.encode()
# #         guess_hash = hashlib.sha256(guess).hexdigest()
# #         return guess_hash[:4] == "0000"

# #     def valid_chain(self, chain):
# #         last_block = chain[0]
# #         current_index = 1

# #         while current_index < len(chain):
# #             block = chain[current_index]
# #             if block['previous_hash'] != self.hash(last_block):
# #                 return False
# #             if not self.valid_proof(last_block['proof'], block['proof']):
# #                 return False
# #             last_block = block
# #             current_index += 1

# #         return True

# #     def resolve_conflicts(self):
# #         new_chain = None
# #         max_length = len(self.chain)

# #         for node in self.nodes:
# #             length, chain = self.get_chain_from_peer(node)
# #             if chain and length > max_length and self.valid_chain(chain):
# #                 max_length = length
# #                 new_chain = chain

# #         if new_chain:
# #             self.chain = new_chain
# #             return True
# #         return False

# #     def get_chain_from_peer(self, node):
# #         try:
# #             s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# #             s.connect(node)
# #             s.send(b"GET_CHAIN")
# #             response = s.recv(4096)
# #             s.close()
# #             length, chain = pickle.loads(response)
# #             return length, chain
# #         except Exception:
# #             return None, None

# #     def register_node(self, address):
# #         self.nodes.add(address)

# #     def broadcast_block(self, block):
# #         for node in self.nodes:
# #             self.send_block_to_peer(node, block)

# #     def send_block_to_peer(self, node, block):
# #         try:
# #             s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# #             s.connect(node)
# #             data = pickle.dumps(block)
# #             s.send(data)
# #             s.close()
# #         except Exception:
# #             pass

# # def handle_client(client_socket, blockchain):
# #     request = client_socket.recv(4096)

# #     if request == b"GET_CHAIN":
# #         response = pickle.dumps((len(blockchain.chain), blockchain.chain))
# #         client_socket.send(response)
# #     elif request == b"GET_NODES":
# #         # Return list of known nodes
# #         response = pickle.dumps(list(blockchain.nodes))
# #         client_socket.send(response)
# #     else:
# #         block = pickle.loads(request)
# #         blockchain.chain.append(block)

# #     client_socket.close()

# # def start_server(blockchain):
# #     server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# #     server.bind(('0.0.0.0', blockchain.port))
# #     server.listen(5)

# #     while True:
# #         client, addr = server.accept()
# #         client_handler = Thread(target=handle_client, args=(client, blockchain))
# #         client_handler.start()

# # class Node:
# #     def __init__(self, port, master_node=None):
# #         self.blockchain = DreamChain(port)
# #         self.port = port
# #         self.master_node = master_node

# #         # Start the server to accept incoming requests for this node
# #         server_thread = Thread(target=start_server, args=(self.blockchain,))
# #         server_thread.start()

# #         if master_node:
# #             self.auto_register_with_master(master_node)

# #     def auto_register_with_master(self, master_node):
# #         """
# #         Connect to the master node, get a list of other nodes, and register with them.
# #         """
# #         # Step 1: Get list of nodes from master node
# #         try:
# #             s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# #             s.connect(master_node)
# #             s.send(b"GET_NODES")
# #             response = s.recv(4096)
# #             s.close()
# #             nodes = pickle.loads(response)
# #             print(f"Received nodes from master: {nodes}")
# #         except Exception as e:
# #             print(f"Error connecting to master node: {e}")
# #             return

# #         # Step 2: Register with all nodes (including master)
# #         for node in nodes:
# #             if node != ('localhost', self.port):  # Skip self
# #                 self.register_node(node)

# #         # Finally, register with master node itself
# #         self.register_node(master_node)

# #     def register_node(self, node_address):
# #         """
# #         Register a node in the network.
# #         """
# #         self.blockchain.register_node(node_address)
# #         print(f"Registered with node {node_address}")

# #     def add_transaction(self, sender, recipient, data):
# #         """
# #         Adds a transaction to the blockchain.
# #         """
# #         self.blockchain.new_transaction(sender, recipient, data)

# #     def mine_block(self):
# #         """
# #         Mines a block using proof of work and broadcasts the block to peers.
# #         """
# #         last_proof = self.blockchain.last_block['proof']
# #         proof = self.blockchain.proof_of_work(last_proof)
# #         block = self.blockchain.new_block(proof)
# #         self.blockchain.broadcast_block(block)
# #         print(f"Block {block['index']} mined.")

# #     def get_chain(self):
# #         """
# #         Fetches the blockchain.
# #         """
# #         return self.blockchain.chain

# #     def resolve_conflicts(self):
# #         """
# #         Resolves conflicts in the blockchain by applying the longest valid chain.
# #         """
# #         if self.blockchain.resolve_conflicts():
# #             print("Chain replaced with the longest one.")
# #         else:
# #             print("Our chain is authoritative.")

# # def DreamChainNode(port):
# #     return Node(port, ('54.197.152.22', port))
# #     # return Node(port, ('localhost', 5000))

# # def MasterNode():
# #     master_node = Node(5000)
# #     return master_node
    
# # if __name__ == '__main__':
# #     # Create a local node that connects to the master node at localhost:5000
# #     master_node = ('localhost', 5000)
# #     node = Node(5001, master_node)

# #     # Add a transaction and mine a block
# #     node.add_transaction('Alice', 'Bob', '100 coins')
# #     node.mine_block()
