#!/bin/bash

sudo apt-get -y install gcc build-essential

DEFAULT_CONDA_DIR="/home/ubuntu/anaconda"
if [ ! -d "$DEFAULT_CONDA_DIR" ]; then
    wget -O inst_conda.sh "https://repo.anaconda.com/archive/Anaconda3-2020.11-Linux-x86_64.sh" \
    && /bin/bash inst_conda.sh -b \
    && rm inst_conda.sh \
    && ./anaconda3/bin/conda init \
    && source ~/.bashrc
fi

conda create --name icarus-conda
conda activate icarus-conda

# Fix for low ram conda installation
# https://stackoverflow.com/questions/64821441/collecting-package-metadata-repodata-json-killed
sudo fallocate -l 1G /swapfile 
sudo chmod 600 /swapfile 
sudo mkswap /swapfile 
sudo swapon /swapfile 
sudo cp /etc/fstab /etc/fstab.bak 
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Install TA-lib
conda install -c conda-forge ta-lib

# Install python packages
pip install -r requirements.txt


