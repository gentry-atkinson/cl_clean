#Author: Gentry Atkinson
#Organization: Texas State University
#Data: 18 Aug, 2022
#
#Testing CL for Label Cleaning

#Experimental Design:
#   -add Noise at Random to one dataset
#   -extract features using 7 feature extractors: traditional, autoencoder, simclr+CNN, simclr+T, nnclr+CNN, nnclr+T
#   -predict a label using KNN for all instances of test data
#   -Compute:
#       P(mispredict | correct label)
#       P(mispredict | incorrect label)
#       P(predicted label == correct label)

#Hypothesis:
#   Null: contrastive learning will be no more likely to identify the correct label of data than AE or traditional
#   Alternative: labels predicted using CL will be more likely to match the true class


import os
from torch import Tensor
import numpy as np
from utils.add_nar import add_nar_from_array
from model_wrappers import Engineered_Features, Conv_AE, SimCLR_C, SimCLR_T, NNCLR_C, NNCLR_T, Supervised_C
from model_wrappers import SimCLR_R, NNCLR_R
from cleaner import compute_apparent_clusterability
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score

K = 5
WRITE_FEATURES = True
WRITE_LABELS = True

feature_learners = {
    "traditional" : Engineered_Features,
    #"CAE" : Conv_Autoencoder,
    "SimCLR + CNN" : SimCLR_C,
    "SimCLR + T" : SimCLR_T,
    "SimCLR + LSTM" : SimCLR_R,
    "NNCLR + CNN" : NNCLR_C,
    "NNCLR + T" : NNCLR_T,
    "NNCLR + LSTM" : NNCLR_R,
    "Supervised Convolutional" : Supervised_C
}

def exp_1(
        X_train : np.ndarray,
        y_train : np.ndarray,
        X_val : np.ndarray,
        y_val : np.ndarray,
        X_test : np.ndarray,
        y_test : np.ndarray,
        set: str
    ) -> dict:
    """
    Run the experiment described on one train/test set.
    Return a dict with 7 rows of results
    """

    results = {
        'set' : [],
        'features' : [],
        'noise percent' : [],
        'accuracy' : [],
        'number mislabeled' : [],
        'P(mispred)' : [],
        'P(mispred|correct)' : [],
        'P(mispred|incorrect)' : [],
        'P(pred label = class)' : [],
        'train clusterability' : [],
        'test clusterability' : []
    }

    print ("Running Experiment 1 with K=", K, " on ", set)
    print("Feature Extractors: ", ', '.join(feature_learners.keys()))

    #Let's make some noise
    num_classes = np.max(y_train)+1
    y_train_low, _, y_train_high, _ = add_nar_from_array(y_train, num_classes)
    y_val_low, _, y_val_high, _ = add_nar_from_array(y_val, num_classes)
    y_test_low, _, y_test_high, _ = add_nar_from_array(y_test, num_classes)

    if WRITE_LABELS:
        with open(f'temp/{set}_train_labels_low_noise.npy', 'wb+') as f:
            np.save(f, y_train_low)
        with open(f'temp/{set}_train_labels_high_noise.npy', 'wb+') as f:
            np.save(f, y_train_high)
        with open(f'temp/{set}_val_labels_low_noise.npy', 'wb+') as f:
            np.save(f, y_val_low)
        with open(f'temp/{set}_val_labels_high_noise.npy', 'wb+') as f:
            np.save(f, y_val_high)
        with open(f'temp/{set}_test_labels_low_noise.npy', 'wb+') as f:
            np.save(f, y_test_low)
        with open(f'temp/{set}_test_labels_high_noise.npy', 'wb+') as f:
            np.save(f, y_test_high)


    noise_dic = {
        'none' : {
            'percent' : 0,
            'y_train' : y_train,
            'y_val' : y_val,
            'y_test' : y_test
        },
        'low' : {
            'percent' : 5,
            'y_train' : y_train_low,
            'y_val' : y_val_low,
            'y_test' : y_test_low
        },
        'high' : {
            'percent' : 10,
            'y_train' : y_train_high,
            'y_val' : y_val_high,
            'y_test' : y_test_high
        }
    }

    #For each extractor apply the experiment with low noise labels
    for extractor in feature_learners.keys():
        for noise_level in noise_dic.keys():

            y_train_noisy = noise_dic[noise_level]['y_train']
            y_val_noisy = noise_dic[noise_level]['y_val']
            y_test_noisy = noise_dic[noise_level]['y_test']

            print(f"## Experiment 1: {noise_level} Noise + {extractor} with {set}")
            print("Shape of X_train in experiment 1: ", X_train.shape)
            
            #check storage for features and generate if necesary
            if os.path.exists(f'temp/{set}_{extractor}_features_train_{noise_level}_noise.npy'):
                f_train = np.load(f'temp/{set}_{extractor}_features_train_{noise_level}_noise.npy', allow_pickle=True)
            else:
                f_learner = feature_learners[extractor](X_train, y=y_train_noisy)
                f_learner.fit(X_train, y_train_noisy, X_val, y_val_noisy)
                f_train = f_learner.get_features(X_train)
                
                if WRITE_FEATURES:
                    f = open(f'temp/{set}_{extractor}_features_train_{noise_level}_noise.npy', 'wb+') 
                    np.save(f, f_train)
                    f.close()

            if os.path.exists(f'temp/{set}_{extractor}_features_test_{noise_level}_noise.npy'):
                f_test = np.load(f'temp/{set}_{extractor}_features_test_{noise_level}_noise.npy', allow_pickle=True)
            else:
                f_test = f_learner.get_features(X_test)
                
                if WRITE_FEATURES:
                    f = open(f'temp/{set}_{extractor}_features_test_{noise_level}_noise.npy', 'wb+') 
                    np.save(f, f_test)
                    f.close()

            #generate a fresh KNN classifier and fit it to the feature set
            model = KNeighborsClassifier(n_neighbors=K, weights='distance', metric='cosine')
            #model = SVC()
            model.fit(f_train, y_train_noisy)

            #predict a label for every instance
            y_pred = model.predict(f_test)

            #flatten labels if they're one-hot
            if y_pred.ndim > 1:
                y_pred = np.argmax(y_pred, axis=-1)

            #iterate over predicted labels, tabulate mispredictions
            num_instances = X_test.shape[0]
            count_mispredicted = 0
            count_mispred_given_cor = 0
            count_mispred_given_inc = 0
            count_lab_equals_class = 0
            count_cor = 0
            count_inc = 0
            
            for i in range(len(y_pred)): 
                #Mislabeled
                if y_test_noisy[i] != y_test[i]:
                    count_inc += 1
                    if y_pred[i] != y_test_noisy[i]:
                        count_mispredicted += 1
                        count_mispred_given_inc += 1
                #Correct Label
                else:
                    count_cor += 1
                    if y_pred[i] != y_test_noisy[i]:
                        count_mispredicted += 1
                        count_mispred_given_cor += 1
                
                if y_pred[i] == y_test[i]:
                    count_lab_equals_class += 1

            #add up the results in the results dictionary
            results['set'].append(set)
            results['features'].append(extractor)
            results['noise percent'].append(noise_dic[noise_level]['percent'])
            results['accuracy'].append(accuracy_score(y_pred, y_test_noisy))
            results['P(mispred)'].append(count_mispredicted / num_instances)
            results['P(mispred|correct)'].append(count_mispred_given_cor / count_cor)
            results['P(mispred|incorrect)'].append(count_mispred_given_inc / count_inc if count_inc != 0 else 0)
            results['P(pred label = class)'].append(count_lab_equals_class/num_instances)
            results['number mislabeled'].append(count_inc)
            results['train clusterability'].append(compute_apparent_clusterability(f_train, y_train))
            results['test clusterability'].append(compute_apparent_clusterability(f_test, y_test))
        # End for noise level
    #End for feature extractor

    return results

    



        





