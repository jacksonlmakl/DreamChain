from dreamchain import DreamChainNode

# Create and connect Node 1
node1 = DreamChainNode(5005).node

# Node 1 mines a block
node1.add_transaction('Jackson', 'Jackson', {'Data':'Something'})
node1.mine_block()
while True:
  pass
