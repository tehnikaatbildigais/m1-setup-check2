---
id: CR-8
type: change-request
title: "Jauns README: projekta apraksts un instrukcijas"
status: DRAFT
priority: low
reporter: "<loma, nevis vārds>"
owner: "@<github-lietotājvārds>"
contract: "Nav (dokumentācija)"
depends_on: [CR-7]
exported: "<datums> · Ezermalas pieteikumu sistēma (simulācija)"
data_check: "Nav personas datu. Ekrānuzņēmumā tikai izdomāti sākumdati."
---

# CR-8 · Jauns README

> Noteikumi vienkāršoti mācību vajadzībām.

## Apraksts (description)

README joprojām ir kursa veidnes teksts par uzdevumiem A0 un A1, un projekta apraksts
(CR-4…CR-7) ir pievienots tā beigās kā atsevišķas piezīmes. Jaunam izstrādātājam vai
lietotājam no tā nav saprotams, kas ir šī sistēma, kā to palaist un kā tajā strādāt.

Vajag README, kas veidots kā parasts GitHub repozitorija apraksts: kas tas ir, iespējas,
palaišana, konfigurācija, struktūra, testēšana, darba process. Kursa A0/A1 instrukcijas
tiek dzēstas.

## Pieņemšanas kritēriji (acceptance criteria)

| # | Ievade | Sagaidāmais rezultāts |
|---|---|---|
| 1 | Atver README | Nav kursa A0/A1 instrukciju; projekta nosaukums, īss apraksts, norāde, ka dati ir izdomāti un sistēma ir mācību režīmā |
| 2 | Saturs | Satura rādītājs ar saitēm uz sadaļām |
| 3 | Iespējas | Visas sistēmas sadaļas (kopsavilkums, organizācijas, kontakti, mijiedarbības ar MI, pieprasījumi, uzdevumi, sadale, meklēšana, pārskats, administrēšana, lietotāju konti) |
| 4 | Palaišana | Instrukcija Codespaces un lokāli; lokālā instrukcija tīrā vidē noved pie strādājošas lietotnes un `make test` |
| 5 | Pirmā ienākšana | Sākumdatu apjoms, ieteicamie darbinieki katrai lomai, kā sākt no jauna |
| 6 | Lomas | Tiesību tabula darbiniekam, vadītājam, administratoram |
| 7 | Konfigurācija | Visi vides mainīgie ar noklusējumiem: `CRM_DB_PATH`, `AUTH_DB_PATH`, `PUBLIC_BASE_URL`, `ANTHROPIC_API_KEY`, `A11Y_REQUIRED` |
| 8 | Projekta struktūra | Mapes un galvenie faili ar īsu nozīmi |
| 9 | Testēšana | `make test`, `make lint-contract`, pieejamības testi ar `make install-dev`; ko pārbauda katrs testu fails; ko dara CI |
| 10 | API līgums | `docs/openapi.yaml` kā patiesības avots; Swagger UI; kāpēc `make lint-contract` šobrīd ziņo par 7 kļūdām (CR-2) |
| 11 | Piekļūstamība un datu aizsardzība | Galvenie principi un saite uz `/pieklustamiba` un `docs/mi2_klasifikacija.md` |
| 12 | Darba process | Pieteikumi `tracker/`, viens pieteikums = viens zars = viens PR, ID nosaukumos, pārbaudes pirms komita (saskaņā ar `CLAUDE.md`) |
| 13 | Zināmie ierobežojumi un licences | Mācību režīms, sesijas, e-pasts, ekrānlasītājs; trešo pušu fontu un axe-core licences |
| 14 | Ekrānuzņēmums | `docs/ekrans-uzdevumu-sadale.png` ar izdomātiem datiem |
| 15 | Visas saites README | Ved uz esošiem failiem un sadaļām |

## Precizējumi (clarifications)

| Jautājums | Atbilde | Kas atbildēja, kad |
|---|---|---|
| Ko darīt ar kursa A0/A1 instrukcijām? | Dzēst pilnībā | <loma>, 2026-10-14 |
| Valoda? | Latviešu | <loma>, 2026-10-14 |
| Vai rakstīt pirms pieteikuma? | Jā, pieteikums sagatavots paralēli | <loma>, 2026-10-14 |
| ❓ Vai pievienot licenci projekta kodam? | <neatbildēts> — README norāda, ka licence nav noteikta | |

## Ārpus tvēruma (out of scope)

- `Makefile` un CI izmaiņas (`make verify-setup` joprojām prasa `setup/claude-answer.md`)
- Kursa A1 uzdevuma (CR-2) pabeigšana
- Angļu valodas versija

## Komentāri (comments)

- 2026-10-14 · Lokālā instrukcija pārbaudīta tīrā virtuālajā vidē: `make test` → 164 iziet, pieejamības testi izlaisti (nav Playwright); `/`, `/docs`, `/pieklustamiba` atbild; `make lint-contract` ziņo par 7 zināmajām CR-2 kļūdām, kā aprakstīts README.
- 2026-10-14 · Ar A0/A1 instrukciju dzēšanu repozitorijā vairs nav paskaidrots, kāpēc `make verify-setup` prasa `setup/claude-answer.md`; README to min sadaļā „Testēšana”.
