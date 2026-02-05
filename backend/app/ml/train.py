"""
Script d'entraînement des modèles ML pour DYLETH
Entraîne RandomForest pour classification SMS frauduleux
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import joblib
import os
from pathlib import Path

# Chemins
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "datasets"
MODEL_DIR = BASE_DIR / "models" / "ml_models"

# Créer dossiers si nécessaire
MODEL_DIR.mkdir(parents=True, exist_ok=True)

def train_sms_classifier():
    """Entraîne le classifieur SMS"""
    print("=" * 60)
    print("🤖 ENTRAÎNEMENT MODÈLE SMS DYLETH")
    print("=" * 60)

    # 1. Charger données
    print("\n📊 Chargement données...")
    df = pd.read_csv(DATA_DIR / "sms_train.csv")
    print(f"   ✓ {len(df)} SMS chargés")
    print(f"   ✓ Frauduleux: {df['is_fraud'].sum()} ({df['is_fraud'].sum()/len(df)*100:.1f}%)")
    print(f"   ✓ Légitimes: {(~df['is_fraud'].astype(bool)).sum()} ({(~df['is_fraud'].astype(bool)).sum()/len(df)*100:.1f}%)")

    # 2. Préparation données
    print("\n🔧 Préparation features...")
    X = df['content']
    y = df['is_fraud']

    # Split train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"   ✓ Train: {len(X_train)} SMS")
    print(f"   ✓ Test: {len(X_test)} SMS")

    # 3. Vectorisation TF-IDF
    print("\n📝 Vectorisation TF-IDF...")
    vectorizer = TfidfVectorizer(
        max_features=1000,
        ngram_range=(1, 2),
        min_df=2,
        stop_words=None  # On garde tout pour le français
    )

    X_train_tfidf = vectorizer.fit_transform(X_train)
    X_test_tfidf = vectorizer.transform(X_test)
    print(f"   ✓ {X_train_tfidf.shape[1]} features extraites")

    # 4. Entraînement Random Forest
    print("\n🌲 Entraînement Random Forest...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=20,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
        verbose=0
    )

    model.fit(X_train_tfidf, y_train)
    print("   ✓ Modèle entraîné")

    # 5. Évaluation
    print("\n📈 Évaluation modèle...")
    y_pred = model.predict(X_test_tfidf)
    y_proba = model.predict_proba(X_test_tfidf)

    accuracy = accuracy_score(y_test, y_pred)
    print(f"   ✓ Accuracy: {accuracy*100:.2f}%")

    # Rapport détaillé
    print("\n📊 Rapport classification:")
    print(classification_report(y_test, y_pred,
                                target_names=['Légitimes', 'Frauduleux'],
                                digits=3))

    # Matrice de confusion
    print("🔢 Matrice de confusion:")
    cm = confusion_matrix(y_test, y_pred)
    print(f"   Vrais Négatifs:  {cm[0][0]}")
    print(f"   Faux Positifs:   {cm[0][1]}")
    print(f"   Faux Négatifs:   {cm[1][0]}")
    print(f"   Vrais Positifs:  {cm[1][1]}")

    # 6. Features importantes
    print("\n🔝 Top 10 mots-clés frauduleux:")
    feature_names = vectorizer.get_feature_names_out()
    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1][:10]

    for i, idx in enumerate(indices, 1):
        print(f"   {i}. '{feature_names[idx]}' - {importances[idx]:.4f}")

    # 7. Test sur exemples
    print("\n🧪 Tests sur exemples:")
    test_messages = [
        "URGENT! Payez 2€ maintenant bit.ly",
        "Salut, ça va? On se voit ce soir?",
        "Votre compte bancaire sera bloqué",
        "RDV dentiste demain 14h"
    ]

    for msg in test_messages:
        features = vectorizer.transform([msg])
        pred = model.predict(features)[0]
        proba = model.predict_proba(features)[0]
        emoji = "🚨" if pred == 1 else "✅"
        print(f"   {emoji} '{msg[:40]}...'")
        print(f"      → {'FRAUDE' if pred == 1 else 'LÉGITIME'} (confiance: {proba[pred]:.2%})")

    # 8. Sauvegarder modèles
    print("\n💾 Sauvegarde modèles...")
    joblib.dump(model, MODEL_DIR / "sms_model.pkl")
    joblib.dump(vectorizer, MODEL_DIR / "vectorizer.pkl")
    print(f"   ✓ Modèle sauvegardé: {MODEL_DIR / 'sms_model.pkl'}")
    print(f"   ✓ Vectorizer sauvegardé: {MODEL_DIR / 'vectorizer.pkl'}")

    # 9. Métadonnées
    metadata = {
        'accuracy': float(accuracy),
        'n_samples_train': len(X_train),
        'n_samples_test': len(X_test),
        'n_features': X_train_tfidf.shape[1],
        'model_type': 'RandomForestClassifier',
        'version': '1.0'
    }

    joblib.dump(metadata, MODEL_DIR / "sms_metadata.pkl")
    print(f"   ✓ Métadonnées sauvegardées")

    print("\n" + "=" * 60)
    print(f"✅ ENTRAÎNEMENT TERMINÉ - Accuracy: {accuracy*100:.2f}%")
    print("=" * 60)

    return model, vectorizer, accuracy


def train_phone_classifier():
    """Entraîne le classifieur téléphone (simple pour MVP)"""
    print("\n📞 Entraînement modèle téléphone...")
    print("   ⚠️  Pour MVP: utilisation règles + base de données")
    print("   ℹ️  ML téléphone sera entraîné en Phase 2")


if __name__ == "__main__":
    print("\n" + "🚀" * 30)
    print("   DYLETH - ML Training Pipeline")
    print("🚀" * 30 + "\n")

    # Vérifier que les datasets existent
    if not (DATA_DIR / "sms_train.csv").exists():
        print("❌ Erreur: sms_train.csv introuvable")
        print(f"   Cherché dans: {DATA_DIR}")
        exit(1)

    # Entraîner SMS (priorité 1)
    model, vectorizer, accuracy = train_sms_classifier()

    # Téléphone (phase 2)
    train_phone_classifier()

    print("\n✅ Tous les modèles sont prêts!")
    print("\n💡 Prochaine étape:")
    print("   1. Redémarrer l'API: uvicorn app.main:app --reload")
    print("   2. Tester: curl -X POST http://localhost:8000/api/v1/sms/analyze-sms")
    print("")