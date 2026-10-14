---
id: CR-4
type: change-request
title: "Lietotāju reģistrācija, pieteikšanās un paroles atjaunošana"
status: DRAFT
priority: medium
reporter: "<loma, nevis vārds>"
owner: "@<github-lietotājvārds>"
contract: "docs/openapi.yaml · POST /auth/register, POST /auth/login, POST /auth/logout, POST /auth/password-reset, POST /auth/password-reset/confirm"
depends_on: []
exported: "<datums> · Ezermalas pieteikumu sistēma (simulācija)"
data_check: "Nav personas datu. E-pasti un lietotājvārdi piemēros ir izdomāti."
---

# CR-4 · Lietotāju reģistrācija, pieteikšanās un paroles atjaunošana

> Noteikumi vienkāršoti mācību vajadzībām.

## Apraksts (description)

Sistēmā nav lietotāju kontu. Vajag, lai cilvēks var izveidot kontu, pieteikties
un iziet, kā arī atjaunot aizmirstu paroli. Reģistrētie lietotāji glabājas
datubāzē, un pēc servera restartēšanas tie saglabājas. Pieteikšanās lapā ir saite
uz reģistrāciju, un reģistrācijas lapā ir saite atpakaļ uz pieteikšanos. Pēc
pieteikšanās lietotājs redz vienkāršu sveiciena lapu ar savu lietotājvārdu un
pogu "Iziet". Izskats ir vienkāršs un neitrāls, jo repozitorijā nav esošu lapu,
pēc kurām vadīties.

## Pieņemšanas kritēriji (acceptance criteria)

| # | Ievade | Sagaidāmais rezultāts |
|---|---|---|
| 1 | Reģistrācija: derīgs e-pasts, lietotājvārds, parole (≥ 8 simboli), tāda pati atkārtotā parole | 201, konts izveidots, pāriet uz pieteikšanās lapu |
| 2 | Parole ar 7 simboliem | 400, lauks `password`, paziņojums par minimālo garumu |
| 3 | Parole un atkārtotā parole atšķiras | 400, lauks `passwordConfirm` |
| 4 | E-pasts jau reģistrēts | 409, lauks `email` |
| 5 | Lietotājvārds jau reģistrēts | 409, lauks `username` |
| 6 | Nederīgs e-pasta formāts (`janis@`) | 400, lauks `email` |
| 7 | Tukšs lietotājvārds vai tikai atstarpes | 400, lauks `username` (jebkuri citi simboli ir atļauti) |
| 8 | Pieteikšanās ar e-pastu + pareizu paroli | 200, atvērta sesija, sveiciena lapa ar lietotājvārdu |
| 9 | Pieteikšanās ar lietotājvārdu + pareizu paroli | 200, tāpat kā #8 |
| 10 | Nepareiza parole vai neesošs lietotājs | 401 ar vienu un to pašu paziņojumu (nevar noteikt, vai konts eksistē) |
| 11 | 3 nepareizas paroles pēc kārtas vienam kontam | Konts bloķēts uz 5 min; arī pareiza parole šajā laikā atgriež 423 vai 401 (❓ sk. precizējumus) |
| 12 | Pēc 5 min bloķēšanas | Pareiza parole atkal ļauj pieteikties; kļūdu skaitītājs tiek nonullēts |
| 13 | Veiksmīga pieteikšanās pēc 1–2 kļūdām | Kļūdu skaitītājs tiek nonullēts |
| 14 | "Iziet" | Sesija beigta; sveiciena lapa vairs nav pieejama bez pieteikšanās |
| 15 | Sveiciena lapa bez pieteikšanās | Pāradresē uz pieteikšanās lapu |
| 16 | Paroles atjaunošana: reģistrēts e-pasts | 202; servera žurnālā tiek ierakstīta vienreizēja saite, derīga 30 min |
| 17 | Paroles atjaunošana: nereģistrēts e-pasts | 202 ar tādu pašu atbildi kā #16; žurnālā saites nav |
| 18 | Jauna parole ar derīgu marķieri | 200; vecā parole vairs nedarbojas, marķieri nevar izmantot otrreiz, bloķēšana noņemta |
| 19 | Beidzies vai jau izmantots marķieris | 400 |
| 20 | Datubāzes saturs | Paroles nav glabātas atklātā tekstā vai atgriezeniskā formā |
| 21 | Jebkura ievade | Žurnālā nav paroļu; e-pasti tikai #16 gadījumā kopā ar saiti |
| 22 | Servera restartēšana | Reģistrētie lietotāji saglabājas (SQLite datubāze) |
| 23 | Visas jaunās operācijas | Ir aprakstītas `docs/openapi.yaml` ar 400, 404 un vismaz vienu 5xx atbildi un kopīgo `Error` shēmu; `make lint-contract` un `make test` beidzas veiksmīgi |

## Precizējumi (clarifications)

| Jautājums | Atbilde | Kas atbildēja, kad |
|---|---|---|
| Tehnoloģija un datubāze? | FastAPI + SQLite | <loma>, 2026-10-14 |
| Reģistrācijas lauki? | E-pasts, lietotājvārds, parole + atkārtojums | <loma>, 2026-10-14 |
| Ar ko pieteikties? | E-pasts vai lietotājvārds vienā laukā | <loma>, 2026-10-14 |
| Paroles prasības? | Vismaz 8 simboli, sastāva noteikumu nav | <loma>, 2026-10-14 |
| Lietotājvārda noteikumi? | Jebkuri simboli, unikāls, nav tukšs | <loma>, 2026-10-14 |
| Bloķēšana? | 3 kļūdas pēc kārtas → 5 min | <loma>, 2026-10-14 |
| Kā piegādāt atjaunošanas saiti? | Prototipā tikai servera žurnālā, e-pastu nesūta | <loma>, 2026-10-14 |
| Vai mainīt API līgumu? | Jā, pievienot /auth operācijas | <loma>, 2026-10-14 |
| Lietotājvārds nedrīkst saturēt `@`.|
| ❓ Vai bloķētam kontam rādīt "konts bloķēts" (423) vai to pašu vispārīgo kļūdu (401)? 423 izpauž, ka konts eksistē. | <neatbildēts> | |
| ❓ Vai e-pastā un lietotājvārdā lielie un mazie burti ir svarīgi (`Janis` vs `janis`)? | <neatbildēts> — ieteikums: e-pastā nav, lietotājvārdā nav | |

## Ārpus tvēruma (out of scope)

- E-pasta adreses apstiprināšana un īsta e-pasta sūtīšana
- Lomas un tiesības (piem. darbinieks vs iedzīvotājs), piekļuves aizsardzība esošajiem /submissions galapunktiem
- Divfaktoru autentifikācija, pieteikšanās ar ārējiem kontiem
- Konta dzēšana un profila labošana

## Komentāri (comments)

- 2026-10-14 · Atjaunošanas saites rakstīšana žurnālā ir pieļaujama tikai lokālajam prototipam: marķieris ir piekļuves dati. Pirms jebkuras publiskas izvietošanas to jāaizstāj ar e-pasta sūtīšanu.
- 2026-10-14 · Sveiciena lapa un formas ir HTML; API līgumā apraksta tikai JSON operācijas.
