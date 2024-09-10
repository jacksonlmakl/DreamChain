from dreamchain import MasterNode

if __name__ == '__main__':
    # Start the master node on port 5000
    master_node = MasterNode()

    # Keep the master node running indefinitely
    print("Master node is running on port 5000 and ready to accept connections...")

    # The node will continue to accept incoming connections via its server thread
    while True:
        pass
