---
id: CR-5
type: change-request
title: "Ezermalas CRM: organizācijas, kontakti, mijiedarbības, pieprasījumi un uzdevumi"
status: DRAFT
priority: high
reporter: "<loma, nevis vārds>"
owner: "@<github-lietotājvārds>"
contract: "docs/openapi.yaml · CRM HTML ekrāni (text/html) · docs/prasibas_arhitektura.md F1–F8, MI-1, MI-2, N1–N4"
depends_on: [CR-4]
exported: "<datums> · Ezermalas pieteikumu sistēma (simulācija)"
data_check: "Nav personas datu. Sākumdati (darbinieki, organizācijas, kontakti) ir izdomāti."
---

# CR-5 · Ezermalas CRM

> Noteikumi vienkāršoti mācību vajadzībām.

## Apraksts (description)

Iestāde ar ~25 darbiniekiem sadarbojas ar uzņēmumiem, NVO un pašvaldībām
(konsultācijas, semināri, pieprasījumi). Šobrīd dati ir Excel tabulās un
personīgajos e-pastos, un neviens nezina, kas ar ko pēdējo reizi runāja.
Vajadzīga viena klientu attiecību sistēma, kurā redzamas organizācijas, to
kontaktpersonas, saziņas vēsture, pieprasījumi un darbinieku uzdevumi.
Vadītājs redz kopainu, un sistēma atbilst piekļūstamības, VDAR un MI akta
prasībām. Pilnas prasības un konceptuālā arhitektūra:
`docs/prasibas_arhitektura.md` un `docs/image.png`.

## Pieņemšanas kritēriji (acceptance criteria)

### Lomas un sākumlapa (N3)

| # | Ievade | Sagaidāmais rezultāts |
|---|---|---|
| 1 | Atver sākumlapu | Saraksts ar darbiniekiem un viņu lomām; izvēle bez paroles (mācību režīms); izvēle saglabāta sesijā |
| 2 | Darbinieks atver organizāciju sarakstu | Redz visas organizācijas; savējās (kur ir atbildīgais) ir atzīmētas ar tekstu |
| 3 | Darbinieks atver citas organizācijas kartīti | Redz visu tikai lasīšanai; rediģēšanas pogu nav; POST uz rediģēšanu → 403 |
| 4 | Vadītājs | Var rediģēt visas organizācijas un redz F7 pārskatu |
| 5 | Administrators | Var mainīt darbinieku lomas, dzēst kontaktpersonas (N2) un skatīt piekļuves žurnālu |
| 6 | Darbinieks atver F7 vai administratora lapas | 403 |
| 7 | Katra lapa | Kājenē redzama norāde "Mācību režīms, nav pieteikšanās" |

### Organizācijas (F1)

| # | Ievade | Sagaidāmais rezultāts |
|---|---|---|
| 8 | Jauna organizācija: nosaukums, reģ. nr. (11 cipari), veids, atbildīgais darbinieks | Saglabāta; POST → redirect → GET uz kartīti |
| 9 | Reģ. nr. nav 11 cipari | Forma tiek parādīta atkārtoti ar ievadītajām vērtībām, kļūdas teksts pie lauka, saistīts ar `aria-describedby`, fokuss uz kļūdu kopsavilkumu |
| 10 | Reģ. nr. jau eksistē | Kļūda pie lauka "Organizācija ar šo reģ. nr. jau ir reģistrēta" |
| 11 | Veids | Tikai uzņēmums / NVO / pašvaldība |
| 12 | Katram laukam | Redzams `<label>`; obligātie lauki atzīmēti ar tekstu, ne tikai ar zvaigznīti |

### Kontaktpersonas (F2, N2)

| # | Ievade | Sagaidāmais rezultāts |
|---|---|---|
| 13 | Jauns kontakts: vārds, amats, e-pasts, tālrunis, saziņas pamats, datums | Saglabāts pie organizācijas; citu personas datu lauku nav |
| 14 | Tālrunis `+37120000000` vai `20000000` | Pieņemts; cits formāts → kļūda pie lauka |
| 15 | Nederīgs e-pasts | Kļūda pie lauka |
| 16 | Pēdējā saziņa ar kontaktu (mijiedarbība vai saziņas datums) senāka par 2 gadiem | Kontakts administratoram izcelts sarakstā "Beidzies glabāšanas termiņš" ar tekstu; automātiski netiek dzēsts |
| 17 | Administrators dzēš kontaktu | Kontakts dzēsts; mijiedarbībās vārds aizstāts ar "Dzēsta kontaktpersona"; piekļuves žurnālā ieraksts par dzēšanu bez dzēstās personas datiem |

### Mijiedarbības (F3, MI-1)

| # | Ievade | Sagaidāmais rezultāts |
|---|---|---|
| 18 | Jauna mijiedarbība: veids (zvans / e-pasts / sanāksme), datums, dalībnieki, kopsavilkums, nākamais solis | Saglabāta; redzama organizācijas kartītē hronoloģiski, jaunākā augšā |
| 19 | Brīvs teksts → "Ģenerēt kopsavilkumu" | Forma tiek atgriezta ar ≤ 3 teikumu kopsavilkumu un nākamā soļa ieteikumu, marķētiem "Ģenerēts ar MI"; nekas vēl nav saglabāts |
| 20 | Darbinieks rediģē un apstiprina | Saglabāts; žurnālā redzama atzīme "Ģenerēts ar MI, apstiprināja <darbinieks>" |
| 21 | Nav `ANTHROPIC_API_KEY` | Izmanto atslēgvārdu imitāciju ar to pašu funkcijas līgumu `kopsavilkums(teksts) → (kopsavilkums, solis)` |
| 22 | Ir `ANTHROPIC_API_KEY` | Izmanto Claude API; kļūdas vai noildzes gadījumā → imitācija un paziņojums lietotājam |

### Pieprasījumi (F4)

| # | Ievade | Sagaidāmais rezultāts |
|---|---|---|
| 23 | Jauns pieprasījums | Statuss "Jauns"; termiņš = izveides datums + 30 dienas; termiņu nevar mainīt |
| 24 | Statusa maiņa | Tikai Jauns → Darbā → Atbildēts |
| 25 | Termiņš pagājis un statuss nav "Atbildēts" | Sarakstā un kartītē teksts "Kavēts" (ne tikai krāsa) |

### Uzdevumi (F5)

| # | Ievade | Sagaidāmais rezultāts |
|---|---|---|
| 26 | Jauns uzdevums | Obligāti saistīts ar organizāciju vai pieprasījumu; ir izpildītājs un termiņš |
| 27 | "Mani uzdevumi šodien" | Izvēlētā darbinieka neizpildītie uzdevumi, kuru termiņš ir šodien vai jau pagājis (❓) |
| 28 | "Atzīmēt kā izpildītu" | Uzdevums pazūd no saraksta; parastā formā (POST → redirect → GET) |

### Meklēšana (F6)

| # | Ievade | Sagaidāmais rezultāts |
|---|---|---|
| 29 | Viens meklēšanas lauks | Meklē organizācijās (nosaukums, reģ. nr.), kontaktos (vārds, e-pasts) un pieprasījumos |
| 30 | Rezultāti | Tabula ar `<caption>` un `<th scope>`; kolonna "Tips" |
| 31 | Nav rezultātu | Teksts ar meklēto vārdu un saiti "Izveidot organizāciju" |

### Pārskats (F7)

| # | Ievade | Sagaidāmais rezultāts |
|---|---|---|
| 32 | Vadītājs izvēlas periodu (no–līdz) | Aktivitāte pa darbiniekiem, kavētie pieprasījumi, aktīvākās organizācijas |
| 33 | Diagramma | Servera ģenerēts SVG ar `<title>`/`<desc>`; tieši zem tās tabula ar tiem pašiem datiem |
| 34 | "No" ir vēlāk par "līdz" | Kļūda pie lauka |

### Piekļūstamība (F8, N1)

| # | Ievade | Sagaidāmais rezultāts |
|---|---|---|
| 35 | Katra lapa | Skip-link, orientieri (`header`, `nav`, `main`, `footer`), redzams fokuss; strādā bez JavaScript |
| 36 | `tests/a11y_check.py` (axe-core + Playwright) galvenajā ceļā | Nav critical/serious pārkāpumu; ja pārlūka nav, tests tiek izlaists (CI paliek zaļš) |
| 37 | Galvenais ceļš ar tastatūru un 200 % mērogā, 320 px platumā | Viss izpildāms; nav horizontālās ritināšanas |
| 38 | `/pieklustamiba` | Paziņojums ar reāliem testu atradumiem un datumu; saite kājenē katrā lapā |

### Piekļuves žurnāls (N2)

| # | Ievade | Sagaidāmais rezultāts |
|---|---|---|
| 39 | Organizācijas kartītes atvēršana, jebkura izmaiņa | Ieraksts: kas, ko, kad, darbība (skatīja / mainīja / dzēsa) |
| 40 | Administrators atver žurnālu | Saraksts, filtrējams pēc darbinieka un organizācijas |

### MI-2

| # | Ievade | Sagaidāmais rezultāts |
|---|---|---|
| 41 | `docs/mi2_klasifikacija.md` | MI akta riska klasifikācija: kas tiek vērtēts, sekas organizācijai/personai, riska klase, lēmums "nebūvēt" ar pamatojumu. Kods netiek veidots |

### Tehniskie (N4)

| # | Ievade | Sagaidāmais rezultāts |
|---|---|---|
| 42 | Sākumdati | 25 darbinieki (vismaz 1 vadītājs, 1 administrators), 10 organizācijas, 20 kontakti, 30 mijiedarbības, izdomāti |
| 43 | `docs/openapi.yaml` | Apraksta CRM maršrutus (text/html); `make lint-contract` jaunajām operācijām bez kļūdām (❓) |
| 44 | `make test` | Iziet; CR-4 testi turpina iziet |

## Precizējumi (clarifications)

| Jautājums | Atbilde | Kas atbildēja, kad |
|---|---|---|
| Vai sadalīt vairākos pieteikumos? | Nē, viena sistēma, viens pieteikums | <loma>, 2026-10-14 |
| Tehnoloģija? | FastAPI + Jinja2 (atkāpe no N4 "Flask"), SQLite | <loma>, 2026-10-14 |
| Pieteikšanās? | Mācību režīms bez parolēm (N3); CR-4 lapas paliek pieejamas paralēli | <loma>, 2026-10-14 |
| Lomas? | 3: darbinieks, vadītājs, administrators | <loma>, 2026-10-14 |
| Ko darbinieks redz par citām organizācijām? | Visu, tikai lasīt | <loma>, 2026-10-14 |
| Kontaktu glabāšanas termiņš? | 2 gadi pēc pēdējās saziņas; administrators dzēš manuāli | <loma>, 2026-10-14 |
| Dzēšana pēc pieprasījuma? | Dzēst kontaktu, anonimizēt mijiedarbībās | <loma>, 2026-10-14 |
| Pieprasījuma termiņš? | Fiksēts, 30 dienas | <loma>, 2026-10-14 |
| Reģ. nr. un tālruņa formāts? | LV: 11 cipari; +371 un 8 cipari vai 8 cipari | <loma>, 2026-10-14 |
| MI-1 nodrošinātājs? | Imitācija pēc noklusējuma, Claude, ja ir API atslēga | <loma>, 2026-10-14 |
| MI-2? | Tikai klasifikācijas dokuments, lēmums "nebūvēt" | <loma>, 2026-10-14 |
| Pieejamības tests? | axe-core + Playwright kā dev atkarība | <loma>, 2026-10-14 |
| F7 periods un diagramma? | Izvēlēts periods; servera SVG + tabula | <loma>, 2026-10-14 |
| Vai CRM maršruti ir līgumā? | Jā | <loma>, 2026-10-14 |
| Sākumdati, darbinieki? | 25 | <loma>, 2026-10-14 |
| Sākumlapā izvēlas darbinieku (loma no viņa ieraksta) |
| Kursa `make lint-contract` prasa visām 4xx/5xx atbildēm JSON `Error` shēmu, bet HTML ekrāni kļūdas rāda HTML. Kā aprakstīt? HTML kļūdu lapas + `application/json` `Error` alternatīva |
| Ko nozīmē "šodien" F5 sarakstā: tikai šodienas termiņš vai arī kavētie? |  abi, kavētie atzīmēti ar tekstu | |
| Vai MI-1 drīkst sūtīt mijiedarbību brīvo tekstu (var saturēt personas datus) Anthropic? | Jā, demo versijā tāpat tiks izmantoti tikai sintētiski dati | |

## Ārpus tvēruma (out of scope)

- Īsta autentifikācija CRM lomām (mācību režīms)
- E-pasta sūtīšana, atgādinājumi pa e-pastu vai paziņojumi
- E-pasta atbildes projekts (attēlā "COULD")
- MI-2 īstenošana
- Datu imports no Excel

## Komentāri (comments)

- 2026-10-14 · Jinja2 un Playwright nav kursa CI konteinera attēlā. Vajag `requirements.txt` / `requirements-dev.txt` un CI soli `pip install`, vai attēla atjaunošanu (to kontrolē kursa veidotājs).
- 2026-10-14 · Mācību režīmā jebkurš var izvēlēties administratora lomu. Sistēmā nedrīkst ievadīt īstus personas datus.
- 2026-10-14 · N4 paredz 1,5 h; pilns apjoms (44 kritēriji) šajā laikā nav reāls. Ieteicams prioritizēt F1–F3 + N1.
