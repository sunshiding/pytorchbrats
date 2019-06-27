"""
To be used when training a model from scratch.
"""
# import warnings
# warnings.filterwarnings("ignore", category=UserWarning)
from thedataset import bratsDataset
from themodel import SmallU3D
import os
import tqdm
import torch
from torch.utils.data import DataLoader, random_split
import tqdm
import numpy as np
from thescore import iouscore

# parser
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('-d', '--dataPath', type=str, default='data')
parser.add_argument('-ne', '--numEpochs', type=int, default=3)
parser.add_argument('-bs', '--batchSize', type=int, default=16)
parser.add_argument('-t', '--threshold', type=float, default=0.5, help='Threshold for the Sigmoid')
parser.add_argument('--cuda', type=bool, default=False)
parser.add_argument('--pathsize', type=str, default='32', help='Which resolution to use.')
# add learning rate
# add valid split
args = parser.parse_args()
dataPath = args.dataPath
#NUM_WORKERS = args.numWorkers
NUM_EPOCHS = args.numEpochs
BATCH_SIZE = args.batchSize
SPLIT_FRAC = 0.25
LEARNING_RATE = 1e-4
THRESHOLD = args.threshold
PATH_SIZE = args.pathsize

print('dataPath =', dataPath)
#print('NumWorkrs =', NUM_WORKERS)
print(f'NumEpochs = {NUM_EPOCHS}')
print(f'BatchSize = {BATCH_SIZE}')
print(f'SPLIT_FRAC = {SPLIT_FRAC}')


# to be set by the parser
VERBOSE = True



# Get data
# dataPath = 'data'
#dataPath = os.path.join('ignore', 'playData')
fullDataset = bratsDataset(dataPath,PATH_SIZE)
print(f"There are {len(fullDataset)} images in total.")

valid_size = int(SPLIT_FRAC * len(fullDataset))
train_size = len(fullDataset) - valid_size
train_dataset, valid_dataset = random_split(fullDataset, [train_size, valid_size])
print(f"There are {len(train_dataset)} training images, and {len(valid_dataset)} validation images.")

# Load data
train_dataloader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=False)#, num_workers=NUM_WORKERS)
valid_dataloader = DataLoader(valid_dataset)#, num_workers=NUM_WORKERS)

# Use model from themodel.py
device = 'cpu'
if args.cuda and torch.cuda.is_available():
    device = 'cuda'

torchDevice = torch.device(device)
model = SmallU3D().to(torchDevice)
optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
criterion = torch.nn.BCEWithLogitsLoss()


# Here starts the training
print("All right, I am starting the training.")
for epoch in range(NUM_EPOCHS):
    print(f'This is epoch number {epoch}.')
    epochMeanLosses = []
    epochMeanScores = []

    # training loop----
    model.train()
    losses = []
    batchloop = tqdm.tqdm(train_dataloader)
    for x,y in batchloop:
        # use cuda if available
        x = x.to(torchDevice)
        y = y.to(torchDevice)
        # Forward pass
        y_pred = model(x)
        # Compute loss
        loss = criterion(y_pred,y)
        # Kill gradients
        optimizer.zero_grad()
        # Backward pass
        loss.backward()
        # update gradients
        optimizer.step()

        batchloop.set_description(f"Epoch number {epoch}, Loss: {loss.item()}")
        losses.append(loss.item())
    print(f"I trained on {len(losses)} images. The average loss was {np.asarray(losses).mean()}.")

    # validation loop----
    losses = []
    model.eval()
    with torch.no_grad():
        validloop = tqdm.tqdm(valid_dataloader)
        scores = []
        for x,y in validloop:
            x = x.to(torchDevice)
            y = y.to(torchDevice)
            y_pred = model(x)
            loss = criterion(y_pred,y)
            losses.append(loss.item())
            validloop.set_description('Loss: {}'.format(loss.item()))

            score = iouscore(y_pred,y)
            scores.append(score)

    print(f"I evaluated the model on {len(scores)} images")
    epochMeanLoss = np.asarray(losses).mean()
    epochMeanLosses.append(epochMeanLoss)
    print(f"The avg validation loss is {epochMeanLoss}")
    epochMeanScore = np.asarray(scores).mean()
    epochMeanScores.append(epochMeanScore)
    print(f"The avg IoU score is: {epochMeanScore}")

print('\nWhile validating, these were the mean losses:\n')
print(epochMeanLosses)
print('\nWhile validating, these were the mean scores:\n')
print(epochMeanScores)
print("\nI am saving the current model now.")
torch.save(model.state_dict(), 'model.pt')

import matplotlib.pyplot as plt
plt.plot(epochMeanLosses, 'g^')
plt.plot(epochMeanScores, 'bs')
plt.show()

# To reload it: 
# model = myModel()
# model.load_state_dict(torch.load(PATH))
# model.eval()