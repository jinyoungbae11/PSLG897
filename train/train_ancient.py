import os
import sys
import torch
import json
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from importlib import import_module

sys.path.append(os.path.join(os.environ['L189_ROOT']))
sys.path.append(os.path.join(os.environ['L189_ROOT'], 'models'))

if __name__ == '__main__':
    ### Set up parser ###
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)

    ### Add settings to parser ###
    parser.add_argument('--data', help='The folder that contains your data', default='data')
    parser.add_argument('--model', help='Which model to run', default='aryabhata')
    parser.add_argument('--dout', help='Location where your model saves to', default='exp/model:{model}')
    parser.add_argument('--writer', help='Location where your model plot writes to', default='runs/model:{model}')


    parser.add_argument('--gpu', help='Use gpu', action='store_true')
    parser.add_argument('--workers', help='Number of workers for each dataloader', default=8, type=int)
    parser.add_argument('--planet', help='Number of planets', default=5, type=int)
    parser.add_argument('--epoch', help='Number of epochs', default=20, type=int)
    parser.add_argument('--batch', help='Size of batches', default=512, type=int)
    parser.add_argument('--lr', help='optimizer learning rate', default=1e-4, type=float)
    parser.add_argument('--latitude', help='latitude', default=78.9629, type=float)
    parser.add_argument('--longtitude', help='longtitude', default=20.5937, type=float)
    parser.add_argument('--alt', help='alt', default=0, type=float)

    ### Retrieve arguments ###
    args = parser.parse_args()
    args.dout = args.dout.format(**vars(args))
    args.dout = args.writer.format(**vars(args))

    ### Make directory to store model ###
    if not os.path.isdir(args.dout):
        os.makedirs(args.dout)

    ### Import selected model ###
    M = import_module('models.{}'.format(args.model))
    data = {
        'train': os.path.join(args.data, 'aryabata.json'),
        'valid': os.path.join(args.data, 'aryabata_validation.json')
    }
    # data = {
    #     'train': os.path.join(args.data, 'train.json'),
    #     'valid': os.path.join(args.data, 'valid.json')
    # }

    ### Load and run selected model ###
    model = M.Module(args)
    model.run_train(data)
