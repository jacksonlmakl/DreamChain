#!/bin/bash
nohup python3 master_node.py & > master_node.log 2>&1 &
nohup python3 first_node.py & > first_node.log 2>&1 &

echo "master_node.py is now running in the background. See master_node.log for logs"
echo "first_node.py is now running in the background. See first_node.log for logs"
