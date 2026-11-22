# Jamvi

App ya jamvi la mikeka, market na pochi ya coin. Inatumia Flask (Python), Neon kwa database na Cloudflare R2 kwa picha. Inafanya kazi kwenye simu na kompyuta.

> Faili hili linakusanya maelezo ya hatua zote. Kila hatua mpya inaongezwa chini ya "Historia ya hatua" na hakuna cha zamani kinachofutwa.

## Hali ya hatua zote

| Hatua | Maelezo | Hali |
|---|---|---|
| 1 | Msingi, muonekano, Neon na R2 | Imekamilika |
| 2 | Usajili na akaunti | Imekamilika |
| 3 | Pochi ya coin (majaribio) | Imekamilika |
| 4 | Jamvi la mikeka linalofanya kazi | Imekamilika |
| 5 | Market inayofanya kazi | Imekamilika |
| 6 | Ujumbe na arifa | Imekamilika |
| 7 | Usimamizi (admin) | Imekamilika |
| 8 | Malipo halisi (M-Pesa, Tigo Pesa, Airtel Money) | Inafuata, baada ya leseni |
| 9 | App ya Android/iPhone | Bado |

## Muundo wa faili

```
app.py            njia za kurasa, wasifu, pochi
auth.py           usajili, kuingia, Google, ulinzi wa fomu (CSRF)
wallet.py         kununua na kutoa coin (hali ya majaribio)
tips.py           jamvi la mikeka: kuweka, kununua, maoni, matokeo, viwango
market.py         market: bidhaa, picha, utafutaji, maagizo yenye escrow
chat.py           ujumbe wa moja kwa moja na kuzuia watumiaji
notifications.py  orodha ya arifa
admin.py          usimamizi na ripoti za watumiaji
vercel.json       ratiba ya kazi ya kila siku (cron)
football.py       mechi halisi, odds na matokeo (API-Football)
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

## Hatua ya 4: jamvi la mikeka linalofanya kazi

- **Kuweka mkeka** (`/jamvi/weka`): mchezo, ligi, mkeka wako, odds, saa ya mchezo (saa za Tanzania), bei (0 = bure, au coin 5 hadi `TIP_MAX_PRICE`) na maelezo ya hiari. Mchezo uanze angalau dakika 5 mbele na usizidi siku 30. Kikomo ni mikeka `MAX_TIPS_PER_DAY` (10) kwa siku kwa kila mtumiaji.
- **Orodha** (`/jamvi`): kichujio cha hali (zote, zinazosubiri, zilizoshinda, zilizopoteza) na kurasa za mikeka 20.
- **Mkeka uliofungwa**: mkeka na maelezo yake vinafichwa na seva yenyewe, havipo kwenye HTML kwa asiyenunua. Unaonekana kwa mwenye mkeka, kwa aliyenunua, na kwa wote baada ya matokeo kuwekwa (uwazi wa rekodi ya mtabiri).
- **Kununua**: mnunuzi analipa bei, muuzaji anapokea bei toa ada ya jukwaa (`TIP_FEE_PCT`, chaguo-msingi 10%), na miamala miwili inaandikwa kwa mkupuo mmoja. Kosa lolote linarudisha kila kitu nyuma. Mtu hawezi kununua mara mbili, kununua wake mwenyewe, mkeka wa bure, mkeka uliokwisha, wala baada ya mchezo kuanza.
- **Kupenda na maoni**: kupenda/kuondoa, maoni hadi herufi 500, kikomo cha maoni 5 kwa dakika, na kufuta maoni (mwenye maoni au msimamizi). Maoni yanatoroshwa dhidi ya XSS.
- **Matokeo**: mwenye mkeka anaweza kuweka umeshinda/umepoteza mara moja baada ya mchezo kuanza. Msimamizi anaweza kuweka au kurekebisha wakati wowote.
- **Kufuta**: mwenye mkeka anaweza kuufuta kama hakuna aliyeununua.
- **Wasifu wa mtabiri** (`/jamvi/mtabiri/<jina>`): idadi ya mikeka, ushindi, kupoteza na asilimia.
- **Viwango** (`/jamvi/viwango`): watabiri wenye angalau `MIN_SETTLED_FOR_RANK` (5) mikeka iliyokwisha, kwa asilimia ya ushindi.
- **Nyumbani** sasa inaonyesha mikeka halisi, na inafunguka hata database ikikosekana.
- **Faili mpya**: `tips.py`, `jamvi_weka.html`, `mkeka.html`, `mtabiri.html`, `viwango.html`. Majedwali: `tip_likes` mpya, safu `league` na `pick` kwenye `tips`, na `idx_comments_tip` (zinaongezwa zenyewe kwenye database ya zamani).
- **Mipangilio mipya**: `TIP_FEE_PCT`, `TIP_MAX_PRICE`, `MAX_TIPS_PER_DAY`, `MIN_SETTLED_FOR_RANK`.

### Kumfanya mtu kuwa msimamizi

Hakuna ukurasa wa usimamizi bado (hatua ya 7). Kwa sasa, kwenye SQL Editor ya Neon:

```sql
UPDATE users SET is_admin = TRUE WHERE username = 'jina_la_mtumiaji';
```

### Mambo ya kujua (hatua ya 4)

- **Matokeo yanaripotiwa na mtabiri mwenyewe.** Mtabiri asiye mwaminifu anaweza kuweka "umeshinda" kwa mkeka uliopoteza, na hilo linapotosha viwango. Hatua ya 7 itaongeza uthibitisho wa msimamizi na ripoti za watumiaji.
- **Hakuna kurudisha pesa (refund) bado.** Hali ya "umefutwa" (`void`) kwa mchezo ulioahirishwa na kurudishiwa wanunuzi itaongezwa hatua ya 7.
- **Maoni hayafichwi** kwa asiyenunua, kwa hiyo mtabiri au mnunuzi anaweza kuandika mkeka kwenye maoni. Udhibiti wa maudhui ni hatua ya 7.
- **Ada ya jukwaa** kwa sasa inatoweka (haiingii akaunti yoyote). Itaandikwa kwenye hesabu ya jukwaa hatua ya 8, pamoja na malipo halisi.
- Mikeka ya mfano ya hatua ya 1 imeondolewa; jamvi linaanza tupu na linajazwa na watumiaji halisi.

## Hatua ya 5: market inayofanya kazi

- **Kuweka bidhaa** (`/market/weka`): jina, kundi (simu na umeme, nguo na viatu, nyumbani, magari na pikipiki, chakula, huduma, mengineyo), bei kwa coin, mahali, maelezo, namba ya kuwasiliana (hiari) na picha hadi 4. Kikomo ni bidhaa `MAX_PRODUCTS_PER_DAY` (10) kwa siku kwa kila mtumiaji.
- **Picha**: zinakaguliwa kwa aina halisi (si jina la faili tu) na ukubwa (jpg, png, webp, gif; MB 5 kila moja; MB 20 kwa ombi lote) kabla ya kupakiwa R2. Upakiaji ukishindwa katikati, picha zilizokwisha pakiwa zinafutwa na bidhaa haiundwi. Bidhaa ikifutwa, picha zake zinafutwa R2.
- **Orodha na utafutaji** (`/market`): vikundi, utafutaji wa jina na maelezo, na kurasa za bidhaa 20. Bidhaa iliyoagizwa, kuuzwa au kufichwa haionekani kwenye orodha.
- **Kuagiza kwa coin (escrow)**: mnunuzi akiagiza, coin zinakatwa kwake lakini **hazimfikii muuzaji** hadi agizo likamilike. Bidhaa inafungwa (`reserved`) ili isiuzwe mara mbili. Kuuza mara mbili pia kunazuiwa na database yenyewe.
- **Mtiririko wa agizo**:
  1. Mnunuzi anaagiza na kuandika namba yake na mahali pa kukutana (muuzaji anaiona).
  2. Muuzaji anabonyeza "Nimekabidhi", au anaweza kughairi wakati wowote (mnunuzi anarudishiwa zote).
  3. Mnunuzi anabonyeza "Nimepokea" na muuzaji analipwa bei toa ada ya jukwaa (`MARKET_FEE_PCT`, chaguo-msingi 5%, inakatwa chini hadi shilingi nzima).
  4. Mnunuzi anaweza kughairi kabla muuzaji hajakabidhi. Baada ya kukabidhiwa, akiwa hajapokea anaweka "pingamizi" na coin zinabaki zimeshikiliwa.
  5. Muuzaji akikabidhi na mnunuzi asijibu kwa `ORDER_AUTO_RELEASE_DAYS` (7) siku, coin zinaachiliwa kwa muuzaji.
- **Pingamizi**: msimamizi anaweza kuachilia coin kwa muuzaji au kuzirudisha kwa mnunuzi kutoka ukurasa wa agizo. Muuzaji anaweza pia kughairi na kurudisha mwenyewe.
- **Faragha**: namba ya kuwasiliana ya muuzaji inaonekana kwa mnunuzi mwenye agizo tu. Agizo linaonekana kwa mnunuzi, muuzaji na msimamizi tu; wengine wanaona 404.
- **Maagizo yangu** (`/market/maagizo`): orodha ya ulizoagiza na ulizoagizwa.
- **Usahihi wa coin**: kila hatua ya agizo inafanyika kwa mkupuo mmoja na mshindi mmoja tu hata maombi mawili yakigongana. Jumla ya coin (salio + zilizoshikiliwa + ada) haibadiliki kamwe, na jaribio linalithibitisha.
- **Faili mpya**: `market.py`, `market.html` (imeandikwa upya), `bidhaa.html`, `bidhaa_weka.html`, `maagizo.html`, `agizo.html`. Jedwali jipya `orders`, safu `contact` kwenye `products`, na faharasa ya kuzuia agizo la pili wazi kwa bidhaa moja (zinaongezwa zenyewe kwenye database ya zamani).
- **Mipangilio mipya**: `MARKET_FEE_PCT`, `MARKET_MAX_PRICE`, `MAX_PRODUCTS_PER_DAY`, `ORDER_AUTO_RELEASE_DAYS`.
- **Mabadiliko mengine**: kikomo cha upakiaji wa ombi kimepanda kuwa MB 20 (kwa picha nyingi), na picha ya wasifu sasa ina kikomo cha MB 5. Bidhaa za mfano za hatua ya 1 zimeondolewa; market inaanza tupu.

### Mambo ya kujua (hatua ya 5)

- **Kuachilia kiotomatiki hakuna cron.** Siku 7 zikipita, coin zinaachiliwa pale mnunuzi au muuzaji anapofungua maagizo yake. Ukitaka iwe ya uhakika bila mtu kufungua, tutaongeza kazi ya kila siku (Vercel Cron) baadaye.
- **Hakuna kuhariri bidhaa.** Kwa sasa unaweza kuificha, kuifuta (kama haina maagizo) na kuweka upya. Kuhariri kunaweza kuongezwa.
- **Hakuna ujumbe kati ya mnunuzi na muuzaji** hadi hatua ya 6. Wanawasiliana kwa namba zilizo kwenye agizo.
- **Picha hazipunguzwi ukubwa.** Zinaonyeshwa kama zilivyopakiwa. Kwa kasi zaidi tunaweza kutumia ukubwa mdogo wa picha (Cloudflare Images au Pillow) baadaye.
- **Ada ya jukwaa inatoweka** (haiingii akaunti yoyote) hadi hatua ya 8, kama ilivyo kwa jamvi.
- **Pingamizi kamili la msimamizi** (orodha ya mapingamizi, ushahidi, ripoti) ni hatua ya 7. Kwa sasa msimamizi anaamua kutoka ukurasa wa agizo.

## Hatua ya 6: ujumbe na arifa

- **Ujumbe wa moja kwa moja** (`/ujumbe`): mazungumzo kati ya watu wawili tu. Kitufe cha "Tuma ujumbe" kipo kwenye bidhaa (kwa muuzaji), kwenye agizo (kwa upande wa pili) na kwenye wasifu wa mtabiri. Ujumbe 1 hadi 1000 herufi, hadi ujumbe 10 kwa dakika (`MESSAGES_PER_MINUTE`).
- **Kuonyesha ujumbe mpya**: ukurasa wa mazungumzo unaangalia ujumbe mpya kila sekunde 8 (hauangalii ukiwa umefichwa). Si "papo hapo" kamili kwa sababu Vercel haishikilii muunganisho wazi; kwa chat ya papo hapo tutahitaji huduma ya ziada baadaye.
- **Kuzuia**: mtumiaji anaweza kumzuia mwingine ("Mzuie") na kuondoa kizuizi. Aliyezuiwa hawezi kutuma na haambiwi kwa maneno ya moja kwa moja kuwa amezuiwa.
- **Faragha**: kila mazungumzo yanasomwa na wahusika wawili tu; mtu wa tatu haoni chochote.
- **Arifa** (`/arifa`, kengele ya juu): mkeka wako umenunuliwa; maoni kwenye mkeka wako; matokeo ya mkeka ulioununua; agizo jipya; muuzaji amekabidhi; pingamizi (muuzaji na wasimamizi wote); agizo limekamilika, limefutwa, au limeachiliwa na msimamizi au kiotomatiki. Arifa zinaandikwa ndani ya muamala uleule, kwa hiyo kitendo kikishindwa hakuna arifa ya uongo.
- **Alama ya idadi** inaonekana kwenye ikoni ya ujumbe na kengele.
- **Faili mpya**: `chat.py`, `notifications.py`, `mazungumzo.html`, `ujumbe.html`, `arifa.html`. Majedwali mapya: `messages`, `blocks`, `notifications` (yanajitengeneza yenyewe).
- **Mpangilio mpya**: `MESSAGES_PER_MINUTE` (hiari, chaguo-msingi 10).

### Mambo ya kujua (hatua ya 6)

- **Ujumbe haujasimbwa** (end-to-end): mwenye ufikiaji wa database anaweza kuusoma. Watumiaji wanaonywa wasitume nywila.
- **Hakuna ripoti ya unyanyasaji bado**; kuzuia ndiyo kinga ya sasa. Ripoti na hatua za msimamizi ni hatua ya 7.
- **Arifa hazifutwi kiotomatiki**; zinaonyeshwa 50 za mwisho.
- Ujumbe kati ya mnunuzi na muuzaji sasa unawezekana (tofauti na hatua ya 5).

## Hatua ya 7: usimamizi (admin)

Ukurasa: `/admin` (ikoni ya ngao kwenye header, kwa wasimamizi tu). Asiye msimamizi anapata 403.

- **Muhtasari**: idadi ya watumiaji, mikeka, bidhaa, maagizo wazi, mapingamizi, ripoti wazi, coin zote na zinazoshikiliwa.
- **Watumiaji**: kutafuta (jina, barua pepe, simu), kusimamisha na kuwasha akaunti, kuthibitisha. Huwezi kujisimamisha wala kumsimamisha msimamizi mwingine. Aliyesimamishwa anatolewa mara moja na hawezi kuingia.
- **Mikeka**: "Batilisha" huwarudishia wanunuzi bei kamili; muuzaji anakatwa alichopokea (bei toa ada) kadiri salio lake linavyoruhusu, na upungufu unabebwa na jukwaa. Inafanya kazi mara moja tu kwa kila mkeka. Mkeka usio na wanunuzi unaweza kufutwa. Kuweka au kurekebisha matokeo bado kunafanywa kwenye ukurasa wa mkeka.
- **Bidhaa**: kuficha na kuonyesha (bidhaa yenye agizo haiguswi).
- **Maagizo**: orodha kwa hali (mapingamizi kwanza); kuachilia au kurudisha coin kunafanywa kwenye ukurasa wa agizo kama hapo awali.
- **Ripoti**: watumiaji wanaweza kuripoti mtumiaji, mkeka au bidhaa ("Ripoti" kwenye kurasa hizo na kwenye mazungumzo). Ripoti moja wazi kwa kila mtu kwa kila kitu; wasimamizi wanaarifiwa; wanaifunga kama "imeshughulikiwa" au "puuza".
- **Kumbukumbu**: kila hatua ya msimamizi (kusimamisha, kuthibitisha, kubatilisha, kufuta, kuficha, kuachilia, kurudisha, kufunga ripoti, kurekebisha matokeo) inaandikwa na haifutwi.
- **Faili mpya**: `admin.py`, `admin_*.html`, `_admin_nav.html`, `_report.html`. Majedwali mapya: `reports`, `admin_log` (yanajitengeneza yenyewe).

### Mambo ya kujua (hatua ya 7)

- Kumfanya mtu msimamizi bado ni kwa SQL (tazama hatua ya 4), kwa makusudi.
- Kusimamisha akaunti hakughairi maagizo yake yaliyo wazi; shughulikia kwa "Maagizo" (achilia au rudisha).
- Maoni hayafichwi kwa ripoti bado (mwenye maoni au msimamizi anaweza kuyafuta kwenye ukurasa wa mkeka).
- Ripoti za ujumbe mmoja mmoja hazipo; unaripoti mtumiaji. Wasimamizi hawasomi ujumbe wa watu kupitia ukurasa huu.
- Matokeo ya mikeka bado yanawekwa na mtabiri; msimamizi anaweza kuyarekebisha.

### Kuwa msimamizi kupitia environment (nyongeza ya hatua ya 7)

Mbali na SQL, unaweza kuweka kwenye Vercel (Settings → Environment Variables) moja au zaidi ya hizi, kisha Redeploy:

```
ADMIN_USERNAMES=jina_lako
ADMIN_EMAILS=wewe@mfano.com
ADMIN_PHONES=0712345678
```

Orodha zinatenganishwa kwa koma. Mtumiaji anayelingana anakuwa msimamizi mara anapofungua app akiwa ameingia, na kitendo kinaandikwa kwenye kumbukumbu (`env_admin`). Kuondoa jina kwenye orodha **hakumwondolei cheo**; tumia `UPDATE users SET is_admin = FALSE WHERE username = '...'`.

**Tahadhari ya usalama**: barua pepe na simu bado hazithibitishwi (SMS/barua pepe ni kazi ijayo). Mtu anaweza kujisajili kwa jina, barua pepe au namba ya mtu mwingine kabla yake. Kwa hiyo jisajili wewe kwanza, kisha weka kwenye environment; na usiweke jina linaloweza kuchukuliwa na mtu mwingine kabla yako.
- Namba za simu zinahifadhiwa kama `+255712345678`; kwenye `ADMIN_PHONES` unaweza kuandika `0712345678` au `+255712345678`.

## Hatua ya 7B: sheria, nenosiri na kazi ya kila siku

- **Kurasa za `/masharti` na `/faragha`**: zinaonekana chini ya kila ukurasa na kwenye fomu ya usajili. **Hizi ni rasimu ya kawaida, si ushauri wa kisheria.** Kabla ya kufungua kwa umma (hasa malipo halisi), mwanasheria wa Tanzania azikague na kuongeza jina la kampuni, anwani ya mawasiliano, na mahitaji ya leseni ya michezo ya kubahatisha na ulinzi wa taarifa binafsi.
- **Kubadilisha nenosiri** (wasifu): linahitaji nenosiri la sasa, jipya lisilopungua herufi 8 na tofauti na la zamani; majaribio mabaya 5 yanazuia kwa dakika 10. Aliyejisajili kwa Google (hana nenosiri) anaweza kuweka la kwanza. Vikao vilivyofunguliwa kwenye vifaa vingine havifungwi nenosiri likibadilika (tutaongeza hilo baadaye).
- **Kuachilia coin kila siku (cron)**: `vercel.json` inaita `/cron/release` kila siku saa 3 asubuhi UTC. Ili ifanye kazi, weka kwenye Vercel Environment Variables `CRON_SECRET` (maneno marefu ya siri unayobuni) kisha Redeploy; Vercel hutuma siri hiyo yenyewe. Bila `CRON_SECRET` anwani hiyo inarudisha 404 na haifanyi kitu. Njia ya awali (kuachilia mtumiaji anapofungua maagizo) inabaki kama ziada.
- **Faili mpya**: `masharti.html`, `faragha.html`, `vercel.json`. Mpangilio mpya: `CRON_SECRET`.

## Marekebisho ya mpangilio (baada ya hatua ya 7B)

- **Header ya simu**: jina la app linafichwa kwenye skrini nyembamba ili ikoni zisikanyagane; ikoni na kiputo cha salio vimepunguzwa kidogo.
- **Menyu ya chini**: ina nafasi juu ya upau wa mfumo wa simu ili maandishi yasifunikwe.
- **Usimamizi**: vigae vya takwimu vyenye rangi zetu (bluu, kijani, machungwa, nyekundu, zambarau) badala ya jedwali lililobanana; vichujio vinashuka mstari unaofuata badala ya kukatwa; vitufe vya kila safu vinashuka chini ya maelezo kwenye simu.
- **Sehemu za kuandika** (ujumbe, ripoti, nenosiri): sasa zinatumia rangi za mandhari yetu kila mahali.
- **Faili zilizobadilika**: `static/css/style.css`, `templates/admin_dash.html`, `templates/_admin_nav.html`, `templates/admin_users.html`, `templates/admin_orders.html`, `templates/admin_reports.html`.

## Mwonekano tulivu na mpangilio mpya wa usimamizi

- **Mwonekano mzima**: pembe ndogo (6px), mistari myembamba, vitufe tambarare (kijani kwa kitendo kikuu, nyekundu kwa hatari), alama (labels) zenye mpaka, vihesabio vidogo vya kijivu (nyekundu kunapohitaji hatua), na vichujio vimekuwa tabo zenye mstari chini (tab iliyochaguliwa inaonekana hata orodha ikisogezwa). Nembo ni ya duara tambarare isiyo na mchanganyiko wa rangi.
- **Usimamizi**: kila ukurasa una kichwa na maelezo mafupi, kisha tabo, kisha visanduku vyenye vichwa. Muhtasari umepangwa kwa makundi: "Zinazohitaji hatua" (mapingamizi, ripoti), "Watumiaji na maudhui", "Coin", na mapingamizi yanayosubiri. Orodha zote zina kichwa chenye idadi.
- **Faili zilizobadilika**: `static/css/style.css`, `static/js/app.js`, `templates/admin_dash.html`, `admin_users.html`, `admin_tips.html`, `admin_products.html`, `admin_orders.html`, `admin_reports.html`, `admin_log.html`.

## Mkeka kujifunga muda ukiisha

- Mkeka unafungwa wenyewe mchezo unapoanza (`starts_at`). Hakuna cron wala kazi ya kuendesha: seva inalinganisha saa kila ombi, kwa hiyo unafungwa sekunde ileile.
- **Kabla ya kuanza**: kadi inasema "Wazi kwa kununua" na "Inafungwa baada ya saa 3" (au siku/dakika).
- **Baada ya kuanza**: kadi inasema "Imefungwa, inasubiri matokeo"; kitufe cha kununua kinaondoka na seva inakataa ununuzi hata ukijaribu kwa nguvu (coin hazikatwi). Mkeka wa kulipia unabaki umefichwa kwa wasionunua hadi matokeo yawekwe; wa bure unabaki wazi.
- Mtabiri anaweza kuweka matokeo mchezo ukishaanza (kama hapo awali).
- **Faili zilizobadilika**: `models.py`, `app.py`, `templates/_cards.html`, `templates/mkeka.html`.
- Bado hakuna kitu kinachomkumbusha mtabiri asiyeweka matokeo; msimamizi anaweza kuyarekebisha au kubatilisha mkeka.

## Odds halisi na hukumu ya kiotomatiki (API-Football)

Mikeka sasa inawekwa kwa **mechi halisi** na **odds halisi za kampuni za kubashiri**. Mtabiri hawezi kuandika odds wala matokeo kwa mkono.

**Jinsi inavyofanya kazi**
1. Mtabiri anachagua mechi (zinazofuata siku chache, ligi zilizochaguliwa) kwenye "Weka mkeka".
2. Anachagua mkeka: matokeo ya dakika 90 (nyumbani/sare/ugenini), nafasi mbili, timu zote kufunga, au jumla ya magoli (mistari 0.5 hadi 4.5). Odds bora inaonyeshwa kwa kila chaguo.
3. Anachagua kampuni ya kubashiri (zilizopendelezwa kwanza, orodha ya `FEATURED_BOOKMAKERS`; mfano Betpawa ikiwa huduma ina odds zake kwa mechi hiyo). Odds zinazorekodiwa ni zile za seva wakati wa kuweka mkeka, si za fomu.
4. Mchezo ukiisha (dakika 105 baada ya kuanza), mfumo unachukua matokeo na kuhukumu: umeshinda au umepoteza. Wanunuzi na mtabiri wanaarifiwa. Mechi iliyofutwa (CANC, ABD, AWD, WO) au iliyoahirishwa zaidi ya siku 5 inabatilisha mkeka na wanunuzi wanarudishiwa coin zote (muuzaji anakatwa alichopokea kadiri salio linavyoruhusu; upungufu unabebwa na jukwaa).
5. Mtabiri hawezi tena kuweka matokeo ya mkeka wa mechi halisi (hatari ya kudanganya imeondoka). Msimamizi bado anaweza kurekebisha.

**Kuwasha**: jisajili API-Football (api-sports.io), pata ufunguo, kisha kwenye Vercel weka `APIFOOTBALL_KEY` na Redeploy. Mpango wa bure ni maombi 100 kwa siku. Bila ufunguo, fomu ya mkono ya zamani inaendelea kufanya kazi.

**Mipangilio** (zote hiari): `FOOTBALL_LEAGUES` (ID za ligi, chaguo-msingi `567,39,140,135,78,61,2,3,12`), `FEATURED_BOOKMAKERS`, `ODDS_CACHE_MINUTES` (30), `FIXTURE_SYNC_HOURS` (6), `FIXTURE_DAYS_AHEAD` (3), `ALLOW_MANUAL_TIPS` (1 = ruhusu mikeka ya mkono hata ufunguo ukiwepo).

**Matumizi ya maombi** (kuweka ndani ya 100 kwa siku): mechi ni ombi moja kwa siku ya mbele kila saa 6; odds ni ombi moja kwa mechi, zinahifadhiwa dakika 30; matokeo ni ombi moja kwa mechi hadi 20, mara moja kila dakika 10 kwa kiwango cha juu. Maombi yakibaki chini ya 4, app inaacha kuomba hadi kesho. Hukumu inaendeshwa mtu anapofungua kurasa za jamvi, na pia na cron ya kila siku.

**Ukurasa wa admin "Mechi"**: maombi yaliyobaki, idadi ya mechi, "Sasisha mechi sasa", "Hukumu mikeka sasa", mikeka inayosubiri hukumu, na **kutafuta ligi** ili kupata ID.

### Mambo ya kujua (odds halisi)

- **Sijaijaribu kwenye API halisi** (hakuna mtandao hapa); nimejaribu kwa majibu bandia yenye muundo wa nyaraka. Baada ya kuweka ufunguo, hakikisha kwenye `/admin/mechi` kuwa mechi zinaonekana. Majina ya masoko yanayotumika: "Match Winner", "Double Chance", "Both Teams Score", "Goals Over/Under".
- **ID za ligi** (hasa Ligi Kuu Tanzania `567`) ni za kukisia: thibitisha kwa kutafuta ligi kwenye admin na ubadilishe `FOOTBALL_LEAGUES` ikihitajika. Jina la ligi linaonekana kwenye kila mechi, kwa hiyo kosa ni rahisi kuliona.
- **Kampuni zinazopatikana ni zile ambazo API ina**. Si lazima Betpawa au kampuni nyingine ya hapa iwepo; ikikosekana, mtabiri anachagua kampuni nyingine. App haichukui odds kutoka tovuti za kampuni kwa kuzisoma moja kwa moja.
- Odds za kabla ya mechi zinasasishwa na huduma kila masaa 3 hivi, na zinapatikana kwa takribani siku 1 hadi 14 kabla ya mechi.
- Matokeo ni ya **dakika 90** (bila muda wa nyongeza wala penalti).
- Mikeka ya zamani ya mkono inabaki kama ilivyo (inahukumiwa na mtabiri).
- **Faili zilizobadilika**: `football.py` (mpya), `config.py`, `schema.sql`, `models.py`, `tips.py`, `admin.py`, `app.py`, `templates/jamvi_weka.html`, `jamvi_weka_mechi.html` (mpya), `admin_mechi.html` (mpya), `_admin_nav.html`, `_cards.html`, `mkeka.html`, `static/css/style.css`, `.env.example`. Majedwali mapya: `fixtures`, `odds_cache`, `kv`; safu mpya kwenye `tips`: `fixture_id`, `market`, `selection`, `bookmaker` (zinajitengeneza zenyewe).

## Hatua zinazofuata

8. Malipo halisi
9. App ya Android/iPhone

## Marekebisho ya mpangilio wa simu (Market na Jamvi)
- Kisanduku cha kutafuta kwenye Market kilikuwa na mpaka maradufu na maandishi yalikatwa; sasa ni mpaka mmoja na kinajaza nafasi.
- Kichwa cha ukurasa na kitufe cha "Weka mkeka/bidhaa" havigawanyiki tena mistari miwili kwenye skrini ndogo.
- Faili lililobadilika: `static/css/style.css`.

## Matangazo (kisliderisha cha ukurasa wa nyumbani)
Admin anaweka matangazo yanayoonekana juu ya ukurasa wa nyumbani kama slaidi zinazoteleza zenyewe kila sekunde 5 (mtumiaji anaweza kuburuta kwa kidole; vitone vinaonyesha slaidi ya sasa).

**Kuweka:** Usimamizi → tabo **Matangazo**. Kila tangazo lina:
- Kichwa, maelezo mafupi na maandishi ya kitufe (hiari).
- Rangi: kijani, samawati, njano, zambarau au nyeusi.
- Kinapeleka wapi: chaguo la haraka (Jamvi, Market, Pochi, Weka mkeka, Weka bidhaa, Viwango, Usajili) au kiungo chochote (`/market?aina=simu` au `https://…`). Viungo vingine (`javascript:`, `http://`, `//`) vinakataliwa.
- Picha ya nyuma (hiari, inahitaji R2; bila R2 tangazo linatumia rangi tu).
- Mpangilio (0 = kwanza) na tarehe ya kuisha (hiari; linaondoka lenyewe).
- Unaweza kuhariri, kuzima/kuwasha, na kufuta. Kila mbofyo unahesabiwa (unaonekana kwenye orodha). Hatua zote zinaingia kwenye Kumbukumbu.

Kubofya tangazo kunapitia `/tangazo/<id>` (kuhesabu) kisha kumpeleka mtumiaji kwenye kiungo. Hadi matangazo 10 yanaonyeshwa kwa wakati mmoja. Jedwali jipya (`banners`) linatengenezwa lenyewe app ikianza.

### Matangazo: kuchagua kiungo bila kunakili
Kwenye fomu ya tangazo, orodha ya "Kinapeleka wapi" sasa ina makundi: **Kurasa**, **Kundi za market**, **Bidhaa maalum** (40 za hivi karibuni zilizo wazi) na **Mikeka maalum** (40 ya hivi karibuni). Kiungo cha mkono bado kinapatikana kwa tovuti za nje au kurasa nyingine.

### Ukurasa wa nyumbani: umesafishwa
Kadi ya "Karibu Jamvi" na vigae vya Jamvi/Market/Pochi/Wasifu vimeondolewa (vipo kwenye menyu ya chini). Juu kunabaki matangazo, kisha mikeka ya hivi karibuni na bidhaa za market. Mgeni asiyeingia anaona vitufe vya "Jisajili" na "Ingia" tu. Maandishi ya matangazo yamepewa kivuli na giza la chini ili yasomeke hata kwenye picha nyeupe.

## Mkeka wa mechi nyingi (kapu la mechi)
Mtabiri sasa anaweza kuunda mkeka wenye mechi zaidi ya moja (hadi 10, `MAX_SLIP_LEGS`).

**Jinsi ya kuweka:** Jamvi → Weka mkeka → chagua mechi → chagua chaguo → **Ongeza kwenye mkeka** → rudia kwa mechi nyingine → **Kamilisha mkeka**. Kwenye kukamilisha unachagua kampuni ya kubashiri: zinaonyeshwa kampuni zenye mechi ZOTE tu, kila moja na odds jumla (odds za mechi zimezidishwa). Kisha unaweka bei na maelezo. Mkeka wa mechi moja unafanya kazi vilevile (kapu lenye mechi 1).

**Sheria:**
- Mechi moja kwa kila mechi halisi kwenye mkeka (kuchagua tena kunabadilisha chaguo la zamani).
- Mechi iliyoanza au isiyo na odds tena inaondolewa kwenye kapu wakati wa kukamilisha.
- Mkeka unafungwa kwa wanunuzi mechi ya KWANZA ikianza; chaguo zinafichwa kwa asiyenunua (mechi zinaonekana).
- Hukumu ni ya kiotomatiki: mechi moja ikipoteza, mkeka umepoteza; zote zikishinda, umeshinda. Mechi iliyoahirishwa/kufutwa inahesabiwa kama odds 1 (odds jumla zinarekebishwa); zote zikibatilishwa, mkeka unabatilishwa na wanunuzi wanarudishiwa coin.
- Mtabiri hawezi kuweka matokeo ya mkeka huu kwa mkono (admin tu).
- Majedwali: `tip_legs` (jipya) na safu `tips.legs`; vinatengenezwa lenyewe baada ya Redeploy.

### Marekebisho ya mpangilio
- Ukurasa haupanuki tena nje ya skrini (kijachini cha kadi ya mkeka kinashuka mstari, gridi za bidhaa zimezuiwa kupanuka na picha pana).

### Kosa la "internal error" kwenye baadhi ya mechi (limerekebishwa)
Odds halisi za API zina masoko mengine yenye thamani za namba au tupu; msimbo ulijaribu kuzisoma kama maandishi na kuvunja ukurasa wa mechi zenye odds (mechi zisizo na odds, kama za Tanzania, zilifunguka). Sasa thamani zisizotarajiwa zinarukwa, na hitilafu yoyote ya kusoma odds inaonyesha ujumbe badala ya ukurasa wa kosa.

## Orodha ya mechi iliyopangwa (kuweka mkeka kwa urahisi)
Ukurasa wa "Weka mkeka" sasa umepangwa:
- **Tabo za siku** juu (Leo, Kesho, …) zenye idadi ya mechi; inafunguka siku ya kwanza yenye mechi.
- **Tabo za ligi** za siku hiyo (Ligi Kuu Tanzania na ligi ulizoweka kwenye `FOOTBALL_LEAGUES` zinakuja kwanza, kwa mpangilio huo huo), ukibonyeza moja unaona ligi hiyo tu.
- Mechi zimekundikwa chini ya kila ligi, saa ya kuanza kushoto na timu mbili chini ya nyingine; mechi uliyoichagua kwenye mkeka inaonyesha "Imechaguliwa".
- **Kutafuta** (timu au ligi) kunatafuta siku zote.

## Mkeka kujifunga kiotomatiki + kaunta
Ili mtu asinunue mkeka uliopitwa na wakati:
- Mkeka **unajifunga dakika 10 kabla ya mechi ya kwanza kuanza** (`LOCK_MINUTES_BEFORE`, chaguo-msingi 10). Baada ya hapo kitufe cha kununua kinatoweka, na seva inakataa ununuzi hata ukijaribu kwa nguvu. Mkeka wa mechi nyingi unafuata mechi ya KWANZA.
- **Dakika 30 kabla ya kufungwa** (`COUNTDOWN_MINUTES`) kaunta ya kuhesabu inaanza (mfano 20:00 → 00:00), kwenye kadi ya mkeka na kwenye ukurasa wa mkeka; ndani ya dakika 2 inabadilika rangi nyekundu. Kaunta ikifika sifuri ukurasa unajisasisha na kuonyesha "umefungwa". Kaunta inatumia muda uliobaki uliotumwa na seva, si saa ya simu, kwa hiyo saa isiyo sahihi ya simu haidanganyi.
- Mkeka mpya lazima uwe wa mechi inayoanza angalau dakika 15 mbele (10 za kufunga + 5), vinginevyo ungejifunga mara moja.
- Hali ya "Inasubiri matokeo" sasa inaanza wakati wa kufungwa (si mechi ikianza).

## Odds zilizopangwa kama kampuni za kubashiri
Ukurasa wa mechi sasa unaonyesha odds kama vitufe vya kugusa, si orodha ndefu:
- **Matokeo ya mchezo:** vitufe vitatu vya mstari mmoja (Nyumbani, Sare, Ugenini).
- **Nafasi mbili:** 1X, 12, X2. **Timu zote kufunga:** Ndiyo / Hapana.
- **Jumla ya magoli:** jedwali la mistari (0.5, 1.5, 2.5 …) lenye Zaidi na Chini kando kwa kando.
- Kugusa odds kunaiongeza moja kwa moja kwenye mkeka (hatua moja, si mbili); chaguo lililochaguliwa linaonekana kwa rangi. Odds bora zinaonyeshwa; kampuni unaichagua mwishoni kwenye "Kamilisha mkeka".

## Mechi ikihamishwa saa
Usasishaji wa mechi ukigundua saa ya mechi imebadilika, mikeka iliyo wazi yenye mechi hiyo inafuata saa mpya (saa ya kufunga inabadilika, na kwa mkeka wa mechi nyingi inafuata mechi ya mapema zaidi). Mtabiri anapata arifa.

## Menyu ya Usimamizi (badala ya tabo 9)
Tabo tisa za admin zilisogezwa kando kwenye simu. Sasa kuna kitufe kimoja kinachoonyesha sehemu uliyopo (mfano "Matangazo ▾"); ukibonyeza kinafunguka kisanduku cha menyu chenye ikoni na jina la kila sehemu (Muhtasari, Watumiaji, Mikeka, Bidhaa, Maagizo, Mechi, Matangazo, Ripoti, Kumbukumbu). Sehemu ya sasa imeangaziwa; kubonyeza nje au Esc kunafunga.

## Marekebisho ya mpangilio wa app nzima
- **Menyu ya kuchagua** (`templates/_menu.html`) imetumika popote palipokuwa na tabo nyingi: Usimamizi (sehemu 9), Market (kundi la bidhaa, lenye ikoni za kila kundi), Jamvi (Zote / Zinazosubiri / Zilizoshinda / Zilizopoteza) na Weka mkeka (ligi za siku). Kila moja inaonyesha chaguo la sasa kwenye kitufe, na ikifunguka inaonyesha orodha yenye ikoni (na idadi pale inapofaa).
- Kitufe cha "Tafuta" kinakaa katikati ya kisanduku cha kutafuta; maandishi ya Market hayakatwi tena.
- Kurasa za Ujumbe na Arifa zina ikoni kwenye kichwa kama kurasa nyingine; hali tupu za Viwango na Mtabiri zimepangwa kwa kisanduku kimoja.
- Kitufe cha "Choose File" kinafuata rangi za mandhari (mwanga na giza).
- Nimekagua kurasa kuu kwa picha za simu (mwanga na giza), ikiwemo admin.

## Wasifu, kuhariri wasifu na mipangilio
- **Wasifu** (`/wasifu`): picha, jina, `@jina_la_mtumiaji`, maelezo mafupi, mahali, takwimu (coin, mikeka, ushindi), vitufe vya **Hariri wasifu** na **Mipangilio**, njia za mkato (Pochi, Mikeka yangu, Maagizo, Ujumbe, Arifa, Usimamizi kwa admin), na taarifa za akaunti.
- **Hariri wasifu** (`/wasifu/hariri`): kubadilisha picha (au kuiondoa), jina la kuonyesha, "Kuhusu mimi" (herufi 160) na mahali. Maelezo na mahali vinaonekana pia kwenye wasifu wa umma wa mtabiri. **Jina la mtumiaji halibadiliki** kwa makusudi: linatumika kwenye viungo na kwenye `ADMIN_USERNAMES`, kwa hiyo kuliruhusu kubadilika kungeweza kuruhusu mtu kuchukua jina la admin.
- **Mipangilio** (`/wasifu/mipangilio`): **Mwonekano** (Mfumo / Mwanga / Giza, unahifadhiwa kwenye kifaa), **Faragha** (kuruhusu au kuzima ujumbe mpya), **Waliozuiwa** (orodha na kuondoa kizuizi), kubadilisha **nenosiri**, viungo vya Masharti na Faragha, na kutoka kwenye akaunti.
- Safu mpya kwenye `users`: `bio`, `location`, `allow_messages` (zinatengenezwa lenyewe baada ya Redeploy).
- Bado hakuna: kufuta akaunti, kubadilisha barua pepe/simu (zinahitaji uthibitisho, ulioahirishwa).

## Nenosiri likibadilika, vifaa vingine vinatolewa
Ukibadilisha nenosiri kwenye Mipangilio, vikao vya vifaa vingine vyote vinafungwa mara moja (mtu mwingine akiwa ameingia kwa akaunti yako atatakiwa kuingia upya). Kifaa ulichotumia kubadilisha kinabaki ndani. Ndani yake kuna alama (`pv`) inayotokana na nenosiri la sasa; `load_user` inailinganisha kila ombi.

## Orodha ya mikeka iliyochelewa kuhukumiwa (Usimamizi → Mechi)
Orodha ya "Mikeka inayosubiri hukumu" sasa inaonyesha mikeka yote iliyo wazi ambayo saa yake ya kuanza imepita: ya mechi halisi, ya mechi nyingi (inaonyesha "Mechi N") na ya mkono yenye saa ("Wa mkono"). Mikeka ya mkono haihukumiwi kiotomatiki; fungua mkeka na mtabiri aweke matokeo, au usimamizi uamue.

## Kusimamisha akaunti ya muuzaji
Admin akimsimamisha mtumiaji, maagizo yote ya market yaliyo wazi ya muuzaji huyo (yaliyolipwa, yaliyowasilishwa au yenye mgogoro) yanafutwa na wanunuzi wanarudishiwa coin zao zote mara moja (wanapata arifa), na bidhaa zake zilizo hewani zinafichwa. Kumwasha tena hakurudishi bidhaa; ziweke tena mwenyewe. Maagizo ambapo aliyesimamishwa ni mnunuzi hayaguswi: muuzaji anaweza kukamilisha, au admin aamue.

## Mikeka ya mkono iliyosahaulika
Mkeka wa mkono wenye saa, ambao mtabiri hakuweka matokeo kwa siku 14 baada ya saa hiyo, unabatilishwa na cron ya kila siku (`/cron/release`), na wanunuzi wanarudishiwa coin zote (muuzaji anakatwa alichopokea kadiri salio lake linavyoruhusu). Mikeka ya mechi halisi na ya mechi nyingi tayari ilikuwa inabatilishwa kiotomatiki baada ya siku 7 bila matokeo.

## Kuzuia kubahatisha nenosiri (sasa kwenye database)
Majaribio 5 yasiyo sahihi ndani ya dakika 10 (kwa kila kifaa/anwani na jina la kuingia, na pia kwa kubadilisha nenosiri) yanafunga kuingia kwa muda. Awali hesabu ilikaa kwenye kumbukumbu ya app, jambo ambalo kwenye Vercel halifanyi kazi vizuri kwa sababu kila nakala ya app ina kumbukumbu yake; sasa inahifadhiwa kwenye jedwali `kv` (ufunguo unaoanza na `fail|`, anwani ikiwa imefichwa kwa hash), kwa hiyo kikomo kinashikilia kila nakala. Database ikishindwa, inarudi kwenye kumbukumbu ili kuingia kusisimame.

## Msaada (maombi ya msaada kwa admin)
- **Kwa mtumiaji** (`/msaada`, kiungo kiko kwenye Wasifu → Mipangilio → Taarifa): maswali ya mara kwa mara (yanayofunguka), fomu ya kutuma ombi (aina, kichwa, maelezo hadi herufi 1500) na orodha ya "Maombi yangu" yenye hali (Linasubiri / Limejibiwa / Limefungwa). Kila ombi lina ukurasa wake (`/msaada/<id>`) unaoonyesha jibu; ni mwenye ombi tu anayeliona.
- **Mgeni** (ambaye hajaingia, mfano amesahau nenosiri) anaweza kutuma ombi akiweka namba ya simu au barua pepe; hapati arifa, kwa hiyo admin anamjibu kupitia mawasiliano hayo.
- **Kikomo:** maombi 3 kwa saa (kwa mtumiaji, au kwa anwani/mawasiliano kwa mgeni) ili kuzuia kero.
- **Admin** (Usimamizi → Msaada): orodha yenye vichujio (Yanayosubiri, Yaliyojibiwa, Yaliyofungwa, Yote), ukurasa wa ombi lenye taarifa za mtumaji, fomu ya jibu (na chaguo la kufunga), na "Funga bila kujibu". Admin wote wanapata arifa ombi jipya likiingia; mtumiaji anapata arifa akijibiwa; dashibodi inaonyesha idadi ya yanayosubiri. Kila jibu na kufunga vinaandikwa kwenye Kumbukumbu.
- Jedwali jipya `support_tickets` linatengenezwa lenyewe baada ya Redeploy.

## Kusahau nenosiri: kiungo cha mara moja kutoka kwa admin
Kurejesha nenosiri kwa barua pepe/SMS bado hakujawashwa (kunahitaji uthibitisho wa simu/barua pepe, ulioahirishwa). Kwa sasa njia ni hii:
1. Mtumiaji anatuma ombi kupitia **Msaada** (`/msaada`) akiweka namba ya simu au barua pepe aliyojisajili nayo.
2. Admin anamthibitisha (mfano kwa kumpigia namba hiyo), kisha anaenda **Usimamizi → Watumiaji** na kubonyeza **Kiungo cha nenosiri** kwa mtumiaji huyo. Ukurasa unaonyesha kiungo (`/weka-nenosiri/<token>`) mara moja tu, chenye kitufe cha kukinakili.
3. Admin anamtumia mtumiaji kiungo; mtumiaji anaweka nenosiri jipya (herufi 8+), kinaisha kutumika, na anaelekezwa kuingia.
- Kiungo kinafanya kazi **mara moja tu** na kinaisha baada ya **saa 24**; kutengeneza kipya kunabatilisha cha awali.
- Token inahifadhiwa kwa hash (si wazi) kwenye jedwali `password_resets`; kila kutengeneza kunaandikwa kwenye Kumbukumbu.
- Haiwezekani kwa akaunti za admin (wanabadilisha nenosiri kupitia Mipangilio), ili admin mmoja asiweze kuteka akaunti ya mwingine.
- Nenosiri likiwekwa, vikao vyote vya zamani vya akaunti vinafungwa na mtumiaji anapata arifa. Kubahatisha token kunazuiwa (majaribio 5 yasiyo sahihi kwa dakika 10 kwa kila anwani).

## Kutafuta kwenye Ujumbe
Ukurasa wa Ujumbe una kisanduku cha kutafuta: unaweza kutafuta mazungumzo yaliyopo kwa jina, `@jina` au maneno ya ujumbe wa mwisho, na pia kupata mtu mpya (jina la mtumiaji au jina la kuonyesha, herufi 2+) kisha kubonyeza "Anza mazungumzo na". Hautaonekana wewe mwenyewe, wala watumiaji waliosimamishwa, wala wale ambao tayari una mazungumzo nao.

## Kuondoa mazungumzo kwenye orodha yako
Kwenye ukurasa wa mazungumzo kuna kitufe cha **Ondoa**. Kinaficha mazungumzo na historia yake kwako tu; mwenzako anabaki na nakala yake kamili. Akitumia ujumbe mpya, mazungumzo yanarudi kwenye orodha yako yakiwa na ujumbe mpya tu (ya zamani hayarudi). Ujumbe ambao haujasomwa kwenye mazungumzo hayo unahesabiwa kama umesomwa unapoondoa. Hii ni kuficha, si kufuta: ujumbe unabaki kwenye database kwa ajili ya ripoti na usimamizi. Jedwali jipya: `conv_hides`.

## Kufuata watabiri
- Kwenye wasifu wa mtabiri (`/jamvi/mtabiri/<jina>`) kuna kitufe cha **Fuata** / **Unamfuata** (bonyeza tena kuacha) na idadi ya wafuasi. Huwezi kujifuata, wala kumfuata aliyesimamishwa.
- Mtabiri akiweka mkeka mpya (wa mechi moja, mechi nyingi au wa mkono), kila mfuasi anapata arifa "X ameweka mkeka mpya: …" inayopeleka kwenye mkeka. Arifa inaandikwa ndani ya muamala uleule wa kuweka mkeka, kwa hiyo haipotei wala haiwezi kuwa ya mkeka usiopo.
- **Ninaowafuata** (`/jamvi/ninaowafuata`, kutoka Wasifu → Njia za mkato): orodha ya watabiri unaowafuata (na idadi ya mikeka yao) na mikeka yao mipya.
- Jedwali jipya `follows` linatengenezwa lenyewe baada ya Redeploy.

## Kurasa za orodha ndefu ("Mapya zaidi" / "Za zamani zaidi")
Jamvi na Market zilikuwa na kurasa tayari. Sasa orodha zote za Usimamizi (Watumiaji, Mikeka, Bidhaa, Maagizo, Ripoti, Msaada, Kumbukumbu; vitu 50 kwa ukurasa) na wasifu wa mtabiri (mikeka 20 kwa ukurasa) zina vitufe vya kurasa, kwa hiyo vitu vya zamani vinafikiwa. Vichujio vya sasa (hali, utafutaji) vinabaki ukihama ukurasa. Kimeundwa kama kifaa kimoja: `templates/_pager.html` na `page_url()` ya `app.py`; ukurasa usio sahihi (`?ukurasa=abc`) unachukuliwa kama wa kwanza.

## Kupenda (kidole gumba) na Vipendwa
- Alama ya kupenda sasa ni **kidole gumba** (SVG mpya `thumb` na `thumb-on` kwenye `_icons.html`), si moyo. Ukipenda, kinajaa rangi ya kuu ya app. Moyo haupo tena popote.
- Unaweza kupenda **mikeka** na pia **bidhaa za market** (bonyeza tena kuondoa). Kadi ya bidhaa inaonyesha idadi ya waliopenda.
- **Vipendwa** (`/wasifu/vipendwa`, kutoka Wasifu → Njia za mkato): tabo mbili, Mikeka na Bidhaa, zenye kurasa. Bidhaa zilizofichwa haziorodheshwi.
- Majedwali mapya: `product_likes` (na faharasa ya `tip_likes` kwa mtumiaji); yanatengenezwa yenyewe baada ya Redeploy.

## Marekebisho ya mpangilio wa app nzima
Nimepitia kurasa zote 34 (mtumiaji, mgeni na admin) kwa picha za simu na kurekebisha:
- Fomu za kutafuta (Ujumbe, Watumiaji, Ligi): kitufe sasa kinalingana na kisanduku, si na kichwa juu yake.
- Tabo ndefu za admin (Maagizo, Ripoti, Msaada) zina kivuli kulia kuonyesha kuna zaidi ya kuteleza.
- Kadi ya mkeka: ligi na tarehe zinapangwa vizuri bila kukatika katikati.
- Kumbukumbu za admin zinaonyesha vitendo kwa Kiswahili ("Alibatilisha mkeka") badala ya majina ya ndani; hali ya bidhaa kwenye admin inasomeka "Hewani".
- Kila kisanduku cha nenosiri kina kitufe cha **Onyesha/Ficha**.

## Ukaguzi wa hali ya mwanga na skrini ya kompyuta
Nimekagua kurasa kuu kwa hali ya **mwanga** (simu) na kwa **skrini ya kompyuta** (giza na mwanga, upana 1280). Hali ya mwanga ilikuwa sawa. Kwenye kompyuta, kurasa za maudhui membamba (Wasifu, Mipangilio, Pochi, Ujumbe, Arifa, Msaada, mkeka mmoja, bidhaa moja, fomu za kuweka, n.k.) sasa zinakaa katikati kwa upana wa juu 700px (darasa `narrow` kupitia `{% block page_class %}` ya `base.html`) badala ya kunyooka ukingo hadi ukingo; orodha za kadi (Jamvi, Market, Admin) zinabaki pana. Kadi ya mkeka inaonyesha ligi na tarehe kwenye mistari miwili safi.

## Usimamizi: muundo mpya (admin)
- **Menyu:** kwenye kompyuta ni **safu ya pembeni** (inabaki juu unaposogeza); kwenye simu ni **tabo zinazoteleza** zenye ikoni. Sehemu zimepangwa kwa umuhimu: Muhtasari, Maagizo, Ripoti, Msaada, kisha Watumiaji, Mikeka, Bidhaa, Mechi, Matangazo, Kumbukumbu. Maagizo yenye mapingamizi, Ripoti wazi na Msaada unaosubiri vina **kitone chekundu chenye idadi**.
- **Muhtasari:** kadi tatu za tahadhari (nyekundu kukiwa na kinachosubiri, kijani kukiwa hakuna), vigae vinne (watumiaji, mikeka, bidhaa, maagizo wazi), coin (kwenye pochi, zinazoshikiliwa, jumla), watumiaji wapya 5, mapingamizi na shughuli 8 za mwisho.
- **Kichwa cha kila ukurasa** sasa ni jina la sehemu ("Watumiaji", "Maagizo"...) na maelezo mafupi chini yake, si "Usimamizi" kila mahali.
- **Msingi mmoja:** kurasa zote za admin zinarithi `templates/admin_base.html` (menyu ni `_admin_nav.html`, orodha ya sehemu iko hapo mara moja tu). Ukurasa mpya wa admin: `{% extends "admin_base.html" %}` na `{% block admin_sec %}jina{% endblock %}`, `{% block admin_sub %}…{% endblock %}`, `{% block admin %}…{% endblock %}`. Idadi za vitone zinatoka `admin.py` (`_admin_counts`).
