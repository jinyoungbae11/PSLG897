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
    parser.add_argument('--data', help='The json file that contains your data', default='{model}')
    parser.add_argument('--model', help='Which model to run', default='aryabhata')
    parser.add_argument('--dout', help='Location where your model saves to', default='exp/{model}/{model}_d{data}_s{seed}.pth')
    parser.add_argument('--writer', help='Location where your model plot writes to', default='runs/{model}/{model}_d{data}_s{seed}')
    parser.add_argument('--eval', help='Whether to run eval', action='store_true')
    parser.add_argument('--saved_model', help='Location of model to load', default=None)
    parser.add_argument('--eval_store', help='Where to dump eval results', default='results.json')

    parser.add_argument('--start_time', help='First year', default="0000_01_01_00:00")


    parser.add_argument('--gpu', help='Use gpu', action='store_true')
    parser.add_argument('--workers', help='Number of workers for each dataloader', default=8, type=int)
    parser.add_argument('--planet', help='Number of planets', default=5, type=int)
    parser.add_argument('--epoch', help='Number of epochs', default=40, type=int)
    parser.add_argument('--batch', help='Size of batches', default=512, type=int)
    parser.add_argument('--lr', help='optimizer learning rate', default=1e-5, type=float)
    parser.add_argument('--latitude', help='latitude', default=78.9629, type=float)
    parser.add_argument('--longtitude', help='longtitude', default=20.5937, type=float)
    parser.add_argument('--alt', help='alt', default=0, type=float)
    parser.add_argument('--seed', help='random seed', default=123, type=int)

    ### Retrieve arguments ###
    args = parser.parse_args()
    args.data = args.data.format(**vars(args))
    args.dout = args.dout.format(**vars(args))
    args.writer = args.writer.format(**vars(args))
    args.eval_name = "{model}_d{data}_s{seed}".format(**vars(args))


    ### Make directory to store model ###
    if not os.path.isdir("exp/{model}".format(**vars(args))):
        os.makedirs("exp/{model}".format(**vars(args)))

    # add manual seed
    torch.manual_seed(args.seed)

    ### Import selected model ###
    M = import_module('models.{}'.format(args.model))

    data = os.path.join("data/" + args.data + ".json")

    ### Load and run selected model ###
    if args.eval:
        saved_model = torch.load(args.saved_model)
        model = M.Module(args, saved_model)

        loss = model.evaluate(data)
        print("Final evaluation loss: " + str(loss))
        with open(args.eval_store, 'r') as eval_store_file:
            results = json.load(eval_store_file)
        results[args.eval_name] = loss
        with open(args.eval_store, 'w') as eval_store_file:
            json.dump(results, eval_store_file, indent=4)

    else:
        model = M.Module(args)
        model.run_train(data)
