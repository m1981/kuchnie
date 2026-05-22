---
aliases: []
categories:
    - Recently Added
confidence: medium
created: '2026-05-22T23:34:57'
orphan: false
sources:
    - file: /Users/michal/PycharmProjects/kuchnie/07_SOP_Montaz/00_Algorytm_Projektowania.md
      hash: c89639e2f05cc794ddcb6d24ee257b63747e696f79f86928fd0e045b97654c91
      ingested: '2026-05-22T23:34:57'
      size: 3356
status: active
tags:
    - projektowanie kuchni
    - etapy projektowania
    - inżynier
    - architekt
    - technolog
    - artysta
    - funkcjonalność
    - estetyka
    - kolorystyka
    - materiały
title: 00 Algorytm Projektowania
---

# 00 Algorytm Projektowania

### ETAP 1: INŻYNIER (Geometria i Funkcja - tzw. "White Box")

_Na tym etapie kuchnia nie ma kolorów. Jest szarą bryłą. Jeśli układ nie działa, żaden kolor tego nie uratuje._

1.  **Pomiary i Ograniczenia:** Wchodzisz z laserem. Gdzie jest pion kanalizacyjny? Gdzie siła do indukcji? Gdzie kratka wentylacyjna? To definiuje układ. ^[FILENAME:00_Algorytm_Projektowania.md:5]
2.  **Trójkąt Roboczy (w aneksie to zazwyczaj "Linia Robocza"):** Ustawiasz w programie (lub na kartce) 3 główne słupy: Lodówka -> Zlew -> Płyta. Zostawiasz między nimi blat roboczy (minimum 60 cm między zlewem a płytą). ^[FILENAME:00_Algorytm_Projektowania.md:6]
3.  **Siatka Szafek (Rytm):** Dzielisz dół na równe moduły (np. 60-60-60-45). Unikasz szafek o dziwnych wymiarach (np. 37,5 cm). ^[FILENAME:00_Algorytm_Projektowania.md:7]
4.  **Zabudowa pod sufit:** Projektujesz blendy maskujące (góra i boki). ^[FILENAME:00_Algorytm_Projektowania.md:8]

_Wynik: Masz gotowy szkielet. Wiesz, ile formatek zamówisz na CNC._

### ETAP 2: ARCHITEKT (Baza Kolorystyczna - 70% wizualnej masy)

_Teraz ubieramy "szarą bryłę" w główny garnitur. Wybieramy dominujący materiał._

1.  **Wybór Stylu:** Pytasz klienta: _Skandynawia, Włochy czy Loft?_ ^[FILENAME:00_Algorytm_Projektowania.md:16]
2.  **Fronty Dolne i Słupki (SWISS KRONO):** Wybierasz JEDEN główny kolor z palety BE.VELVET (np. U119 EM Beż Jasny). ^[FILENAME:00_Algorytm_Projektowania.md:17]
3.  **Zasada Monolitu (Korpusy):** Od razu, automatycznie dobierasz do tego płytę korpusową w tym samym kolorze (U119 VL). Nie pytasz o to klienta, po prostu to robisz. ^[FILENAME:00_Algorytm_Projektowania.md:18]
4.  **Cokoły i Blendy:** Wszystko w tym samym kolorze co fronty. ^[FILENAME:00_Algorytm_Projektowania.md:19]

_Wynik: Masz spójną, nowoczesną bazę. Aneks wygląda jak elegancka meblościanka._

### ETAP 3: TECHNOLOG (Strefa Robocza - 20% wizualnej masy)

_Tu wchodzi Twój produkt Premium, który sprzedaje całą kuchnię._

1.  **Blat (EGGER 12mm Kompakt):** Dobierasz blat kontrastujący lub współgrający z bazą. (np. do beżowych frontów dajesz blat w dekorze jasnego kamienia). ^[FILENAME:00_Algorytm_Projektowania.md:27]
2.  **Zlew:** Skoro masz blat wodoodporny, od razu projektujesz zlew podwieszany (stalowy lub kompozytowy). To Twój as w rękawie. ^[FILENAME:00_Algorytm_Projektowania.md:28]
3.  **Ściana (Splashback):** Decyzja: czy ściana ma zniknąć (wtedy dajesz płytę w kolorze frontów), czy ma być ozdobą (wtedy dajesz płytę w dekorze blatu lub drewna). ^[FILENAME:00_Algorytm_Projektowania.md:29]

_Wynik: Kuchnia zyskuje funkcjonalność i status Premium dzięki cienkiemu blatowi._

### ETAP 4: ARTYSTA (Biżuteria i Detale - 10% wizualnej masy)

_Dopiero teraz zajmujesz się "smaczkami", które nadają ostateczny charakter._

1.  **Akcenty Drewniane (SWISS KRONO Sensesation):** Jeśli kuchnia jest zbyt sterylna, zmieniasz fronty szafek wiszących na dekor drewna (np. Dąb Eden). ^[FILENAME:00_Algorytm_Projektowania.md:37]
2.  **Uchwyty / Profile Gola:** Dobierasz kolor detali. Złoto (styl włoski), Czarny mat (loft), frezowane/ukryte (minimalizm). ^[FILENAME:00_Algorytm_Projektowania.md:38]
3.  **Oświetlenie LED:** Wybierasz temperaturę barwową (ciepła 3000K do drewna/beżu, neutralna 4000K do szarości/czerni). ^[FILENAME:00_Algorytm_Projektowania.md:39]

---

### Dlaczego ten model działa?

Bo eliminuje chaos. Kiedy klient mówi: _"A może zróbmy zielone fronty na górze, a na dole drewno, i do tego gruby blat w ciapki?"_, Ty jako ekspert odpowiadasz:
_"Panie Janie, w nowoczesnym projektowaniu najpierw budujemy bazę. Ustaliliśmy styl minimalistyczny. Zróbmy spójny dół, dajmy ultracienki blat Eggera ze zlewem podwieszanym, a drewnem ocieplimy tylko górę. Inaczej zrobimy z aneksu choinkę."_ ^[FILENAME:00_Algorytm_Projektowania.md:46]

Idąc od ogółu (bryła) do szczegółu (uchwyt), masz pełną kontrolę nad projektem, budżetem i zamówieniem na CNC. ^[FILENAME:00_Algorytm_Projektowania.md:48]

## Parametryczne Modelowanie Mebli Kuchennych z Corpus

Ten przewodnik opisuje proces modelowania parametrycznego szafek kuchennych przy użyciu oprogramowania Corpus. Kluczowe jest budowanie biblioteki sparametryzowanych modułów dla konkretnych układów kuchni (I, L, U), z uwzględnieniem parametrów dla różnych typów szafek, takich jak szafki dolne, narożne, słupki i szafki wiszące. Celem jest efektywne generowanie bezbłędnych projektów dla produkcji [[cnc-driven-furniture-production]]. ^[FILENAME:corpus-cwiczenia.md:1]

### Kluczowe Parametry i Moduły:

- **Szafki Dolne:** Uwzględnienie parametrów dla [[szafka zlewowa]], [[szafka pod piekarnik]], frontów zmywarek. ^[FILENAME:corpus-cwiczenia.md:12,14,16]
- **Szafki Narożne:** Modelowanie [[ślepym narożnik]] i [[narożnik L-kształtny]]. ^[FILENAME:corpus-cwiczenia.md:25,27]
- **Szafki Wysokie (Słupki):** Parametryzacja dla [[słupek lodówkowy]] oraz [[słupek Piekarnik + Mikrofala]]. ^[FILENAME:corpus-cwiczenia.md:34,36]
- **Moduły Szufladowe:** Tworzenie biblioteki [[moduły szufladowe]] z uwzględnieniem różnych szerokości i wysokości. ^[FILENAME:corpus-cwiczenia.md:18]
