#!/usr/bin/env python

import re
import numpy as np
import pandas as pd
import seaborn as sns

import matplotlib.pyplot as plt
from mpl_toolkits import mplot3d

# filenames
params_file = 'test_formatted'

def load_data(filename):
    datasets = []
    with open(filename, 'r') as f:
        new_dict = {}
        for line in f:
            if line.startswith('#'):
                datasets.append(new_dict)
                items = line.split()
                items[0] = items[0][1:]
                new_dict = {}
                for key in items:
                    new_dict[key] = []
            else:
                vals = line.split()
                keys = list(new_dict.keys())
                for idx, v in enumerate(vals):
                    try:
                        v = float(v)
                    except:
                        pass
                    new_dict[keys[idx]].append(v)
        datasets.append(new_dict)
    return datasets[1:]

def show_plots(data):
    for ds in data:
        keys = list(ds.keys())
        if len(keys) == 2:
            X = np.array(ds[keys[1]])
            Y = np.array(ds[keys[0]])
            df = pd.DataFrame({keys[0]: Y, keys[1]: X})
            max_index = np.argmax(Y)
            colors = ['C0'] * len(Y)
            colors[max_index] = 'C3'
            sns.set_style('whitegrid')
            g = sns.stripplot(x=keys[1], y=keys[0], data=df, color='C0', size=6)
            g.axes.cla()
            plt.sca(g.axes)
            plt.scatter(X, Y, c=colors)
            if isinstance(X[0], float):
                plt.xticks(list(range(int(min(X)), int(max(X) + 5), 5)))
            sns.despine()
            plt.subplots_adjust(right=0.96, left=0.06)
        elif len(keys) == 3:
            fig = plt.figure()
            ax = fig.add_subplot(111, projection='3d')
            X = np.array(ds[keys[1]])
            Y = np.array(ds[keys[2]])
            Z = np.array(ds[keys[0]])
            max_index = np.argmax(Z)
            colors = ['C0'] * len(Z)
            colors[max_index] = 'C3'
            ax.scatter3D(X, Y, Z, color=colors)
            ax.set_xlabel(keys[1])
            ax.set_ylabel(keys[2])
            ax.set_zlabel(keys[0])
            
            xticks = np.sort(np.unique(X))
            yticks = np.sort(np.unique(Y))
            ax.set_xticks(xticks)
            ax.set_yticks(yticks)
            plt.subplots_adjust(right = 0.96, left = 0.06)
        else:
            raise ValueError('4d plots not supported')
        plt.show()
        


if __name__ == '__main__':
    data = load_data(params_file)
    show_plots(data)