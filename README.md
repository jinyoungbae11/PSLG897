# Ancient Indian Astronomical Models
Anjali Kantharuban, Rushil Kapadia, Nikhil Mandava, Alok Elashoff, and Jinyoung Bae

## Description

This project allows for the training and evaluation of the ancient Indian planetary models of Arybhata, Lata, and Somayaji. The respective models of each astronomer were built to reflect their modeling assumptions. These models take time, observational longitude, and observational latitude as inputs and produce the observed azimuth and altitude of any the 5 visible planets (Mars, Venus, Mercury, Saturn, Jupiter). 

Beyond these three astronomical models, we have also included a baseline model which is a simple 3 layer feedforward neural network. This baseline model is used as a comparison point for the results of the ancient Indian models.

## Requirements

We provide a requirements.txt. You can ensure you have all the necessary requirements to run the project by running:
```
pip install -r requirements.txt
```
In order to set the environment variables required to access the data and models, run the following command in the root directory of your repository:

```
$ export L189_ROOT=$(pwd)
```

## Generating Data
All data found in this repository was generated using the methods described in [Data Generation for Measured Planetary Positions in the Night Sky](https://github.com/AlokElashoff/PSEG897). All observations were generated using the crosstaff tool at 20.5937° N 78.9629° E each day at 18:30 UTC to represent the data collection process of the ancient Indian astronomers.

| Dataset | Train Time Period | Eval Time Period |
| --- | --- | --- |
| Arybhata | 450 - 550 CE | 550-575 CE |
| Lata | 700-800 CE | 800-825 CE |
| Somayaji | 1450-1500 CE | 1500-1525 CE |
| Common | 950-1050 CE | 1050-1075 CE |

## Training and Evaluating Models
To train and evaluate the models contained in this repository, run:
```
python3 train_ancient.py
```
With the following flags: 
```
-h, --help            Show this help message and exit
--data                The json file that contains your data
--model               Which model to run
--dout                Location where your model saves to
--writer              Location where your model plot writes to
--eval                Whether to run eval
--eval_store          Where to dump eval results
--saved_model         Location of model to load
--start_time          First year
--gpu                 Use gpu
--workers             Number of workers for each dataloader
--planets             Number of planets
--epoch               Number of epochs
--batch               Size of batches
--lr                  Optimizer learning rate
--latitude            Observational latitude on Earth
--longitude           Observational longitude on Earth
--alt                 Observational altitude on Earth
--seed                Random seed
```

## Navigating the Repository
The generated data that we used for our models is stored in the data folder. The data used to train the models are the files 'aryabhata.json', 'lata.json', 'somayaji.json', and 'common.json' where each of the first three files were used to train the respective astronomer's models and the last file was used as a common train set. The same file names but with '\_eval' at the end are the train sets used for each of the models.

The actual models are stored in the models folder under the astronomer's name and the baseline model is stored as 'baseline.py.' The 'planet_loader.py' file loads the data and parses it.

The file to train and evaluate all models is stored under the train folder in 'train_ancient.py'.
