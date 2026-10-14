# MI-2 · Organizāciju prioritizācija «pēc sadarbības potenciāla»: klasifikācija

> CR-5, kritērijs #41. Sagatavots 14.10.2026. Šis ir izstrādes komandas izvērtējums
> mācību vajadzībām, nevis juridisks atzinums. Pirms jebkura lēmuma «būvēt» to
> jāpārskata datu aizsardzības speciālistam un juristam.

## 1. Ko sistēma darītu

Ezermalas CRM sakārtotu organizācijas (uzņēmumus, NVO, pašvaldības) pēc aprēķināta
«sadarbības potenciāla», un darbinieki pēc šīs secības izlemtu, kurām organizācijām
pievērst uzmanību: kam piedāvāt konsultācijas, kurus aicināt uz semināriem, kuru
pieprasījumus skatīt vispirms.

## 2. Kas tiek vērtēts

| Ievaddati | Avots CRM | Piezīme |
|---|---|---|
| Mijiedarbību skaits un biežums | `interactions` | Atspoguļo darbinieku aktivitāti, ne organizācijas vajadzības |
| Pieprasījumu skaits, statuss, kavējumi | `requests` | Kavējums rodas iestādes, nevis organizācijas dēļ |
| Organizācijas veids | `organizations.type` | Var radīt sistemātisku atšķirību starp NVO un uzņēmumiem |
| Kopsavilkumu brīvais teksts | `interactions.summary` | Var saturēt informāciju par kontaktpersonām |
| Kontaktpersonu dati | `contacts` | Fiziskas personas; VDAR attiecas tieši |

Modelis netieši vērtētu arī **fiziskas personas**: kontaktpersonas, kuru saziņas
vēsture ietekmē organizācijas vērtējumu, un mazās NVO, kas faktiski ir dažu cilvēku
apvienības.

## 3. Sekas organizācijai un personai

- **Piekļuve iestādes pakalpojumiem.** Zemāk novērtētas organizācijas saņemtu mazāk
  konsultāciju un uzaicinājumu. Publiskai iestādei tas ir nevienlīdzīgas attieksmes
  risks.
- **Pašpastiprinoša cilpa.** Organizācijas ar mazāk mijiedarbībām saņem zemāku vērtējumu,
  tāpēc vēl mazāk mijiedarbību. Jaunas un mazas organizācijas nonāk nelabvēlīgā stāvoklī.
- **Necaurredzamība.** Organizācija nezina, ka tiek vērtēta, un nevar apstrīdēt
  vērtējumu.
- **Profilēšana (VDAR 4. panta 4. punkts, 22. pants).** Ja vērtējumā izmanto
  kontaktpersonu datus, tā ir fizisku personu profilēšana, kurai vajag tiesisko pamatu,
  informēšanu un iespēju iebilst.

## 4. Klasifikācija pēc MI akta (Regula (ES) 2024/1689)

| Jautājums | Izvērtējums |
|---|---|
| Aizliegta prakse (5. pants)? | Nē. Nav sociālās vērtēšanas fiziskām personām plašā nozīmē, nav manipulācijas. |
| Augsta riska sistēma (6. pants, III pielikums)? | **Iespējams.** III pielikuma 5. punkts attiecas uz publisko iestāžu MI, kas vērtē fizisku personu tiesības uz pakalpojumiem. Organizāciju vērtēšana tieši tur neietilpst, bet, ja vērtējums balstās uz kontaktpersonu datiem un ietekmē piekļuvi iestādes pakalpojumiem, robeža ir neskaidra. 6. panta 3. punkts paredz, ka sistēma, kas veic fizisku personu profilēšanu, vienmēr ir augsta riska. |
| Pārredzamības pienākumi (50. pants)? | Ja tiek ģenerēts teksts vai rādīti MI vērtējumi, tie jāmarķē. |
| Riska klase | **Augsts vai neskaidrs.** Bez juridiska izvērtējuma pieņemam augstāko piemērojamo klasi. |

Augsta riska sistēmai būtu vajadzīga riska pārvaldība, datu kvalitātes prasības,
tehniskā dokumentācija, žurnalēšana, cilvēka pārraudzība, precizitātes un noturības
pārbaudes, kā arī pamattiesību ietekmes novērtējums publiskai iestādei (27. pants).
Mācību prototipā (N4: 1,5 h) neko no tā nevar nodrošināt.

## 5. Lēmums

**Nebūvēt.** MI-2 netiek īstenots CR-5 ietvaros, un kods netiek veidots.

Pamatojums:

1. Iespējamā augsta riska klase un fizisku personu profilēšana prasa pasākumus, ko
   prototipā nevar nodrošināt.
2. Pieejamie dati (mijiedarbību skaits) mēra darbinieku aktivitāti, nevis
   «sadarbības potenciālu», tāpēc vērtējums būtu maldinošs.
3. Vadītāja vajadzību daļēji sedz F7 pārskats: aktīvākās organizācijas un kavētie
   pieprasījumi bez automātiskas vērtēšanas, un lēmumu pieņem cilvēks.

## 6. Ja to būtu jāpārskata

Pirms jebkura lēmuma «būvēt» jāizpilda:

- definēt, ko nozīmē «sadarbības potenciāls», un to saskaņot ar vadību;
- izslēgt kontaktpersonu datus no ievaddatiem vai noteikt tiesisko pamatu;
- veikt pamattiesību ietekmes novērtējumu un VDAR ietekmes novērtējumu (35. pants);
- paredzēt organizāciju informēšanu un iespēju apstrīdēt vērtējumu;
- rādīt vērtējumu tikai kā ieteikumu ar paskaidrojumu, ne kā secību pēc noklusējuma.
