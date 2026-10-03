# 02 — Specyfikacja użytkowa

> KryzIO · tryb uproszczony · CO, nie JAK

## Nawigacja

- Aplikacja startuje od **czatu z agentem**
- Osobne zakładki: **Czat** (start), **Mapa** (panel na żywo), **Demo** (symulacja)

## Funkcje

### Pytanie do agenta (zakładka Czat — ekran startowy)

- **F1** — Mieszkanka wpisuje pytanie zwykłym językiem (np. „Czy na Kobierzyńskiej grozi zalanie, co mam zrobić?”)
- **F2** — Agent rozpoznaje miejsce z pytania (ulica, osiedle) albo prosi o doprecyzowanie
- **F3** — Odpowiedź: aktualna sytuacja w tym miejscu + konkretna lista kroków (przed / w trakcie / po zdarzeniu)
- **F4** — Każda odpowiedź pokazuje źródła danych i godzinę ich aktualizacji
- **F5** — Gdy danych brakuje, agent odpowiada wprost **„Brak danych”** (zamiast zgadywać)
- **F6** — Gotowe przyciski z szybkimi pytaniami (np. „Co spakować?”, „Gdzie najbliższy schron?”)
- **F6a** — Mieszkanka może opcjonalnie podać w rozmowie skład gospodarstwa (dzieci, senior, zwierzę) — lista kroków to uwzględnia
- **F6b** — Agent pamięta kontekst (adres, skład gospodarstwa) tylko w ramach jednej sesji; bez kont, bez zapisu na serwerze

### Panel na żywo (zakładka Mapa)

- **F7** — Podsumowanie bieżących zagrożeń w Krakowie (ostrzeżenia IMGW, stany wód, jakość powietrza, wyłączenia prądu)
- **F8** — Mapa Krakowa z naniesionymi zagrożeniami
- **F9** — Mapa schronów / miejsc ukrycia + najbliższy schron dla podanego adresu

### Zakładka Demo (symulacja)

- **F10** — Wybór scenariusza: **powódź**, **brak prądu**, **atak bombowy**
- **F11** — Scenariusz podmienia dane wejściowe agenta i mapy na symulowane; ekran wyraźnie oznaczony jako SYMULACJA
- **F12** — W scenariuszu można zadawać agentowi pytania tak samo jak na żywo
- Scenariusz ataku bombowego: symulowany komunikat + wskazówki z poradnika + najbliższy schron (na ten moment wystarczy)

### Informacje stałe

- **F13** — Numery alarmowe i zasady z poradnika bezpieczeństwa — dostępne zawsze, bez pytania do agenta

## Poza tą specyfikacją (świadomie)

- Powiadomienia push i proaktywne ostrzeżenia
- Język angielski
- Konta użytkowników / logowanie
- Aplikacja mobilna natywna
- Zgłaszanie zdarzeń przez mieszkańców
- Panel dla urzędu / służb

## Ustalenia z iteracji

- Lista funkcji zaakceptowana przez autora (Q1)
- F5: komunikat przy braku danych — dosłownie „Brak danych”
- F10: scenariusze demo zmienione na powódź / brak prądu / atak bombowy (pożar wypadł ze scenariuszy demo względem kroku 1 — do potwierdzenia)
- Q2: pamięć tylko w sesji — tak
- Q3: skład gospodarstwa — tak, opcjonalnie
- Q4: atak bombowy = komunikat + poradnik + schron — na ten moment tak
- Q5: start od czatu, mapa jako osobna zakładka
