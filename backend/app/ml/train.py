from sklearn.ensemble import RandomForestClassifier
import joblib

# Entraîner avec vos données
model = RandomForestClassifier()
model.fit(X_train, y_train)

# Sauvegarder
joblib.dump(model, 'models/ml_models/sms_model.pkl')
joblib.dump(vectorizer, 'models/ml_models/vectorizer.pkl')