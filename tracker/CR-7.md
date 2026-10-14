---
id: CR-7
type: defect
title: "Koda audita labojumi: drošība, VDAR, tāfele, pieejamība, testi"
status: DRAFT
priority: high
reporter: "<loma, nevis vārds>"
owner: "@<github-lietotājvārds>"
contract: "docs/openapi.yaml · /auth/register, /auth/login, /auth/password-reset/confirm (paroles garums), /uzdevumi/{taskId}/izpilditajs, /uzdevumi/{taskId}/izpildits, /uzdevumi/sadale, /pieklustamiba (POST), /admin/atsauksmes"
depends_on: [CR-4, CR-5, CR-6]
exported: "<datums> · Ezermalas pieteikumu sistēma (simulācija)"
data_check: "Nav personas datu. Piemēros izmantoti sākumdatu izdomātie vārdi."
---

# CR-7 · Koda audita labojumi

> Noteikumi vienkāršoti mācību vajadzībām.

## Apraksts (description)

Pēc CR-6 tika veikts pilns koda audits (četras daļas: CRM serveris, pieteikšanās un
infrastruktūra, lapas un JavaScript, testi un līgums). Atrasti 66 atradumi, no tiem
55 jālabo. Daļa ir drošības un VDAR kļūdas: pieteikšanās bloķēšanu varēja apiet,
paroles atjaunošanas saiti varēja novirzīt uz svešu domēnu, un kontaktpersonas dzēšana
neizdzēsa vārdu no visiem ierakstiem. Daļa ir nepareiza uzvedība (tāfele varēja rādīt
nesaglabātu nodošanu kā veiksmīgu) un pieejamības problēmas. CI nepalaida CR-4…CR-6
testus, tāpēc šīs kļūdas netika pamanītas.

Pilns atradumu saraksts ar failiem: `docs/audits-2026-10-14.md`.

Pēc audita tika veikta atkārtota piekļūstamības pārbaude pret Direktīvu (ES) 2016/2102,
MK noteikumiem Nr. 445 un EN 301 549 (V3.2.1 → WCAG 2.1 AA; papildus WCAG 2.2 AA, uz kuru
balstās V4.1.1). Eiropas Piekļūstamības akts (Direktīva 2019/882, Preču un pakalpojumu
piekļūstamības likums) attiecas uz uzņēmumu produktiem un pakalpojumiem, nevis uz iestādes
iekšējo sistēmu, tāpēc netiek piemērots. Atrasts: piekļūstamības paziņojumam trūka
obligāto sadaļu un atgriezeniskās saites mehānisma, pieteikšanās lapās nebija saites uz
paziņojumu, un pēc kļūdas fokuss pazuda.

Lietotājam redzamās izmaiņas: parole ne garāka par 1024 simboliem; jauna atsauksmju forma
piekļūstamības paziņojumā; administratoram jauna lapa „Piekļūstamības atsauksmes”.

## Pieņemšanas kritēriji (acceptance criteria)

### Drošība un VDAR

| # | Ievade | Sagaidāmais rezultāts |
|---|---|---|
| 1 | Vairāki paralēli pieteikšanās mēģinājumi ar nepareizu paroli vienam kontam | Konts tiek bloķēts kā pēc 3 secīgiem mēģinājumiem; arī pareiza parole pēc tam atgriež 401 (CR-4 #11) |
| 2 | Paralēli mēģinājumi | Paroles pārbaudes vienam kontam nenotiek vienlaikus (deterministisks tests) |
| 3 | `POST /auth/password-reset` ar `Host: evil.example` | Saite žurnālā sākas ar `PUBLIC_BASE_URL` (noklusējums `http://localhost:8000`), nevis ar `evil.example` |
| 4 | Parole garāka par 1024 simboliem reģistrācijā vai paroles maiņā | 400, lauks `password`, `TOO_LONG`; scrypt netiek izsaukts |
| 5 | Parole garāka par 1024 simboliem pieteikšanās laikā | 401 bez paroles pārbaudes |
| 6 | Nederīgs vai beidzies atjaunošanas marķieris | 400 `INVALID_OR_EXPIRED` pirms jaunās paroles jaukšanas |
| 7 | Atver atjaunošanas saiti pārlūkā | Marķieris pēc ielādes tiek izņemts no adreses joslas un vēstures |
| 8 | Administrators dzēš kontaktpersonu, kuras vārds minēts citas organizācijas mijiedarbībā, pieprasījuma temata/aprakstā vai uzdevuma nosaukumā | Visās vietās vārds aizstāts ar „Dzēsta kontaktpersona” (N2) |
| 9 | Administratora kopsavilkums | Glabāšanas termiņa skaits tiek aprēķināts bez kontaktpersonu datu nolasīšanas |
| 10 | Iestatīts `CRM_DB_PATH` | Lietotne izmanto šo ceļu arī tad, ja norādīts lietotāju DB ceļš; testi nekad neizmanto izstrādātāja vides mainīgos |

### Uzdevumu sadales tāfele (CR-6)

| # | Ievade | Sagaidāmais rezultāts |
|---|---|---|
| 11 | Darbinieka sīkdatne zudusi, vadītājs pārvelk kartīti | Serveris atbild 403 JSON; kartīte atgriežas, paziņojums ekrānlasītājam |
| 12 | Atbilde nav JSON vai ir pāradresācija | `board.js` to uzskata par neveiksmi un atgriež kartīti |
| 13 | Otra pārvietošana, kamēr pirmā vēl notiek | Netiek sākta; paziņojums „vēl tiek nodots” |
| 14 | Kartītes uzdevums jau izpildīts citā cilnē | Serveris atbild 400 `TASK_DONE`; kartīte tiek noņemta no tāfeles |
| 15 | Forma „Nodot” ar to pašu darbinieku | Bez JS: nav paziņojuma „Uzdevums nodots”; ar JS: paziņojums „jau ir šim darbiniekam” |
| 16 | Kartīte pārvietota uz nerādītu kolonnu | Skaitītāji uzreiz neskaita paslēpto kartīti |
| 17 | Ekrānlasītājs, pogu saraksts | Katra „Nodot citam darbiniekam” poga satur uzdevuma nosaukumu |

### CRM pareizība

| # | Ievade | Sagaidāmais rezultāts |
|---|---|---|
| 18 | Izpildītu uzdevumu atzīmē kā izpildītu vēlreiz | Izpildes datums nemainās, žurnālā nav jauna ieraksta |
| 19 | Izpilda uzdevumu, kas saistīts tikai ar pieprasījumu | Žurnāla ierakstā ir pieprasījuma organizācija |
| 20 | Jauns uzdevums ar organizāciju un citas organizācijas pieprasījumu | 400, kļūda pie lauka „Pieprasījums” |
| 21 | „Ģenerēt kopsavilkumu” ar piezīmēm > 8000 rakstzīmēm | 400 ar kļūdu pie piezīmēm (ne tikai saglabājot) |
| 22 | Kontaktpersona dzēsta, kamēr cits veido mijiedarbību ar to | Mijiedarbība saglabājas bez dzēstā dalībnieka, nav 500 |
| 23 | F9 „pēdējās 7 dienas” | Šodiena un 6 iepriekšējās dienas (ne 8) |
| 24 | Sākumdati | Darbiniekam 22 nav mijiedarbību, uzdevumu un organizāciju |

### Pieejamība un lapas

| # | Ievade | Sagaidāmais rezultāts |
|---|---|---|
| 25 | ≤ 768 px, `crm.js` neielādējas | Navigācija redzama (CR-6 #4) |
| 26 | Fokuss ar Tab iziet no atvērtas izvēlnes | Izvēlne aizveras (WCAG 2.4.11) |
| 27 | Saite uz enkuru vai fokuss zem „sticky” augšējās joslas | Elements nav aizsegts (WCAG 2.4.11) |
| 28 | 320 px, atver „Pievienot” | Izvēlne pilnībā ekrānā |
| 29 | `/uzdevumi/sadale` | Kolonnām nav liekas 36 px atstarpes |

### Piekļūstamība: Direktīva 2016/2102, MK noteikumi Nr. 445, EN 301 549

| # | Ievade | Sagaidāmais rezultāts |
|---|---|---|
| 35 | `/pieklustamiba` | Saturs pēc Lēmuma (ES) 2018/1523 parauga: apņemšanās ar atsauci uz MK noteikumiem Nr. 445; tvērums; atbilstības statuss (pilnībā / daļēji / neatbilst) pret EN 301 549; nepieejamais saturs pa kategorijām (neatbilstība, nesamērīgs slogs, ārpus tvēruma); sagatavošanas datums, metode (pašnovērtējums, VARAM vadlīnijas), pēdējās un nākamās pārskatīšanas datums (ne retāk kā reizi gadā) |
| 36 | Atgriezeniskās saites mehānisms | Forma `/pieklustamiba` darbojas bez pieteikšanās un bez JavaScript; apraksts obligāts (≤ 2000), lapa un e-pasts nav obligāti (VDAR minimizācija); kļūdas pie laukiem; atbildīgā kontakts norādīts |
| 37 | Sūdzību kārtība | Norādīta iespēja vērsties pie Tiesībsarga ar biroja kontaktiem |
| 38 | Administrators atver `/admin/atsauksmes` | Saraksts ar ziņojumiem; dzēšana pēc apstrādes ar ierakstu piekļuves žurnālā; citām lomām 403 |
| 39 | Pieteikšanās, reģistrācijas un paroles atjaunošanas lapas | Katrā lapā saite uz piekļūstamības paziņojumu (WCAG 3.2.6) |
| 40 | Pieteikšanās vai reģistrācijas forma ar kļūdu | Fokuss pāriet uz pirmo kļūdaino lauku vai kļūdas tekstu, nevis paliek uz `<body>` (WCAG 2.4.3); pēc paroles atjaunošanas pieprasījuma fokuss uz paziņojumu |
| 41 | axe-core visās lapās, ieskaitot pieteikšanās lapas un atsauksmes, gaišais un tumšais režīms | 0 pārkāpumu; tests pārbauda, ka lapa atgriež 200 (kļūdas lapa nedrīkst „iziet” axe pārbaudi) |
| 42 | WCAG 1.4.12: palielinātas teksta atstarpes visās galvenā ceļa lapās | Saturs netiek nogriezts, nav horizontālās ritināšanas |
| 43 | Tastatūra: no katras lapas ar Tab sasniedzama kājene | Nav tastatūras slazdu (WCAG 2.1.2) |

### Testi, līgums, CI

| # | Ievade | Sagaidāmais rezultāts |
|---|---|---|
| 30 | CI (push, PR) | Palaiž `make test` pirms `make verify-setup` |
| 31 | `A11Y_REQUIRED=1` un nav Chromium | Pieejamības testi krīt, nevis tiek klusi izlaisti; `make install-dev` uzstāda pārlūku ar `--with-deps` |
| 32 | Pārlūka tāfeles testi palaisti jebkurā secībā vai atkārtoti | Iziet (nav atkarīgi no iepriekšējā testa datiem) |
| 33 | `docs/openapi.yaml` | Paroles `maxLength: 1024`; `return_to` kā teksts ar rezerves vērtību; JSON/HTML noteikums un `TASK_DONE` aprakstīti; tukša kolonnu izvēle = noklusējums; `make lint-contract` jaunu kļūdu nav |
| 34 | `make test` | Iziet. Automātisks tests ir visiem kritērijiem, izņemot #7, #9, #12, #13, #16, #27, #29 (JS/CSS uzvedība un iekšējā vaicājuma forma), kas pārbaudīti koda pārskatā; tiem testu var pievienot vēlāk. Kritērijiem #35–#43 ir testi |

## Precizējumi (clarifications)

| Jautājums | Atbilde | Kas atbildēja, kad |
|---|---|---|
| Vai labot uzreiz bez pieteikuma? | Jā, labojumi veikti zarā `audits-2026-10-14`; šis pieteikums tos noformē | <loma>, 2026-10-14 |
| Vai mainīt CI darbplūsmu (kursa veidotāja fails)? | <neatbildēts> — ieteikums: jā, citādi testi CI netiek palaisti | |
| Vai paroles maksimums 1024 ir pieņemams? | <neatbildēts> — ieteikums: jā (aizsardzība pret slodzi; CR-4 maksimumu nenoteica) | |
| Pret kādiem avotiem pārbaudīt piekļūstamību? | Direktīva 2016/2102, MK noteikumi Nr. 445, Direktīva 2019/882 un Preču un pakalpojumu piekļūstamības likums, EN 301 549 V3.2.1 / V4.1.1 | <loma>, 2026-10-14 |
| ❓ Kāds ir īstais iestādes kontakts piekļūstamības jautājumiem? | <neatbildēts> — paziņojumā izmantots izdomāts `pieklustamiba@ezermala.example` | |
| ❓ Vai veikt manuālu pārbaudi ar ekrānlasītāju (NVDA)? | <neatbildēts> — bez tās statuss paliek „daļēji atbilst” | |

## Ārpus tvēruma (out of scope)

- Sesiju derīguma termiņš un sīkdatnes `Secure` / `max_age` (CR-4 lēmums lokālajam prototipam; jauns CR pirms publiskas izvietošanas)
- Lietotājvārdu atstarpju apstrāde (CR-4: „jebkuri simboli”)
- `Accept` q-vērtību pilna apstrāde
- Meklēšanas pārnešana uz SQL (SQLite `LIKE` neatbalsta latviešu burtu reģistru)
- Vārda locījumu atpazīšana, dzēšot kontaktpersonu
- `tools/lint_contract.py` izmaiņas (kursa rīks)
- Manuāla pārbaude ar ekrānlasītāju un ar lietotājiem (nepieciešama, lai statusu mainītu uz „pilnībā atbilst”)
- Padziļinātais izvērtējums (MK 445 26.2.2. apakšpunkts) un nesamērīgā sloga izvērtējums pēc VARAM vadlīnijām
- Testu fiksāciju apvienošana un CR-4 testu ātruma uzlabošana

## Komentāri (comments)

- 2026-10-14 · Audits: 4 meklētāji ar `code-review` skilu; katrs atradums pārbaudīts pirms labošanas. 66 atradumi, 55 izlaboti, 1 dublikāts, 10 nav laboti (sk. „Ārpus tvēruma” un `docs/audits-2026-10-14.md`).
- 2026-10-14 · `make test`: 282 testi iziet (pirms audita 228).
- 2026-10-14 · Atkārtotā piekļūstamības pārbaudē testa skripts atklāja vēl vienu kļūdu: `/admin/atsauksmes` atgrieza kļūdas lapu (veidnes mainīgais `items` sakrita ar navigācijas mainīgo), bet axe to neuzrādīja, jo kļūdas lapā pārkāpumu nav. Labots; pārlūka testi tagad pārbauda arī statusu 200.
- 2026-10-14 · Avoti paziņojuma saturam: Komisijas Īstenošanas lēmums (ES) 2018/1523 (paraugs), VARAM vadlīnijas, Tiesībsarga biroja kontakti (tiesibsargs.lv).
- 2026-10-14 · Jauns iestatījums `PUBLIC_BASE_URL`: jāiestata, ja lietotne nedarbojas uz `http://localhost:8000`.
- 2026-10-14 · Komitu nosaukumi zarā sākas ar „Audits:”; pirms PR tos var pārsaukt ar `CR-7:` prefiksu.
