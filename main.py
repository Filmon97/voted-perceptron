from utils import (MnistDataset, np)
from numba import njit

########## voted perceptron ############


def train(X, y, epoch):
	v1 = np.zeros(X.shape[1])
	c1 = 0
	v = np.array([v1])
	c = np.array([c1])
	print(v1.shape)
	print(v.shape)
	print(c.shape)
	# k = 0, w[0] = 0, c[0] = 0
	""" """ for _ in range(epoch):
		k = 0
		for xi, label in zip(X, y):
			if label == gamma(xi, w):
				c[k] = c[k] + 1
			else:
				v.append
				w[k] = w[k] + label * xi
				c[k+1] = 1
				k = k + 1 """
 """
	return (v, c)

def gamma(xi, w):
	dot_product = np.dot(xi, w)
	return np.where(dot_product >= 0.0, 1, -1)


def predict(v, c, x):
	""" x: un labeled instance"""
	s = 0
	for vi, ci in zip (v, c):
		s = s + ci * gamma(x, vi)
	return np.where(s >= 0.0, 1, -1)

if __name__ == "__main__":
	md = MnistDataset()
	X_train, y_train = md.train_dataset()

	X_test, y_test = md.test_dataset()

	print('Rows: {0}, columns: {1}'.format(X_train.shape[0], X_train.shape[1]))

	print('Rows: {0}, columns: {1}'.format(X_test.shape[0], X_test.shape[1]))

	# TODO One vs ALL
	# 	#y = np.where(y_test == '0', -1, 1)
	#print(y)
	v, c = train(X_train,y_train, 2)
	predicted_label = predict(v,c, X_test[1])
	 
	print("True label: {}".format(y_test[1]))
	print("Predicted label: {}".format(predicted_label))