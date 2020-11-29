import os
import sys
import random
import json
import tqdm
import torch
import pyproj
import numpy as np
from torch import nn
from torch.nn import functional as F
from torch.utils.data import DataLoader
from tensorboardX import SummaryWriter
from planet_loader import PlanetDataset, collate_fn



class Module(nn.Module):
    def __init__(self, args, saved_model=None):
        super().__init__()
        self.args = args
        self.device = torch.device('cuda') if self.args.gpu else torch.device('cpu')

        if saved_model:
            self.args = saved_model['args']

        ### Layers Here ###
        self.linear_1 = nn.Linear(args.planet, 8)
        self.linear_2 = nn.Linear(8, 16)
        self.linear_3 = nn.Linear(16, args.planet * 3)

        if saved_model:
            self.load_state_dict(saved_model['model'], strict=False)

        ### End Layers ###

        self.to(self.device)

    def forward(self, t):
        ### Models Here ###
        args = self.args
        B = t.shape[0]
        t = t.repeat(1, args.planet).reshape(B, args.planet)
        positions = self.linear_1(t)
        positions = F.relu(positions)
        positions = self.linear_2(positions)
        positions = F.relu(positions)
        positions = self.linear_3(positions)
        positions = positions.reshape(B, args.planet, 3)
        alt, az = self.convert_coordinates(positions[:,:,0],positions[:,:,1],positions[:,:,2])

        positions = torch.stack([az, alt], dim=-1)
        return positions
        ### End Model ###

    def convert_coordinates(self, x, y, z):

        view_x, view_y, view_z = self.gps_to_ecef_custom(self.args.latitude, self.args.longtitude, 6378.1370)
        planet_lla = self.ecef2lla(x - view_x, y - view_y, z - view_z)

        return planet_lla[:,:,1], planet_lla[:,:,0]


    def gps_to_ecef_custom(self, lat, lon, alt):

        equatorial_radius = 6378.1370
        polar_radius = 6356.7523

        rad_lat = torch.tensor(lat) * np.pi / 180
        rad_lon = torch.tensor(lon) * np.pi / 180

        e2 = torch.tensor(1 - (polar_radius ** 2) / (equatorial_radius ** 2), dtype=torch.float)
        sin_phi = torch.sin(rad_lat)
        N_phi = torch.div(equatorial_radius, (1 - e2 * torch.pow(sin_phi, 2)))

        x_view = (N_phi + alt) * torch.cos(rad_lat) * torch.cos(rad_lon)
        y_view = (N_phi + alt) * torch.cos(rad_lat) * torch.sin(rad_lon)
        z_view = (N_phi * (1 - e2) + alt) * torch.cos(rad_lat) * torch.cos(rad_lon)

        return x_view, y_view, z_view



    def ecef2lla(self, x, y, z) :
        B = x.shape[0]
        a = torch.tensor(6378137, dtype=torch.float).to(self.device)
        f = torch.tensor(0.0034, dtype=torch.float).to(self.device)
        b = torch.tensor(6.3568e6, dtype=torch.float).to(self.device)
        e = torch.sqrt(torch.div(torch.pow(a, 2) - torch.pow(b, 2) , torch.pow(a, 2)))
        e2 = torch.sqrt(torch.div(torch.pow(a, 2) - torch.pow(b, 2) , torch.pow(b, 2)))

        lla = torch.zeros(B, self.args.planet, 3).to(self.device)

        p = torch.sqrt(torch.pow(x, 2) + torch.pow(y, 2))

        theta = torch.arctan(torch.div((z * a), (p * b)))

        lon = torch.arctan(torch.div(y, x))

        first = z + torch.pow(e2, 2) * b * torch.pow(torch.sin(theta), 3)
        second = p - torch.pow(e, 2) * a * torch.pow(torch.cos(theta), 3)
        lat = torch.arctan(torch.div(first, second))
        N = torch.div(a, (torch.sqrt(1 - (torch.pow(e, 2) * torch.pow(torch.sin(lat), 2)))))

        m = torch.div(p, torch.cos(lat))
        height = m - N

        lon = torch.div(lon * 180, torch.tensor(np.pi)).to(self.device)
        lat = torch.div(lat * 180, torch.tensor(np.pi)).to(self.device)
        lla[:, :, 0] = lat
        lla[:, :, 1] = lon
        lla[:, :, 2] = height

        return lla

    def run_train(self, data):
        ### Setup ###
        args = self.args
        self.writer = SummaryWriter(args.writer) ## Our summary writer, which plots loss over time
        self.fsave = os.path.join(args.dout) ## The path to the best version of our model

        with open(data, 'r') as file:
            dataset = json.load(file)
        dataset = PlanetDataset(dataset, self.args)
        train_size = int(len(dataset) * 0.8)
        valid_size = len(dataset) - train_size
        train_dataset, valid_dataset = torch.utils.data.random_split(dataset, [train_size, valid_size])

        train_dataloader = DataLoader(train_dataset, batch_size=args.batch, shuffle=True, num_workers=args.workers, collate_fn=collate_fn)
        valid_dataloader = DataLoader(valid_dataset, batch_size=args.batch, shuffle=True, num_workers=args.workers, collate_fn=collate_fn)

        optimizer = torch.optim.Adam(list(self.parameters()), lr=args.lr)

        best_loss = 1e10 ## This will hold the best validation loss so we don't overfit to training data

        ### Training Loop ###
        batch_idx = 0
        for epoch in range(args.epoch):
            print('Epoch', epoch)
            train_description = "Epoch " + str(epoch) + ", train"
            valid_description = "Epoch " + str(epoch) + ", valid"

            train_loss = torch.tensor(0, dtype=torch.float)
            train_size = torch.tensor(0, dtype=torch.float)

            self.train()

            for batch in tqdm.tqdm(train_dataloader, desc=train_description):
                batch_idx+=1
                optimizer.zero_grad() ## You don't want to accidentally have leftover gradients

                ### Compute loss and update variables ###
                loss = self.compute_loss(batch)

                train_size += batch['time'].shape[0] ## Used to normalize loss when plotting
                train_loss += loss

                self.writer.add_scalar("Loss/BatchTrain", (loss/batch['time'].shape[0]).item(), batch_idx)

                ### Backpropogate ###
                loss.backward()
                optimizer.step()
                torch.cuda.empty_cache()

            ### Run validation loop ###
            valid_loss, valid_size = self.run_eval(valid_dataloader, valid_description)

            ### Write to SummaryWriter ###
            self.writer.add_scalar("Loss/Train", (train_loss/train_size).item(), epoch)
            self.writer.add_scalar("Loss/Valid", (valid_loss/valid_size).item(), epoch)
            self.writer.flush()

            ### Save model if it is better that the previous ###

            if valid_loss < best_loss:
                print( "Obtained a new best validation loss of {:.2f}, saving model checkpoint to {}...".format((valid_loss/valid_size).item(), self.fsave))
                torch.save({
                    'model': self.state_dict(),
                    'optim': optimizer.state_dict(),
                    'args': self.args
                }, self.fsave)
                best_loss = valid_loss

        self.writer.close()

    def run_eval(self, valid_dataloader, valid_description):
        self.eval()
        loss = torch.tensor(0, dtype=torch.float)
        size = torch.tensor(0, dtype=torch.float)

        with torch.no_grad():
            for batch in tqdm.tqdm(valid_dataloader, desc=valid_description):
                size += batch['time'].shape[0] ## Used to normalize loss when plotting
                loss += self.compute_loss(batch)

        return loss, size

    def evaluate(self, data):
        self.eval()
        args = self.args
        with open(data, 'r') as file:
            dataset = json.load(file)
        dataset = PlanetDataset(dataset, self.args)
        dataloader = DataLoader(dataset, batch_size=args.batch, shuffle=True, num_workers=args.workers, collate_fn=collate_fn)
        description = "Evaluating..."

        loss = [torch.tensor(0, dtype=torch.float) for i in range(self.args.planet)]
        size = torch.tensor(0, dtype=torch.float)

        with torch.no_grad():
            for batch in tqdm.tqdm(dataloader, desc=description):
                batch_size = batch['time'].shape[0]

                ### Move data to GPU if available ###
                times = batch['time'].to(self.device)
                # planet_times = batch['planet_times'].to(self.device)

                true_position = batch['pos'].to(self.device)

                ### Run forward ###
                pred_position = self.forward(times)

                true = []
                pred = []
                true_az_sin = torch.sin(torch.deg2rad(true_position[:, :, 0]))
                true_az_cos = torch.cos(torch.deg2rad(true_position[:, :, 0]))
                true_alt_sin = torch.sin(torch.deg2rad(true_position[:, :, 1]))
                true_alt_cos = torch.cos(torch.deg2rad(true_position[:, :, 1]))

                pred_az_sin = torch.sin(torch.deg2rad(pred_position[:, :, 0]))
                pred_az_cos = torch.cos(torch.deg2rad(pred_position[:, :, 0]))
                pred_alt_sin = torch.sin(torch.deg2rad(pred_position[:, :, 1]))
                pred_alt_cos = torch.cos(torch.deg2rad(pred_position[:, :, 1]))

                true_positions = torch.stack([true_az_sin, true_az_cos, true_alt_sin, true_alt_cos], dim=2)
                pred_positions = torch.stack([pred_az_sin, pred_az_cos, pred_alt_sin, pred_alt_cos], dim=2)
                pred_positions_by_planet = [pred_positions[:, i].reshape(batch_size, -1)  for i in range(args.planet)]
                true_positions_by_planet = [true_positions[:, i].reshape(batch_size, -1)  for i in range(args.planet)]


                loss_by_planet = [F.mse_loss(pred_positions_by_planet[i], true_positions_by_planet[i], reduction='sum') for i in range(self.args.planet)]
                size += batch['time'].shape[0] ## Used to normalize loss when plotting
                loss = [loss_by_planet[i] + loss[i] for i in range(self.args.planet)]

        return [(loss[i] / size).item() for i in range(self.args.planet)]


    def compute_loss(self, batch):
        batch_size = batch['time'].shape[0]

        ### Move data to GPU if available ###
        times = batch['time'].to(self.device)
        # planet_times = batch['planet_times'].to(self.device)
        true_position = batch['pos'].to(self.device)
        ### Run forward ###
        pred_position = self.forward(times)

        # B x planets x 2

        # B x planets x 4 -> sin(alt), cos(alt), sin(az), cos(az)
        true = []
        pred = []
        true_az_sin = torch.sin(torch.deg2rad(true_position[:, :, 0]))
        true_az_cos = torch.cos(torch.deg2rad(true_position[:, :, 0]))
        true_alt_sin = torch.sin(torch.deg2rad(true_position[:, :, 1]))
        true_alt_cos = torch.cos(torch.deg2rad(true_position[:, :, 1]))

        pred_az_sin = torch.sin(torch.deg2rad(pred_position[:, :, 0]))
        pred_az_cos = torch.cos(torch.deg2rad(pred_position[:, :, 0]))
        pred_alt_sin = torch.sin(torch.deg2rad(pred_position[:, :, 1]))
        pred_alt_cos = torch.cos(torch.deg2rad(pred_position[:, :, 1]))

        true_positions = torch.stack([true_az_sin, true_az_cos, true_alt_sin, true_alt_cos], dim=2)
        pred_positions = torch.stack([pred_az_sin, pred_az_cos, pred_alt_sin, pred_alt_cos], dim=2)

        ### Compute loss on results ###
        loss = F.mse_loss(pred_positions, true_positions, reduction='sum')
        return loss
