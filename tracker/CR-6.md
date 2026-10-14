---
id: CR-6
type: change-request
title: "Ezermalas CRM: jauns izskats un uzdevumu sadales tāfele vadītājam"
status: DRAFT
priority: medium
reporter: "<loma, nevis vārds>"
owner: "@<github-lietotājvārds>"
contract: "docs/openapi.yaml · GET /uzdevumi/sadale, POST /uzdevumi/{taskId}/izpilditajs, esošie CRM maršruti bez izmaiņām"
depends_on: [CR-5]
exported: "<datums> · Ezermalas pieteikumu sistēma (simulācija)"
data_check: "Nav personas datu. docs/design_example.png ir trešās puses produkta ekrānuzņēmums; sk. komentārus."
---

# CR-6 · Ezermalas CRM: jauns izskats un uzdevumu sadales tāfele

> Noteikumi vienkāršoti mācību vajadzībām.

## Apraksts (description)

CRM darbojas, bet izskatās kā formu kopums, nevis darba rīks, ko atver katru rītu.
Vadītājs šobrīd nevar vienuviet redzēt, cik uzdevumu ir katram darbiniekam, un
pārdalīt tos, ja kāds ir pārslogots vai prombūtnē.

Vajag:

1. **Jaunu vizuālo identitāti visai lietotnei**: pastāvīga sānjosla ar galvenajām
   sadaļām, augšējā josla ar meklēšanu un ātro pievienošanu, blīvāks, vieglāk
   pārskatāms saturs. Struktūras iedvesma: `docs/design_example.png` (sānjosla,
   kolonnu tāfele, kompaktas kartītes). Krāsas, burti un nosaukumi ir mūsu pašu.
2. **Uzdevumu sadales tāfeli** vadītājam un administratoram: kolonnas ir darbinieki,
   kartītes ir viņu atvērtie uzdevumi. Kartīti var pārvilkt uz cita darbinieka kolonnu,
   un uzdevums tiek nodots tam darbiniekam.

**Neviena esošā funkcija nedrīkst pazust.** Drīkst pievienot jaunas.

## Pieņemšanas kritēriji (acceptance criteria)

### Funkcionalitāte saglabāta

| # | Ievade | Sagaidāmais rezultāts |
|---|---|---|
| 1 | Visi CR-4 un CR-5 maršruti (sk. `docs/openapi.yaml`) | Pieejami ar tiem pašiem URL, metodēm, parametriem, tiesībām un statusa kodiem |
| 2 | `make test` | Iziet. Testus, kas pārbauda mainītu HTML struktūru, drīkst pielāgot tikai tā, lai tie pārbauda to pašu uzvedību; neviens tests netiek dzēsts bez aizstājēja |
| 3 | Visas formas (F1–F5, MI-1, admin) | Servera validācija, kļūdu teksti pie laukiem, kļūdu kopsavilkums ar fokusu, POST → redirect → GET darbojas kā CR-5 |
| 4 | JavaScript izslēgts vai nav ielādējies | Visas CR-5 funkcijas joprojām darbojas (JS tikai uzlabo); izņēmums ir tikai vilkšana tāfelē (#20–#22), kurai ir alternatīva (#23) |
| 5 | Lomas (N3), VDAR (N2), MI marķējums, piekļuves žurnāls | Nemainīti |

### Lietotnes ietvars

| # | Ievade | Sagaidāmais rezultāts |
|---|---|---|
| 6 | Jebkura CRM lapa (izņemot `/sakums`, `/pieklustamiba`, CR-4 lapas) | Kreisajā pusē sānjosla: Kopsavilkums, Mani uzdevumi, Organizācijas, Pieprasījumi, Uzdevumu sadale¹, Pārskats¹, Administrēšana² (¹ vadītājs un administrators, ² administrators) |
| 7 | Sānjoslas punkti | Ikona **un redzams teksts** (nevis tikai ikona ar uznirstošu padomu); aktīvā sadaļa atzīmēta gan vizuāli, gan ar `aria-current="page"` |
| 8 | Augšējā josla | Lapas nosaukums, meklēšanas lauks (F6), poga „Pievienot” ar izvēlni: Organizācija, Uzdevums; pašreizējais darbinieks un loma, saite „Mainīt darbinieku” |
| 9 | „Pievienot” izvēlne | Atveras ar peli un tastatūru (Enter/Space, bultiņas, Escape aizver un atgriež fokusu); bez JS tā ir saišu saraksts |
| 10 | Platums ≤ 768 px | Sānjosla kļūst par apakšējo vai saliekamu izvēlni; nav horizontālās ritināšanas 320 px platumā (izņemot tāfeles kolonnu laukumu, #26) |
| 11 | Kājene | Joprojām „Mācību režīms, nav pieteikšanās” un saite uz `/pieklustamiba` |

### Uzdevumu sadales tāfele (jauna)

| # | Ievade | Sagaidāmais rezultāts |
|---|---|---|
| 12 | Vadītājs vai administrators atver `GET /uzdevumi/sadale` | Tāfele: katra kolonna ir viens darbinieks |
| 13 | Darbinieks atver `/uzdevumi/sadale` | 403 |
| 14 | Kolonnas galvene | Darbinieka vārds, atvērto uzdevumu skaits, kavēto skaits (teksts, ne tikai krāsa) un noslodzes josla (atvērtie, kavētie izcelti) |
| 15 | Kartīte | Uzdevuma nosaukums, saistītā organizācija un/vai pieprasījums (saites), termiņš, birka „Kavēts”, ja termiņš pagājis |
| 16 | Kartīšu secība kolonnā | Vispirms kavētie, tad pēc termiņa |
| 17 | Rāda tikai atvērtos uzdevumus | Izpildītie uzdevumi netiek rādīti |
| 18 | Kolonnu atlase pēc noklusējuma | Darbinieki, kuriem ir vismaz viens atvērts uzdevums |
| 19 | Vadītājs izvēlas, kurus darbiniekus rādīt | Izvēle saglabājas šim vadītājam un ir spēkā arī nākamajā reizē. Tas tiek glabāts pēc tava ieteikuma. |
| 20 | Kartīti pārvelk uz cita darbinieka kolonnu | Uzdevuma izpildītājs mainās; kartīte paliek jaunajā kolonnā; abu kolonnu skaitītāji atjaunojas bez lapas pārlādes |
| 21 | Pārvilkšana neizdodas (tīkls, 403, 404, 5xx) | Kartīte atgriežas sākotnējā kolonnā; paziņojums ar iemeslu (`aria-live`) |
| 22 | Kartīti nomet tajā pašā kolonnā | Nekas nemainās, pieprasījums netiek sūtīts |
| 23 | Katrai kartītei poga „Nodot citam darbiniekam” (WCAG 2.2, 2.5.7) | Atver darbinieku sarakstu; izvēle maina izpildītāju tāpat kā #20; darbojas ar tastatūru un bez JS (forma, `POST /uzdevumi/{taskId}/izpilditajs`, 303 atpakaļ uz tāfeli) |
| 24 | `POST /uzdevumi/{taskId}/izpilditajs` ar `Accept: application/json` | 200 `{id, assignee_id}`; nederīgs darbinieks → 400 `Error`; darbinieka loma → 403; neesošs uzdevums → 404 |
| 25 | Izpildītāja maiņa | Ieraksts piekļuves žurnālā: „mainīja”, uzdevums #ID, organizācija |
| 26 | Daudz kolonnu vai šaurs ekrāns | Kolonnu laukums ritinās horizontāli savā reģionā (fokusējams, ar nosaukumu); lapa pati neritinās horizontāli |
| 27 | Kolonnā nav uzdevumu | Teksts „Atvērtu uzdevumu nav”; kolonna joprojām pieņem kartītes |
| 28 | Pēc nodošanas | Jaunais izpildītājs redz uzdevumu sadaļās „Mani uzdevumi” un „Kopsavilkums” (ja termiņš ir šodien vai pagājis) |

### Vizuālā identitāte

| # | Ievade | Sagaidāmais rezultāts |
|---|---|---|
| 29 | Krāsas, burti, atstarpes | Pēc sadaļas „Dizaina virziens” kā CSS mainīgie vienā vietā; gaišais un tumšais režīms |
| 30 | Burtu saime | Glabāta repo (OFL), nav ārēju pieprasījumu; atbalsta ā č ē ģ ī ķ ļ ņ š ū ž |
| 31 | F7 diagramma | Joprojām SVG + tā pati tabula; krāsa pārbaudīta ar dataviz validatoru gaišajam un tumšajam režīmam |
| 32 | Zīmols | Nav Pipedrive vai cita produkta nosaukuma, logotipa vai zīmola krāsu |

### Piekļūstamība un līgums

| # | Ievade | Sagaidāmais rezultāts |
|---|---|---|
| 33 | `tests/a11y_check.py` visām lapām, ieskaitot `/uzdevumi/sadale` (gaišais, tumšais, 320 px, 640 px) | axe bez critical/serious; nav horizontālās lapas ritināšanas |
| 34 | Tāfele tikai ar tastatūru | Uzdevumu var nodot citam darbiniekam ar #23; fokuss pēc darbības paliek uz pārvietotās kartītes vai tās pogas |
| 35 | Kustība | Animācija tikai kā atbilde uz darbību (vilkšana, nomešana, izvēlnes atvēršana); `prefers-reduced-motion` to izslēdz |
| 36 | `/pieklustamiba` | Atjaunota ar CR-6 testu rezultātiem |
| 37 | `docs/openapi.yaml` | Apraksta `GET /uzdevumi/sadale` un `POST /uzdevumi/{taskId}/izpilditajs` (HTML un JSON atbildes); `make lint-contract` jaunajām operācijām bez kļūdām |

## Dizaina virziens (priekšlikums)

**Ideja.** „Darba galds pie ezera”: mierīga, tumša ezera dzelmes sānjosla un gaišs,
vēss darba laukums. Vienīgais skaļais elements ir **sadales tāfele**: tās kolonnu
galvenes ar noslodzes joslu ļauj vienā skatienā redzēt, kurš ir pārslogots. Viss pārējais
ir kluss un blīvs.

| Nosaukums | Hex | Loma |
|---|---|---|
| Dzelme | `#10343B` | Sānjosla, virsraksti tumšā fonā |
| Ūdens | `#1F6F78` | Galvenās pogas, saites, aktīvā sadaļa |
| Niedre | `#D8B23A` | Nomešanas vietas izcēlums, aktīvās sadaļas atzīme sānjoslā (nekad teksts uz balta) |
| Migla | `#EEF3F3` | Darba laukuma fons |
| Tinte | `#172326` | Pamatteksts |
| Dzērvene | `#B3261E` | Kavēts, kļūdas (vienmēr kopā ar tekstu) |

- **Burti:** Onest (OFL, latin-ext). Viena saime: 400 teksts, 500 etiķetes, 650
  virsraksti; skaitļiem `tabular-nums`. Skala ~1,2: 13 / 15 / 18 / 22 / 27 px.
- **Kartītes:** plakanas, 1 px apmale, 6 px noapaļojums; ēna tikai velkamajai kartītei.
  Pogām un laukiem 6 px, kolonnām 8 px, lapas paneļiem 0. Noapaļojums seko hierarhijai.
- **Teksts:** teikuma reģistrs, bez lielajiem burtiem etiķetēs, bez „→” pogās; darbības
  nosaukums ir vienāds visā plūsmā („Nodot citam darbiniekam” → „Uzdevums nodots: <vārds>”).
- **Izkārtojums:** teksts izlīdzināts pa kreisi; skaitļi kolonnu galvenēs un tabulās pa labi.

```
+--------+-------------------------------------------------------------------+
| Kops.  | Uzdevumu sadale     [ Meklēt ...       ]  [+ Pievienot]  Inese D. |
| Mani   +-------------------------------------------------------------------+
| Org.   | Rādīt: [Darbinieki v]                    32 atvērti, 8 kavēti     |
| Piepr. | +------------+ +------------+ +------------+ +------------+       |
|>Sadale | | Anna K.    | | Jānis O.   | | Līga B.    | | Mārtiņš L. |       |
| Pārsk. | | 3 atv. 1 k.| | 2 atv.     | | 0 atv.     | | 4 atv. 2 k.|       |
| Admin. | | ###=       | | ##         | |            | | ####==     |       |
|        | | +--------+ | | +--------+ | | Atvērtu    | | +--------+ |       |
|        | | |Kavēts  | | | |Saskaņot| | | uzdevumu   | | | ...    | |       |
|        | | |Piezvan.| | | |telpas  | | | nav        | | +--------+ |       |
|        | | |SIA Ezer| | | |18.10.  | | |            | |            |       |
|        | | |[Nodot] | | | |[Nodot] | | |            | |            |       |
|        | | +--------+ | | +--------+ | |            | |            |       |
|        | +------------+ +------------+ +------------+ +------------+       |
+--------+-------------------------------------------------------------------+
```

## Precizējumi (clarifications)

| Jautājums | Atbilde | Kas atbildēja, kad |
|---|---|---|
| Kas ir tāfeles kolonnas un kartītes? | Kolonnas: darbinieki; kartītes: viņu atvērtie uzdevumi | <loma>, 2026-10-14 |
| Kas var lietot tāfeli? | Vadītājs un administrators | <loma>, 2026-10-14 |
| Vai vajag JavaScript? | Jā; JS atļauts visā lietotnē, bet esošās funkcijas nedrīkst pazust | <loma>, 2026-10-14 |
| Vilkšana un WCAG 2.5.7? | Vilkšana + poga „Nodot citam darbiniekam” | <loma>, 2026-10-14 |
| Kuras kolonnas rādīt? | Vadītāja izvēlēti darbinieki; noklusējums: tie, kam ir atvērti uzdevumi | <loma>, 2026-10-14 |
| Kas ir kartītē? | Atvērtie uzdevumi: nosaukums, saite, termiņš, „Kavēts” | <loma>, 2026-10-14 |
| Cik tuvu piemēram? | Struktūra no piemēra, jauna identitāte | <loma>, 2026-10-14 |
| Kur glabāt vadītāja kolonnu izvēli? | Pēc tavas izvēles. | |
| Vai nodošana jāpaziņo jaunajam izpildītājam? | Jā, jāpaziņo, bet pati funkcionalitāte ir out of scope šajā CR | |
| Vai vilkšanai kolonnas iekšienē jāmaina secība? | Secību nosaka termiņš | |
| Vai `docs/design_example.png` komitēt repo? | Nē | |

## Ārpus tvēruma (out of scope)

- Tāfele pieprasījumiem vai organizācijām
- Uzdevuma termiņa vai statusa maiņa ar vilkšanu (tikai izpildītāja maiņa)
- Paziņojumi (e-pasts, push) par nodotiem uzdevumiem
- Īsta autentifikācija (paliek mācību režīms)
- Pipedrive funkcijas, kuras CRM nav (darījumu summas, „Won”, aktivitāšu plānotājs)

## Komentāri (comments)

- 2026-10-14 · `docs/design_example.png` ir Pipedrive mārketinga ekrānuzņēmums ar demo personas foto un vārdu. Izmantojam tikai kā struktūras iedvesmu. Ieteikums: neglabāt to repo (autortiesības, personas attēls), bet aprakstīt šajā pieteikumā vai aizstāt ar paša zīmētu skici.
- 2026-10-14 · Esošā lietotne apzināti strādāja bez JS (CR-5 #35). Šis CR to atslābina, bet #4 prasa, lai bez JS nekas, kas jau strādā, nesalūzt.
- 2026-10-14 · Liels apjoms vienā PR: ietvars + identitāte skar katru lapu. Ieteicamā secība zarā: (1) ietvars un tokeni, (2) lapu pielāgošana, (3) tāfele, (4) a11y un līgums.
