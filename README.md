# Jamvi (hatua ya 3: pochi ya coin)

App ya jamvi la mikeka, market na pochi ya coin. Inatumia Flask (Python), Neon kwa database na Cloudflare R2 kwa picha.

## Muundo wa faili

```
app.py            njia za kurasa, wasifu, pochi
auth.py           usajili, kuingia, Google, ulinzi wa fomu
wallet.py         kununua na kutoa coin (hali ya majaribio)
models.py         maswali ya database (watumiaji, pochi, miamala)
config.py         mipangilio kutoka .env
db.py             muunganisho wa Neon
schema.sql        majedwali ya database
storage.py        upakiaji wa picha kwenda R2
templates/        kurasa za HTML
static/           CSS na JS
```

## Kuendesha kwenye kompyuta

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # kisha jaza thamani zako
python app.py                    # majedwali yanatengenezwa yenyewe ombi la kwanza
```

Fungua http://localhost:5000

Ukijaribu kwenye `http://` bila SSL, weka `COOKIE_SECURE=0` kwenye `.env`. Kwenye hosting yenye https iache `1`.

Kama ulishaendesha `python db.py init` hatua ya 1, endesha tena. Haifuti data, inaongeza safu mpya tu.

## Usajili na kuingia

- **Barua pepe au namba ya simu** (Tanzania, mfano 0712345678) pamoja na nenosiri.
- **Google** (hiari): kitufe kinaonekana tu ukijaza `GOOGLE_CLIENT_ID` na `GOOGLE_CLIENT_SECRET`.
- Umri wa miaka 18+ unakaguliwa kwa tarehe ya kuzaliwa na uthibitisho wa mtumiaji.
- Kila mtumiaji mpya anapata pochi na zawadi ya coin bandia (`SIGNUP_BONUS`, hali ya demo tu).
- Majaribio mengi ya nenosiri yanafungwa kwa dakika 10 (kwa kila akaunti na IP).

### Kuwasha Google

1. Kwenye Google Cloud Console tengeneza "OAuth client ID" aina ya "Web application".
2. Kwenye "Authorized redirect URIs" weka `https://DOMAIN-YAKO/google/rudi` (kwa majaribio: `http://localhost:5000/google/rudi`).
3. Nakili Client ID na Client secret kwenye `.env`.

## Pochi ya coin

- **Nunua coin** (`/pochi/nunua`) na **Toa pesa** (`/pochi/toa`) zinafanya kazi hali ya majaribio tu: salio linabadilika, lakini hakuna pesa halisi inayoingia wala kutoka.
- Kila mabadiliko ya salio na muamala wake vinaandikwa kwa mkupuo mmoja, na salio haliwezi kushuka chini ya sifuri.
- Kila fomu ina tokeni ya mara moja, hivyo kubonyeza mara mbili hakukati wala hakuongezi mara mbili.
- `COIN_RATE_TZS` (chaguo-msingi 100) ni thamani ya coin 1 kwa shilingi; `MIN_WITHDRAW` (50) ni kiwango cha chini cha kutoa.
- `COIN_MODE` ikiwa si `demo`, kununua na kutoa vinafungwa kabisa hadi hatua ya 8.

## Mambo ambayo bado hayajafanyika

- Namba ya simu haijathibitishwa kwa SMS (inahitaji mtoa huduma wa SMS). Barua pepe pia haijathibitishwa kwa kiungo, isipokuwa ya Google.
- Kusahau/kubadilisha nenosiri (inahitaji kutuma barua pepe).
- Masharti ya matumizi na sera ya faragha (kurasa zitaongezwa kabla ya kuzindua).

## Kuunganisha Neon na R2

Tazama maelezo ya hatua ya 1: `DATABASE_URL` kwa Neon; `R2_*` kwa Cloudflare R2. Fungua `/afya` kuona kama zimeunganishwa.

## Hali ya coin

`COIN_MODE=demo` inamaanisha coin ni bandia. Malipo halisi (M-Pesa, Tigo Pesa, Airtel Money) na kutoa pesa vinaongezwa hatua ya 8, baada ya kupata leseni na ruhusa zinazotakiwa.

## Hatua zinazofuata

4. Jamvi la mikeka linalofanya kazi
5. Market inayofanya kazi
6. Ujumbe na arifa
7. Usimamizi (admin)
8. Malipo halisi
9. App ya Android/iPhone
