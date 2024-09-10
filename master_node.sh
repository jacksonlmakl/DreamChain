#!/bin/bash

# Step 1: Update and upgrade the system packages
echo "Updating and upgrading system packages..."
sudo apt update && sudo apt upgrade -y

# Step 2: Install Python 3 and venv (if not already installed)
echo "Installing Python 3 and venv..."
sudo apt install -y python3 python3-venv python3-pip

# Step 3: Create a Python virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Step 4: Activate the virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Step 5: Install the requirements from requirements.txt
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies from requirements.txt..."
    pip install -r requirements.txt
else
    echo "requirements.txt not found. Please provide one."
    exit 1
fi

# Step 6: Run the master_node.py script in the background with nohup
echo "Running master_node.py in the background..."
nohup python master_node.py &

# Step 7: Notify the user
echo "Master node is running in the background with nohup."
echo "Check nohup.out for logs."

