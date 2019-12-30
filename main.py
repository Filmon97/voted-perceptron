"""
main.py

    A python file used to represent the voted perceptron

    most common variables
    ----------
    kernel_degree : int
        the degree of the polynomial kernel function

    v_label_coeffs : ndarray
        The label components of the prediction vectors.

    v_train_indices : ndarray
        The training case indices of the prediction vectors.

    c : ndarray
        The votes for the prediction vectors.

    functions
    p.s. most of the function are decorated with njit,
    njit is the nopython mode of numba and it is the
    compiled mode (*the code inside those function
    will be strange and non pythonic*)
    ----------
    """

from utils import (
    MnistDataset,
    Pretrained,
    np
)
import matplotlib.pyplot as plt
from numba import njit, prange
from math import copysign
from tqdm import tqdm


@njit
def train(X, y, epoch, kernel_degree):
    """Train the voted perceptron.

            Parameters
            ----------
            X : ndarray
                An ndarray where each row is a training case of the mnist dataset.

            y : ndarray
                An ndarray where each element is the label/classification of a
                training case in train_set for binary classification.
                Valid label values are -1 and 1.

            epochs : int
                The number of epochs to train.
            """

    # prediction vector's xi
    # v_train_indices = []
    # prediction vector's labels
    # v_label_coeffs = []
    # weights of the prediction vectors
    c = np.array((1, 0), dtype=np.int64)

    #v1 = np.zeros(X.shape[1])
    # don't call np.array on a np.array var
    v_train_indices = np.array((1, 0), dtype=np.int64)
    v_label_coeffs = np.array((1, 0), dtype=np.int64)
    v_train_indices[0] = -1
    # i will use the negative index as a flag to use np.zeros...
    # first v = 1*zero_vector
    weight = 0
    mistakes = 0
    for _ in range(epoch):
        # for xi, label in zip(X, y):
        # numba don't support nested arrays
        for i in range(X.shape[0]):
            xi = X[i]
            label = y[i]
            # same here i can't use sum over the prediction vector
            # we need to iterate over a variable
            # we define a new function
            y_hat = copysign(1, implicit_form_product(
                X, v_train_indices, v_label_coeffs, xi, kernel_degree)[-1])
            # we take always the last prediction vector's product
            # complexity of implicit_form_product is O(k)
            if y_hat == label:
                weight = weight + 1
            else:
                c = np.append(c, np.array([weight]), axis=0)
                v_train_indices = np.append(
                    v_train_indices, np.array([i]), axis=0)
                v_label_coeffs = np.append(
                    v_label_coeffs, np.array([label]), axis=0)
                # reset #C_k+1 = 1
                weight = 1
                mistakes = mistakes + 1
    c = np.append(c, np.array([weight]), axis=0)
    c = c[1:c.shape[0]]
    return v_train_indices, v_label_coeffs, c, mistakes


@njit(parallel=True)
def implicit_form_product(X, v_train_indices, v_label_coeffs, x, kernel_degree):
    dot_products = np.empty(v_train_indices.shape[0], dtype=np.float64)
    v_x = np.empty(v_train_indices.shape[0], dtype=np.float64)
    for i in range(v_train_indices.shape[0]):
        yi = v_label_coeffs[i]
        if v_train_indices[i] < 0:
            xi = np.zeros(X.shape[1])
        else:
            xi = X[v_train_indices[i]]
        dot_products[i] = yi * polynomial_expansion(xi, x, kernel_degree)
        if i == 0:
            v_x[0] = dot_products[0]
        else:
            v_x[i] = v_x[i-1] + dot_products[i]

    return v_x

# TODO reduce the number of for loops
@njit
def implicit_form_v(X, v_train_indices, v_label_coeffs):
    products = np.empty(v_train_indices.shape[0], dtype=np.float64)
    for i in range(v_train_indices.shape[0]):
        yi = v_label_coeffs[i]
        if v_train_indices[i] < 0:
            xi = np.zeros(X.shape[1])
        else:
            xi = X[v_train_indices[i]]
        products[i] = (yi * xi)

    # i can't use itertools.accumulate and
    # np.add.accumulate(product)
    # is not implemented in numba
    # numba pull #4578
    # we will iterate to create the array
    v = np.empty(v_train_indices.shape[0], dtype=np.float64)
    for i in range(1, products.shape[0]):
        v[i] = v[i - 1] + products[i]

    return v


@njit
def polynomial_expansion(xi, xj, d):
    return (1 + np.dot(xi, xj)) ** d

# _________________________________________________________________________________
# prediction functions


@njit
def last_unnormalized(X, v_train_indices, v_label_coeffs, x, kernel_degree):
    """Compute score using the final prediction vector(unnormalized)"""
    """ x: unlabeled instance"""
    score = implicit_form_product(X,
                                  v_train_indices, v_label_coeffs, x, kernel_degree)[-1]

    return score


@njit
def normalize(score, v):
    norm = np.linalg.norm(v)
    if norm == 0:
        return score
    return score / norm


@njit
def last_normalized(X, v_train_indices, v_label_coeffs, x, kernel_degree):
    """Compute score using the final prediction vector(normalized)"""
    """ x: unlabeled instance"""
    score = last_unnormalized(
        X, v_train_indices, v_label_coeffs, x, kernel_degree)

    return normalize(score, implicit_form_v(X, v_train_indices, v_label_coeffs)[-1])


@njit
def vote(X, v_train_indices, v_label_coeffs, c, x, kernel_degree):
    """Compute score using analog of the deterministic leave-one-out conversion"""
    """ x: unlabeled instance"""

    dot_products = implicit_form_product(X,
                                         v_train_indices, v_label_coeffs, x, kernel_degree)

    s = np.empty(v_train_indices.shape[0])
    for i in range(v_train_indices.shape[0]):
        weight = c[i]
        v_x = dot_products[i]
        s[i] = weight * copysign(1, v_x)

    return s


@njit
def avg_unnormalized(X, v_train_indices, v_label_coeffs, c, x, kernel_degree):
    """Compute score using an average of the prediction vectors"""
    """ x: unlabeled instance"""

    dot_products = implicit_form_product(X,
                                         v_train_indices, v_label_coeffs, x, kernel_degree)

    s = np.empty(v_train_indices.shape[0])
    for i in range(v_train_indices.shape[0]):
        weight = c[i]
        v_x = dot_products[i]
        s[i] = weight * v_x

    return s


@njit
def avg_normalized(X, v_train_indices, v_label_coeffs, c, x, kernel_degree):
    """Compute score using an average of the prediction vectors(normalized)"""
    """ x: unlabeled instance"""

    dot_products = implicit_form_product(X,
                                         v_train_indices, v_label_coeffs, x, kernel_degree)
    v = implicit_form_v(X, v_train_indices, v_label_coeffs)
    s = np.empty(v_train_indices.shape[0])
    for i in range(v_train_indices.shape[0]):
        weight = c[i]
        v_x = dot_products[i]
        s[i] = weight * normalize(v_x, v[i])

    return s


@njit
def highest_score_arg(s):
    return np.argmax(s)


@njit
def highest_score(s):
    return np.max(s)

# _________________________________________________________________________________
# model functions


@njit(parallel=True)
def fit(X, y, epoch, kernel_degree):
    array = []
    for i in prange(10):
        array.append(model(X, y, i, epoch, kernel_degree))
    return array


@njit
def model(X, y, class_type, epoch, kernel_degree):
    y = np.where(y == class_type, 1, -1)
    if epoch < 1:
        divider = int(epoch * 100)
        # contiguous arrays
        fraction_x = X[0:int(X.shape[0] / divider),
                       :].copy()
        fraction_y = y[0:int(X.shape[0] / divider)].copy()
        return train(fraction_x, fraction_y, 1, kernel_degree)
    return train(X, y, epoch, kernel_degree)

#TODO: parallelize
def test_error(X, models, test, label, kernel_degree):
    scores = np.empty(test.shape[0])
    j = 0
    for x in test:
        s = np.empty(10)
        for i in range(10):
            s[i] = last_unnormalized(
                X, models[i, 0], models[i, 1], x, kernel_degree)
        # Survival Of The Fittest
        scores[j] = highest_score_arg(s)
        j = j + 1
    error = (scores != label).sum() / label.shape[0]
    return error

# TODO define SupVect and Mistakes function


def save_models(models, epoch, kernel_degree):
    #print("saving models in models/...")
    pretrained = Pretrained()
    if epoch < 1:
        epoch = '0_{}'.format(int(epoch * 10))
    pretrained.save_model(
        models, 'pretrained_e{0}_k{1}'.format(epoch, kernel_degree))


def load_models(epoch, kernel_degree, same):
    #print("loading models from models/...")
    pretrained = Pretrained()
    if epoch < 1:
        epoch = '0_{}'.format(int(epoch * 10))
    return pretrained.load_model('pretrained_e{0}_k{1}_{2}'.format(epoch, kernel_degree, same))


def train_and_store(X_train, y_train, epoch, kernel_degree):
    models = np.array(fit(X_train, y_train, epoch, kernel_degree))
    save_models(models, epoch, kernel_degree)


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

    for kernel_degree in range(1, 6):
        # from 0.1 to 0.9
        for i in range(1, 10):
            train_and_store_k_perm(X_train, y_train, i/10, kernel_degree, 5)

        # from 1 to 9
        for i in range(1, 10):
            train_and_store_k_perm(X_train, y_train, i, kernel_degree, 5)

        # from 10 to 30
        for i in range(10, 40, 10):
            train_and_store_k_perm(X_train, y_train, i, kernel_degree, 5)


def lightweight_experiment(X_train, y_train):
    print("training the perceptron algorithm on MNIST dataset")

    # from 0.1 to 0.9
    print("epoch: from 0.1 to 0.9")
    for i in tqdm(range(1, 10)):
        for kernel_degree in range(1, 6):
            train_and_store(X_train, y_train, i/10, kernel_degree)

    # from 1 to 9
    print("epoch: from 1 to 9")
    for i in tqdm(range(1, 10)):
        for kernel_degree in range(1, 6):
            train_and_store(X_train, y_train, i, kernel_degree)

    # from 10 to 30
    print("epoch: from 10 to 30")
    for i in tqdm(range(10, 40, 10)):
        for kernel_degree in range(1, 6):
            train_and_store(X_train, y_train, i, kernel_degree)


if __name__ == "__main__":
    md = MnistDataset()
    # split data
    X_train, y_train = md.train_dataset()

    X_test, y_test = md.test_dataset()

    lightweight_experiment(X_train, y_train)
