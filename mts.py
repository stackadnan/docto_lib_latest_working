# import numpy as np
# import pandas as pd
# from sklearn.datasets import load_breast_cancer
# from sklearn.ensemble import RandomForestClassifier
# from sklearn.preprocessing import StandardScaler
# from sklearn.model_selection import train_test_split
# from scipy.spatial.distance import mahalanobis
# from sklearn.metrics import classification_report, confusion_matrix

# # Load dataset
# data = load_breast_cancer()
# X = pd.DataFrame(data.data, columns=data.feature_names)
# y = pd.Series(data.target)  # 0 = malignant (abnormal), 1 = benign (normal)

# # Step 1: Feature Selection using Random Forest
# rf = RandomForestClassifier(n_estimators=100, random_state=42)
# rf.fit(X, y)
# importances = rf.feature_importances_
# indices = np.argsort(importances)[::-1]

# # Select top N features
# N = 10
# top_features = X.columns[indices[:N]]
# X_selected = X[top_features]

# # Step 2: Standardize
# scaler = StandardScaler()
# X_scaled = scaler.fit_transform(X_selected)

# # Step 3: Split into train (build Mahalanobis space) and test
# X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.3, random_state=42)

# # Build Mahalanobis Space using ONLY class 1 (benign = normal)
# X_space = X_train[y_train == 1]
# mean_vector = np.mean(X_space, axis=0)
# cov_matrix = np.cov(X_space, rowvar=False)
# inv_cov_matrix = np.linalg.inv(cov_matrix)

# # Step 4: Compute Mahalanobis Distances
# def compute_md(x):
#     return mahalanobis(x, mean_vector, inv_cov_matrix)

# md_test = np.array([compute_md(x) for x in X_test])

# # Step 5: Threshold for classification
# # Use the max MD of training normal samples as threshold
# threshold = max([compute_md(x) for x in X_space])

# # Predict based on distance
# y_pred = (md_test > threshold).astype(int)  # 1 = abnormal (malignant), 0 = normal (benign)
# y_test_true = (y_test == 0).astype(int)     # same logic: 1 = abnormal

# # Step 6: Evaluate
# print("Confusion Matrix:")
# print(confusion_matrix(y_test_true, y_pred))
# print("\nClassification Report:")
# print(classification_report(y_test_true, y_pred))




from sklearn import datasets

# Built-in datasets you can load like this
available_datasets = {
    "iris": datasets.load_iris,
    "digits": datasets.load_digits,
    "wine": datasets.load_wine,
    "breast_cancer": datasets.load_breast_cancer,
    "diabetes": datasets.load_diabetes,
    "linnerud": datasets.load_linnerud,
    "covtype": datasets.fetch_covtype,
    "olivetti_faces": datasets.fetch_olivetti_faces,
    "20newsgroups": datasets.fetch_20newsgroups,
    "california_housing": datasets.fetch_california_housing
}

print("Available sklearn datasets:")
for name in available_datasets:
    print("-", name)

# Example: load and print info about 'wine' dataset
print("\n--- Example: 'wine' dataset ---")
data = datasets.load_iris()
print("Feature names:", data.feature_names)
print("Target names:", data.target_names)
print("Shape of data:", data.data.shape)
print("First row of features:", data.data[0])
print("First target label:", data.target[0])
