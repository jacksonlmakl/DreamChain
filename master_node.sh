#!/bin/bash

# Step 1: Create a Python virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Step 2: Activate the virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Step 3: Install the requirements
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies from requirements.txt..."
    pip install -r requirements.txt
else
    echo "requirements.txt not found. Please provide one."
    exit 1
fi

# Step 4: Run the master_node.py script in the background with nohup
echo "Running master_node.py in the background..."
nohup python master_node.py &

# Step 5: Notify the user
echo "Master node is running in the background with nohup."
echo "Check nohup.out for logs."

