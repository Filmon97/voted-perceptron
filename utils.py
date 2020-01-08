"""
utils.py

- Mnist loader,
- Progress bar
- model save & load

"""

import numpy as np
import os
from tqdm import tqdm

import urllib.request
from urllib.parse import urljoin
import gzip

import joblib

import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
from high_performance import (
    predictions,
    highest_score_arg,
    fit
)
# _________________________________________________________________________________
# Progress Bar


class MnistDataset:
    """Mnist utils"""

    def __init__(self, refresh=False):
        self.mnist_path_dir = 'mnist'
        self.datasets_url = 'http://yann.lecun.com/exdb/mnist/'
        self.refresh = refresh

    def download_file(self, download_file):

        output_file = os.path.join(self.mnist_path_dir, download_file)

        if self.refresh or not os.path.isfile(output_file):
            print('downloading {0} from {1}'.format(
                download_file, self.datasets_url))
            url = urljoin(self.datasets_url, download_file)
            download_url(url, output_file)

        return output_file

    def load_mnist(self, train_test='train'):

        try:
            os.makedirs(self.mnist_path_dir, exist_ok=False)
            print('Creating mnist directory')
        except:
            pass

        # Load MNIST dataset from 'path'
        labels_path = self.download_file(
            '{}-labels-idx1-ubyte.gz'.format(train_test))
        images_path = self.download_file(
            '{}-images-idx3-ubyte.gz'.format(train_test))

        with gzip.open(labels_path, 'rb') as lbpath:
            lbpath.read(8)
            buffer = lbpath.read()
            labels = np.frombuffer(buffer, dtype=np.uint8)

        with gzip.open(images_path, 'rb') as imgpath:
            imgpath.read(16)
            buffer = imgpath.read()
            images = np.frombuffer(buffer,
                                   dtype=np.uint8).reshape(len(labels),
                                                           784).astype(np.float32)

        return images, labels

    def train_dataset(self):
        return self.load_mnist(train_test='train')

    def test_dataset(self):
        return self.load_mnist(train_test='t10k')

# _________________________________________________________________________________
# Progress Bar


class ProgressBar(tqdm):
    """Progress utils"""

    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)


def download_url(url, output_file):
    with ProgressBar(unit='B', unit_scale=True,
                     miniters=1, desc=url.split('/')[-1]) as t:
        urllib.request.urlretrieve(
            url, filename=output_file, reporthook=t.update_to)

# _________________________________________________________________________________
# model save & load


class Pretrained:
    """Pretrained utils"""

    def __init__(self):
        self.model_path_dir = 'models'

    def save_model(self, model, filename):
        try:
            os.makedirs(self.model_path_dir, exist_ok=False)
            #print('Creating models directory')
        except:
            pass
        i = 0
        output_file = os.path.join(
            self.model_path_dir, filename) + '_{}.pkl'.format(i)
        while os.path.isfile(output_file):
            i = i + 1
            output_file = os.path.join(
                self.model_path_dir, filename) + '_{}.pkl'.format(i)
        # compression level = 9
        joblib.dump(model, output_file, 9)

    def load_model(self, filename):
        input_file = os.path.join(self.model_path_dir, filename) + '.pkl'
        return joblib.load(input_file)

# _________________________________________________________________________________
# Experiment utils

def test_error(X, models, test, label, kernel_degree):
    scores_random = np.empty(test.shape[0])
    scores_last = np.empty(test.shape[0])
    scores_avg = np.empty(test.shape[0])
    scores_vote = np.empty(test.shape[0])
    j = 0
    for x in test:
        s_random = np.empty(10)
        s_last = np.empty(10)
        s_avg = np.empty(10)
        s_vote = np.empty(10)
        for i in range(10):
            predictions_array = predictions(
                X, models[i, 0], models[i, 1], models[i, 2], x, kernel_degree)
            s_random[i] = predictions_array[0]
            s_last[i] = predictions_array[1]
            s_avg[i] = predictions_array[2]
            s_vote[i] = predictions_array[3]
        # Survival Of The Fittest
        scores_random[j] = highest_score_arg(s_random)
        scores_last[j] = highest_score_arg(s_last)
        scores_avg[j] = highest_score_arg(s_avg)
        scores_vote[j] = highest_score_arg(s_vote)
        j = j + 1

    error_random = np.sum(scores_random != label) / label.shape[0]
    error_last = np.sum(scores_last != label) / label.shape[0]
    error_avg = np.sum(scores_avg != label) / label.shape[0]
    error_vote = np.sum(scores_vote != label) / label.shape[0]

    return error_random, error_last, error_avg, error_vote


def n_mistakes(models):
    m = 0
    for o in range(10):
        m = m + models[o,3]
    return m

def n_supvect(models):
    s_v = 0
    for o in range(10):
        s_v = s_v + models[o,1].shape[0]
    return s_v

def save_models(models, epoch, kernel_degree):
    # print("saving models in models/...")
    pretrained = Pretrained()
    if epoch < 1:
        epoch = '0_{}'.format(int(epoch * 10))
    pretrained.save_model(
        models, 'pretrained_e{0}_k{1}'.format(epoch, kernel_degree))


def load_models(epoch, kernel_degree, same):
    # print("loading models from models/...")
    pretrained = Pretrained()
    if epoch < 1:
        epoch = '0_{}'.format(int(epoch * 10))
    return pretrained.load_model('pretrained_e{0}_k{1}_{2}'.format(epoch, kernel_degree, same))


def train_and_store(X_train, y_train, epoch, kernel_degree):
    models = np.array(fit(X_train, y_train, epoch, kernel_degree))
    save_models(models, epoch, kernel_degree)


def load_and_test(X_train, X_test, y_test, epoch, kernel_degree, same=0):
    models = load_models(epoch, kernel_degree, same)
    e_r, e_l, e_a, e_v = test_error(
        X_train, models, X_test, y_test, kernel_degree)
    perc_r = e_r * 100
    perc_l = e_l * 100
    perc_a = e_a * 100
    perc_v = e_v * 100
    # print("{0:.2f}".format(perc))
    return perc_r, perc_l, perc_a, perc_v


def train_and_store_k_perm(X_train, y_train, epoch, kernel_degree, k):
    np.random.seed(31415)
    print("training k permutation")
    for _ in range(k):
        arr = np.append(X_train, np.expand_dims(y_train, axis=1), axis=1)
        arr = np.random.permutation(arr)
        X_perm = arr[:, 0:-1].copy()
        y_perm = arr[:, -1].copy()
        models = fit(X_perm, y_perm, epoch, kernel_degree)
        save_models(models, epoch, kernel_degree)


def load_and_test_k_perm(X_train, X_test, y_test, epoch, kernel_degree, k):
    print("loading k permutation and training 10 classes")
    for i in range(k):
        models = load_models(epoch, kernel_degree, i)
        error = test_error(X_train, models, X_test, y_test, kernel_degree)
        perc = error * 100
        print("{0:.2f}".format(perc))


def freund_schapire_experiment(X_train, y_train):
    freund_schapire_training(X_train, y_train)
    # TODO
    # freund_schapire_testing(X_test, y_test)


def freund_schapire_training(X_train, y_train):
    print("training the perceptron algorithm on MNIST dataset")

    # from 0.1 to 0.9
    print("epoch: from 0.1 to 0.9")
    for i in range(1, 10):
        for kernel_degree in range(1, 6):
            train_and_store_k_perm(X_train, y_train, i / 10, kernel_degree, 5)

    # from 1 to 9
    print("epoch: from 1 to 9")
    for i in range(1, 10):
        for kernel_degree in range(1, 6):
            train_and_store_k_perm(X_train, y_train, i, kernel_degree, 5)

    # 10 the last width kernel 1
    print("epoch: 10")
    for i in range(10, 11):
        for kernel_degree in range(1, 6):
            train_and_store_k_perm(X_train, y_train, i, kernel_degree, 5)

    # from 20 to 30
    print("epoch: from 20 to 30")
    for i in range(20, 40, 10):
        for kernel_degree in range(2, 6):
            train_and_store_k_perm(X_train, y_train, i, kernel_degree, 5)


def lightweight_training(X_train, y_train):
    print("training the perceptron algorithm on MNIST dataset")

    # from 0.1 to 0.9
    print("epoch: from 0.1 to 0.9")
    for i in tqdm(range(1, 10)):
        for kernel_degree in range(1, 6):
            train_and_store(X_train, y_train, i / 10, kernel_degree)

    # from 1 to 9
    print("epoch: from 1 to 9")
    for i in tqdm(range(1, 10)):
        for kernel_degree in range(1, 6):
            train_and_store(X_train, y_train, i, kernel_degree)

    # 10 the last width kernel 1
    print("epoch: 10")
    for i in tqdm(range(10, 11)):
        for kernel_degree in range(1, 6):
            train_and_store(X_train, y_train, i, kernel_degree)

    # from 20 to 30
    print("epoch: from 20 to 30")
    for i in tqdm(range(20, 40, 10)):
        for kernel_degree in range(2, 6):
            train_and_store(X_train, y_train, i, kernel_degree)


def lightweight_testing(X_train, X_test, y_test):
    print("testing the perceptron algorithm on MNIST dataset")
    errors = []

    for kernel_degree in range(1, 6):
        same_kernel_errors = []

        # from 0.1 to 0.9
        print("epoch: from 0.1 to 0.9")
        for i in tqdm(range(1, 10)):
            same_kernel_errors.append(load_and_test(
                X_train, X_test, y_test, i / 10, kernel_degree))

        # from 1 to 9
        print("epoch: from 1 to 9")
        for i in tqdm(range(1, 10)):
            same_kernel_errors.append(load_and_test(
                X_train, X_test, y_test, i, kernel_degree))

        # 10 the last width kernel 1
        print("epoch: 10")
        for i in tqdm(range(10, 11)):
            same_kernel_errors.append(load_and_test(
                X_train, X_test, y_test, i, kernel_degree))

        # from 20 to 30
        print("epoch: from 20 to 30")
        for i in tqdm(range(20, 40, 10)):
            same_kernel_errors.append(load_and_test(
                X_train, X_test, y_test, i, kernel_degree))
        errors.append(same_kernel_errors)

    return errors


def lightweight_experiment():
    md = MnistDataset()
    # split data
    X_train, y_train = md.train_dataset()

    X_test, y_test = md.test_dataset()

    lightweight_training(X_train, y_train)

    errors = lightweight_testing(X_train, X_test, y_test)

    """ error_random = []
    error_last = []
    error_avg = []
    error_vote = []
    kernel = 4

    print("epoch: from 0.1 to 0.9 kernel:{}".format(kernel))
    x1 = np.arange(0.1, 1, 0.1)
    x2 = np.arange(1, 11)
    for i in tqdm(x1):
        e_r, e_l, e_a, e_v = load_and_test(X_train, X_test, y_test, i, kernel)
        error_random.append(e_r)
        error_last.append(e_l)
        error_avg.append(e_a)
        error_vote.append(e_v)
    print("epoch: from 1 to 10 kernel:{}".format(kernel))
    for i in tqdm(x2):
        e_r, e_l, e_a, e_v = load_and_test(X_train, X_test, y_test, i, kernel)
        error_random.append(e_r)
        error_last.append(e_l)
        error_avg.append(e_a)
        error_vote.append(e_v)

    log_plot(np.concatenate((x1, x2)), error_random, error_last, error_avg, error_vote, kernel) """


def simple_plot(errors, x, kernel_degree):
    plt.style.use('seaborn')
    plt.plot(x, errors, label='last(unorm)')
    plt.xlabel('Epoch')
    plt.ylabel('Test Error')
    plt.title('d={}'.format(kernel_degree))
    plt.legend()
    plt.show()


def log_plot(x, error_random, error_last, error_avg, error_vote, kernel_degree):
    """ errors should contains:
        - error_random,
        - error_last,
        - error_avg,
        - error_vote
    """
    plt.style.use('seaborn')
    fig = plt.figure(figsize=(10, 6))
    ax = fig.add_subplot(111)
    ax.plot(x, error_random, label='random(unorm)')
    ax.plot(x, error_last, label='last(unorm)')
    ax.plot(x, error_avg, label='avg(unorm)')
    ax.plot(x, error_vote, label='vote')
    ax.xaxis.set_major_formatter(ScalarFormatter())
    ax.set_title('d={}'.format(kernel_degree))
    ax.set_xlabel('Epoch')
    ax.set_ylabel('Test Error')
    plt.legend()
    plt.show()