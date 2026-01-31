#!/bin/bash

API_URL="http://localhost:8000"

echo "Test DYLETH API"
echo "==============="
echo ""

echo "1. Health Check..."
curl -s $API_URL/health | python3 -m json.tool
echo ""

echo "2. Test vérification téléphone frauduleux..."
curl -s -X POST $API_URL/api/v1/phone/check-phone \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+33612345678",
    "country": "FR"
  }' | python3 -m json.tool
echo ""

echo "3. Test analyse SMS suspect..."
curl -s -X POST $API_URL/api/v1/sms/analyze-sms \
  -H "Content-Type: application/json" \
  -d '{
    "content": "URGENT! Votre colis attend. Payez 2€ maintenant: http://bit.ly/abc123",
    "sender": "+33612345678"
  }' | python3 -m json.tool
echo ""

echo "4. Test analyse email..."
curl -s -X POST $API_URL/api/v1/email/analyze-email \
  -H "Content-Type: application/json" \
  -d '{
    "sender": "noreply@fake-bank.com",
    "subject": "Action requise sur votre compte",
    "body": "Cher client, nous avons détecté une activité suspecte. Cliquez ici pour confirmer vos identifiants."
  }' | python3 -m json.tool
echo ""

echo "Tests terminés!"
