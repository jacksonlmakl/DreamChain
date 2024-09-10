from dreamchain import DreamChainNode ,MasterNode, Node

if __name__ == '__main__':
    master_node = MasterNode()
    # Create a local node that connects to the master node at localhost:5000
    node = Node(5001, master_node)

    # Add a transaction and mine a block
    node.add_transaction('Jackson', 'Jackson', 'Some Data')
    node.mine_block()
    node.resolve_conflicts()
    while True:
        continue
    
