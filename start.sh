#!/bin/bash
nohup python3 master_node.py > master_node.log 2>&1 &
nohup python3 first_node.py > first_node.log 2>&1 &

