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
        """
        Resolves conflicts by applying the longest valid chain in the network.
        Fetches the chain from all peers and applies the longest one if valid.
        """
        new_chain = None
        max_length = len(self.chain)

        for node in self.nodes:
            length, chain = self.get_chain_from_peer(node)
            if chain and length > max_length and self.valid_chain(chain):
                max_length = length
                new_chain = chain

        # If we discovered a new, valid chain longer than our current one, replace it
        if new_chain:
            self.chain = new_chain
            print("Chain replaced with the longest one from peer.")
            return True
        return False

    def get_chain_from_peer(self, node):
        """
        Retrieve the blockchain from a peer node, fetching the data in chunks.
        """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(node)
            s.send(b"GET_CHAIN")

            # Use a loop to fetch the entire chain
            data = b""
            while True:
                part = s.recv(4096)
                if not part:
                    break
                data += part
            
            s.close()

            length, chain = pickle.loads(data)
            return length, chain
        except Exception as e:
            print(f"Error fetching chain from peer {node}: {e}")
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
        except Exception as e:
            print(f"Error sending block to peer {node}: {e}")


def handle_client(client_socket, blockchain):
    request = client_socket.recv(4096)

    if request == b"GET_CHAIN":
        # Return the current length and chain to the requesting peer
        response = pickle.dumps((len(blockchain.chain), blockchain.chain))
        client_socket.send(response)
    elif request == b"GET_NODES":
        # Return the list of known nodes
        response = pickle.dumps(list(blockchain.nodes))
        client_socket.send(response)
    else:
        # Assume it's a new node sending its address or a block
        try:
            data = pickle.loads(request)
            if isinstance(data, tuple) and len(data) == 2:
                # New node registering itself (expecting an address tuple like ('ip', port))
                print(f"Received new node: {data}")
                blockchain.register_node(data)
            else:
                # Assume it's a block being sent
                blockchain.chain.append(data)
                print(f"Received block {data['index']} from peer and added to the chain.")
        except Exception as e:
            print(f"Error handling request: {e}")

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

        # Register this node with the master
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(master_node)
            # Send this node's address to the master node for registration
            s.send(pickle.dumps(('localhost', self.port)))  # Replace 'localhost' with public IP if needed
            s.close()
        except Exception as e:
            print(f"Error registering with master node: {e}")
            return

        # Register with all nodes (including master)
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
        print(f"Current registered nodes: {self.blockchain.nodes}")

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

        # Resolve conflicts to ensure the node's chain is up-to-date after mining
        self.resolve_conflicts()

    def get_chain(self):
        """
        Fetches the blockchain and ensures conflicts are resolved by syncing with peers.
        """
        print("Resolving conflicts to sync with the latest chain from peers...")
        self.resolve_conflicts()
    
        # Now return the local chain, which should be the latest after conflict resolution
        return self.blockchain.chain

    def resolve_conflicts(self):
        """
        Resolves conflicts by applying the longest valid chain in the network.
        Fetches the chain from all peers and applies the longest one if valid.
        """
        if self.blockchain.resolve_conflicts():
            print("Chain replaced with the longest one.")
        else:
            print("Our chain is authoritative.")

class DreamChainNode:
    def __init__(self,port):
        # Create a new node and connect to the master node at 54.197.152.22:5000
        node = Node(port, ('54.197.152.22', 5000))
    
        # Fetch the latest chain from the master node and ensure the local chain is up-to-date
        print("Resolving conflicts to sync with the master node's chain...")
        node.resolve_conflicts()
    
        self.node = node
