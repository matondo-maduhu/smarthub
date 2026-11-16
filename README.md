# Jamvi (hatua ya 1: msingi na muonekano)

App ya jamvi la mikeka, market na pochi ya coin. Inatumia Flask (Python), Neon kwa database na Cloudflare R2 kwa picha.

## Muundo wa faili

```
app.py            njia (routes) za kurasa
config.py         mipangilio kutoka .env
db.py             muunganisho wa Neon
schema.sql        majedwali ya database
storage.py        upakiaji wa picha kwenda R2
templates/        kurasa za HTML
static/css/       muonekano
static/js/        vichujio na kubadilisha mandhari
```

## Kuendesha kwenye kompyuta

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # kisha jaza thamani zako
python app.py
```

Fungua http://localhost:5000

## Kuunganisha Neon

1. Kwenye Neon, nakili "Connection string" kisha weka kwenye `DATABASE_URL` ndani ya `.env`.
2. Tengeneza majedwali: `python db.py init`
3. Jaribu: `python db.py ping`

## Kuunganisha Cloudflare R2

1. Tengeneza bucket, kisha tengeneza API token (Object Read & Write).
2. Jaza `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`.
3. Washa anwani ya umma ya bucket, kisha weka kwenye `R2_PUBLIC_URL`.
4. Fungua `/afya` kuona kama Neon na R2 zimeunganishwa.

## Kuweka mtandaoni (production)

Amri ya kuanzisha: `gunicorn app:app`
Weka vigezo vya `.env` kwenye mipangilio ya huduma ya hosting, usiviweke kwenye repo.

## Hali ya coin

`COIN_MODE=demo` inamaanisha coin ni bandia. Malipo halisi (M-Pesa, Tigo Pesa, Airtel Money) na kutoa pesa vinaongezwa hatua ya 8, baada ya kupata leseni na ruhusa zinazotakiwa.

## Hatua zinazofuata

2. Usajili na akaunti
3. Pochi ya coin (majaribio)
4. Jamvi la mikeka linalofanya kazi
5. Market inayofanya kazi
6. Ujumbe na arifa
7. Usimamizi (admin)
8. Malipo halisi
9. App ya Android/iPhone
