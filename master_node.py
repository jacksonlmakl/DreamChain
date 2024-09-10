from dreamchain import DreamChainNode ,MasterNode, Node

if __name__ == '__main__':
    node = MasterNode()
    # Create a local node that connects to the master node at localhost:5000
    # Add a transaction and mine a block
    node.add_transaction('Jackson', 'Jackson', 'Some Data')
    node.mine_block()
    node.resolve_conflicts()
