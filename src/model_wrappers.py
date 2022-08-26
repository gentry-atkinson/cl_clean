#Author: Gentry Atkinson
#Organization: Texas State University
#Data: 23 Aug, 2022
#
#Make some nice models with a common interface

#import CL_HAR.models as models
import torch
import numpy as np
from torch import nn
from utils.ts_feature_toolkit import get_features_for_set

EMBEDDING_WIDTH = 64

class Engineered_Features():
    def __init__(self, X) -> None:
        pass
    def fit(self, X, y=None) -> None:
        pass
    def get_features(self, X) -> np.ndarray:
        return get_features_for_set(X)


#https://www.kaggle.com/code/ljlbarbosa/convolution-autoencoder-pytorch/notebook
class Conv_Autoencoder(nn.Module):
    def __init__(self, X) -> None:
        super(Conv_Autoencoder, self).__init__()
        self.conv1 = nn.Conv1d(in_channels=X[0].shape[1],out_channels=2*EMBEDDING_WIDTH, kernel_size=8, padding_mode='zeros')
        self.conv2 = nn.LazyConv1d(out_channels=EMBEDDING_WIDTH, kernel_size=8, padding_mode='zeros')
        self.pool = nn.MaxPool1d(kernel_size=X[0].shape[1])
        self.embedding = nn.LazyLinear(out_features=EMBEDDING_WIDTH)