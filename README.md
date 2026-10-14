# M1 · Vides pārbaude un API līgums

Šī repozitorija ir FITA 1. moduļa obligātajam vides pārbaudes uzdevumam **A0** un izvēles uzdevumam **A1**. Visi piemēra dati ir sintētiski; Ezermalas novada pašvaldība un OMD reģistrs ir izdomāti.

## A0 · Vides pārbaude

1. Izveido vai apstiprini savu personīgo GitHub kontu.
2. Izveido savu repozitoriju no šīs veidnes.
3. Atver repozitoriju GitHub Codespaces un sagaidi, līdz vide ir gatava.
4. Terminālī palaid `claude` un piesakies ar kursa Claude kontu.
5. Uzdod Claude jautājumu: `Explain what make test does`.
6. Saglabā Claude atbildi failā `setup/claude-answer.md`.
7. Palaid `make verify-setup`.
8. Izveido zaru `setup-ok`, veic komitu un nosūti zaru uz GitHub.
9. GitHub cilnē **Actions** pārliecinies, ka pārbaude ir zaļa.

Fails `setup/claude-answer.md` apstiprina, ka Claude Code pieteikšanās Codespace vidē ir izdevusies. Tukšs vai neesošs fails neizturēs pārbaudi.

Pašas veidnes CI izveido īslaicīgu atbildes failu tikai `mleitass/m1-setup-check`
izpildes vidē. No veidnes izveidotajās dalībnieku repozitorijās šis solis netiek
izpildīts, tāpēc dalībnieka atbildes fails joprojām ir obligāts.

## A1 · Līgums pirms koda (izvēles uzdevums)

Izlasi `tracker/CR-2.md` un papildini CR-2 daļu failā `docs/openapi.yaml`:

- dokumentē 5xx un noildzes uzvedību;
- pievieno pilnu `reasonCode` vērtību sarakstu;
- pievieno `PENDING_CHANNEL_CHECK` atbildes kanālu;
- nodrošini, ka katrai operācijai ir `400`, `404` un vismaz viena `5xx` atbilde;
- visām kļūdu atbildēm izmanto kopīgo `Error` shēmu ar `$ref`.

Pārbaudi rezultātu ar:

```bash
make lint-contract
```

Sākotnējā līguma versija šo pārbaudi neiztur apzināti. Uzdevums ir pabeigts, kad komanda beidzas veiksmīgi.

## CR-4 · Lietotāju konti (prototips)

Palaid `make run` un atver <http://localhost:8000/login>. Ir pieejamas lapas
`/login`, `/register`, `/password-reset` un `/welcome`, kā arī API operācijas
`/auth/*` (sk. `docs/openapi.yaml` un Swagger UI `/docs`).

- Lietotāji glabājas SQLite failā `data/users.db`; ceļu var mainīt ar `AUTH_DB_PATH`.
  Mape `data/` netiek komitēta.
- Paroles atjaunošanas saite netiek sūtīta pa e-pastu, bet tiek ierakstīta servera
  žurnālā (terminālī). Tas ir pieļaujams tikai lokālajam prototipam.

## CR-5 · Ezermalas CRM

Klientu attiecību sistēma iestādei: organizācijas, kontaktpersonas, mijiedarbības,
pieprasījumi un uzdevumi. Prasības: `docs/prasibas_arhitektura.md`, pieteikums
`tracker/CR-5.md`.

1. `make install` (vai `make install-dev`, lai palaistu arī pieejamības testu).
2. `make run` un atver <http://localhost:8000/>.
3. Sākumlapā izvēlies darbinieku. Mācību režīmā paroles nav; loma (darbinieks,
   vadītājs, administrators) nosaka tiesības. Pēc izvēles atveras kopsavilkums (F9).

- Dati glabājas `data/crm.db` (ceļu var mainīt ar `CRM_DB_PATH`). Pirmajā palaišanā tiek
  ievietoti izdomāti sākumdati: 25 darbinieki, 10 organizācijas, 20 kontakti,
  95 mijiedarbības, 43 pieprasījumi un 35 uzdevumi. Lai sāktu no jauna, izdzēs `data/crm.db`.
- MI-1 kopsavilkums: bez `ANTHROPIC_API_KEY` darbojas atslēgvārdu imitācija; ar atslēgu
  izmanto Claude (`claude-opus-5-5`).
- Pieejamības tests `tests/a11y_check.py` (axe-core + Playwright) tiek izlaists, ja
  Playwright vai Chromium nav uzstādīts.
- MI-2 klasifikācija un lēmums: `docs/mi2_klasifikacija.md`.

## Komandas

| Komanda | Nozīme |
|---|---|
| `make verify-setup` | Pārbauda Python, kursa pakotnes, Claude Code, saglabāto atbildi un smoke testus |
| `make test` | Palaiž visus `pytest` testus |
| `make lint-contract` | Validē OpenAPI dokumentu un kursa līguma noteikumus |
| `make run` | Palaiž prototipu uz porta 8000 (CR-4, CR-5) |
| `make install` / `make install-dev` | Uzstāda lietotnes / testu atkarības (CR-5) |
