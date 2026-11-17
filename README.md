# Jamvi

App ya jamvi la mikeka, market na pochi ya coin. Inatumia Flask (Python), Neon kwa database na Cloudflare R2 kwa picha. Inafanya kazi kwenye simu na kompyuta.

> Faili hili linakusanya maelezo ya hatua zote. Kila hatua mpya inaongezwa chini ya "Historia ya hatua" na hakuna cha zamani kinachofutwa.

## Hali ya hatua zote

| Hatua | Maelezo | Hali |
|---|---|---|
| 1 | Msingi, muonekano, Neon na R2 | Imekamilika |
| 2 | Usajili na akaunti | Imekamilika |
| 3 | Pochi ya coin (majaribio) | Imekamilika |
| 4 | Jamvi la mikeka linalofanya kazi | Inafuata |
| 5 | Market inayofanya kazi | Bado |
| 6 | Ujumbe na arifa | Bado |
| 7 | Usimamizi (admin) | Bado |
| 8 | Malipo halisi (M-Pesa, Tigo Pesa, Airtel Money) | Bado, baada ya leseni |
| 9 | App ya Android/iPhone | Bado |

## Muundo wa faili

```
app.py            njia za kurasa, wasifu, pochi
auth.py           usajili, kuingia, Google, ulinzi wa fomu (CSRF)
wallet.py         kununua na kutoa coin (hali ya majaribio)
models.py         maswali ya database (watumiaji, pochi, miamala)
config.py         mipangilio kutoka .env
db.py             muunganisho wa Neon na utengenezaji wa majedwali
schema.sql        majedwali ya database
storage.py        upakiaji wa picha kwenda R2
templates/        kurasa za HTML
static/css/       muonekano
static/js/        vichujio, mandhari, makadirio ya pochi
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

Njia mbadala ya kutengeneza majedwali kwa mkono: `python db.py init`. Kujaribu muunganisho: `python db.py ping`.

## Kuweka mtandaoni (production)

- Amri ya kuanzisha (hosting ya kawaida): `gunicorn app:app`
- Vigezo vya `.env` viwekwe kwenye mipangilio ya huduma ya hosting. Usiviweke kwenye repo.

### Vercel

1. Weka vigezo kwenye **Project → Settings → Environment Variables**: `DATABASE_URL`, `SECRET_KEY`, `R2_*`, `COIN_MODE=demo`, na vingine vya `.env.example` unavyovihitaji.
2. Vercel haisomi faili la `.env`, na vigezo vipya havifanyi kazi kwenye deploy ya zamani. Baada ya kuviweka au kuvibadilisha, fanya **Redeploy**.
3. Vercel haiwezi kuendesha amri kama `python db.py init`. Ndiyo sababu app inatengeneza majedwali yenyewe kwenye ombi la kwanza (angalia "Majedwali yanajitengeneza" hapa chini).
4. Kuona makosa: **Project → Logs**. Fungua pia `/afya` kuona kama Neon na R2 zimeunganishwa.
5. Kosa la `relation "users" does not exist` linamaanisha majedwali hayakutengenezwa. Linaisha mara tu app ikiwa na toleo lenye utengenezaji wa kiotomatiki na `DATABASE_URL` sahihi.

## Kuunganisha Neon

1. Kwenye Neon, nakili "Connection string" kisha weka kwenye `DATABASE_URL` (inaishia `?sslmode=require`).
2. Majedwali yanatengenezwa yenyewe app ikianza. Au kwa mkono: `python db.py init`.
3. Jaribu: `python db.py ping` au fungua `/afya`.

## Kuunganisha Cloudflare R2

1. Tengeneza bucket, kisha tengeneza API token (Object Read & Write).
2. Jaza `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`.
3. Washa anwani ya umma ya bucket, kisha weka kwenye `R2_PUBLIC_URL`.
4. Fungua `/afya` kuona kama Neon na R2 zimeunganishwa.

## Hali ya coin

`COIN_MODE=demo` inamaanisha coin ni bandia. Malipo halisi (M-Pesa, Tigo Pesa, Airtel Money) na kutoa pesa halisi yanaongezwa hatua ya 8, baada ya kupata leseni na ruhusa zinazotakiwa. Nchini Tanzania hii inahusisha Bodi ya Michezo ya Kubahatisha (GBT) na kanuni za Benki Kuu kuhusu pesa za kielektroniki.

---

# Historia ya hatua

## Hatua ya 1: msingi na muonekano

- Kurasa tano: Nyumbani, Jamvi, Market, Pochi, Wasifu. Menyu ya chini kwa simu na menyu ya juu kwa kompyuta.
- Mandhari nyeusi na nyeupe (kitufe cha kubadilisha kinakumbuka chaguo), rangi chache zenye mpangilio na icons za SVG za kisasa.
- Jamvi: kadi za mikeka zenye vichujio (zote, zinazosubiri, zilizoshinda, zilizopoteza). Mikeka ya kulipia inaonyesha kufuli.
- Market: bidhaa za kawaida kwa vikundi, utafutaji na vichujio.
- Muunganisho wa Neon (`db.py`, `schema.sql`) na R2 (`storage.py`), pamoja na ukurasa wa `/afya`.
- Onyo la umri wa miaka 18+ na uwajibikaji kwenye kila ukurasa.
- Data ya mikeka na bidhaa ni ya mfano kwa sasa. Itabadilishwa na data halisi hatua ya 4 na 5.

## Hatua ya 2: usajili na akaunti

- **Njia za kujisajili**: barua pepe au namba ya simu ya Tanzania (mfano 0712345678) pamoja na nenosiri, na Google (hiari). Njia zaidi zitaongezwa baadaye.
- **Umri 18+**: unakaguliwa kwa tarehe ya kuzaliwa na uthibitisho wa mtumiaji. Aliye chini ya miaka 18 anakataliwa.
- **Pochi na zawadi**: kila mtumiaji mpya anapata pochi na zawadi ya coin bandia (`SIGNUP_BONUS`, hali ya demo tu).
- **Wasifu**: kubadilisha jina, kupakia picha (inakwenda R2) na kutoka kwenye akaunti.
- **Usalama**: manenosiri yamehifadhiwa kama hash, fomu zina ulinzi wa CSRF, majaribio mengi ya nenosiri yanafungwa kwa dakika 10 (kwa kila akaunti na IP), kurudi kwenye kiungo cha ndani tu baada ya kuingia, picha zinakaguliwa kwa aina halisi na si kwa jina la faili tu, akaunti zilizosimamishwa haziwezi kuingia, na akaunti ya Google haiunganishwi kimya kimya na akaunti ya nenosiri yenye barua pepe ileile.
- **Faili mpya**: `auth.py`, `models.py` na kurasa za kuingia, kujisajili na kukamilisha usajili.

### Kuwasha Google

1. Kwenye Google Cloud Console tengeneza "OAuth client ID" aina ya "Web application".
2. Kwenye "Authorized redirect URIs" weka `https://DOMAIN-YAKO/google/rudi` (kwa majaribio: `http://localhost:5000/google/rudi`).
3. Nakili Client ID na Client secret kwenye `GOOGLE_CLIENT_ID` na `GOOGLE_CLIENT_SECRET`. Kitufe cha Google kinaonekana tu zikiwa zimewekwa.

### Majedwali yanajitengeneza

App ikianza (au Vercel ikiamsha function mpya), ombi la kwanza linaendesha `schema.sql`. Inatengeneza tu yanayokosekana na haifuti data. Kufuli la Postgres linazuia maombi mawili ya kwanza kugongana. Majedwali mapya ya hatua zijazo yataongezwa kwenye `schema.sql` na yatajitengeneza yenyewe.

### Mambo ambayo bado hayajafanyika (hatua ya 2)

- Namba ya simu haijathibitishwa kwa SMS (inahitaji mtoa huduma wa SMS). Barua pepe pia haijathibitishwa kwa kiungo, isipokuwa ya Google.
- Kusahau au kubadilisha nenosiri (inahitaji kutuma barua pepe).
- Masharti ya matumizi na sera ya faragha (kurasa zitaongezwa kabla ya kuzindua).

## Hatua ya 3: pochi ya coin (majaribio)

- **Nunua coin** (`/pochi/nunua`): vifurushi vya coin 50, 100, 500 na 1,000, vikionyesha bei ya TSh. Coin zinaongezwa kwenye pochi, hakuna pesa halisi.
- **Toa pesa** (`/pochi/toa`): idadi ya coin, mtandao (M-Pesa, Tigo Pesa au Airtel Money) na namba ya simu. Coin zinakatwa, hakuna pesa halisi inayotumwa. Namba inahifadhiwa kwenye historia kwa tarakimu tatu za mwisho tu.
- **Historia ya miamala** kwenye Pochi, na salio linaonekana kwenye kila ukurasa.
- **Usahihi wa salio**: mabadiliko ya salio na muamala wake yanaandikwa kwa mkupuo mmoja, na salio haliwezi kushuka chini ya sifuri.
- **Kubonyeza mara mbili**: kila fomu ina tokeni ya mara moja inayohifadhiwa kwenye database (`idem_key`), kwa hiyo ombi moja haliwezi kutekelezwa mara mbili.
- **Usalama wa hali**: `COIN_MODE` ikiwa si `demo`, kununua na kutoa vinafungwa kabisa hadi hatua ya 8.
- **Mipangilio**: `COIN_RATE_TZS` (chaguo-msingi 100) ni thamani ya coin 1 kwa shilingi; `MIN_WITHDRAW` (chaguo-msingi 50) ni kiwango cha chini cha kutoa.
- **Faili mpya**: `wallet.py`, `pochi_nunua.html`, `pochi_toa.html`. Safu mpya `idem_key` kwenye jedwali la `transactions` (inaongezwa yenyewe kwenye database ya zamani).
- **Bado**: kiasi cha kuandika mwenyewe na vifurushi vikubwa zaidi (hiari, kulingana na uamuzi wako).

## Hatua zinazofuata

4. Jamvi la mikeka linalofanya kazi: kuweka mkeka, kuufunga kwa bei ya coin, kununua, maoni na viwango vya watabiri
5. Market inayofanya kazi
6. Ujumbe na arifa
7. Usimamizi (admin)
8. Malipo halisi
9. App ya Android/iPhone
