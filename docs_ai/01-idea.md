# 01 — Pomysł, persona, poufność

**Nazwa projektu: KryzIO**

> Tryb: uproszczony · HackYeah 2026 · zadanie otwarte SMART CITY · Kraków

## Pomysł

Agent AI dla mieszkańców Krakowa, który zbiera w jednym miejscu informacje o sytuacjach kryzysowych i takich, które mogą się w nie przerodzić (np. wzrost poziomu wody, susza, pożar wielkopowierzchniowy, atak bombowy). Na podstawie danych z publicznych i rządowych źródeł odpowiada na pytania mieszkańca i mówi mu, **co ma zrobić** — przed zdarzeniem, w trakcie i po nim. Odpowiedzi są spersonalizowane, czyli zależą od lokalizacji i sytuacji użytkownika.

Przykład: „Czy na ulicy Kobierzyńskiej w najbliższych dniach może dojść do zalania i jak mam się przygotować?”

## Problem

- Informacje o zagrożeniach są rozproszone na wielu stronach (IMGW, Tauron, GIOŚ, Airly, komunikaty, poradniki) i nikt ich nie agreguje
- Alert RCB jest ogólny, a mieszkańcy często traktują go jak spam
- Mieszkaniec nie dostaje odpowiedzi na pytanie „co to znaczy dla **mnie**, pod **moim** adresem i co mam teraz zrobić”

## Użytkownicy

- **Główni:** mieszkańcy Krakowa
- **Szerzej:** wszyscy przebywający w mieście — świadomie poza PoC (persona poboczna odrzucona)

## Źródła danych (wstępnie)

- IMGW (ostrzeżenia meteorologiczne i hydrologiczne, stany wód)
- Tauron Dystrybucja (wyłączenia prądu)
- Komunikaty i Poradnik bezpieczeństwa (tvp.pl / rządowy poradnik)
- GIOŚ (jakość powietrza)
- Airly (jakość powietrza; rate limit → cache + asynchroniczne odświeżanie co 2h)
- Otwarte mapy (OpenStreetMap) — geokodowanie adresów
- Mapa schronów / miejsc ukrycia (źródło do ustalenia przez backend)
- Do rozważenia: mapy zagrożenia powodziowego (Hydroportal / ISOK, Wody Polskie), otwarte dane Krakowa

## Zespół

- Autor — frontend + integracja agenta AI
- Backend — API, pobieranie danych, scraping, cache
- Pomysł i prezentacja

## Persona

**Persona główna — Marta, 41 lat, księgowa, Dębniki.** Mieszka z dwójką dzieci i mamą po siedemdziesiątce w bloku niedaleko Kobierzyńskiej. Pamięta powodzie z telewizji, ale nie wie, czy jej okolica jest zagrożona, a alerty RCB zwykle odrzuca bez czytania. Gdy coś się dzieje, przegląda Facebooka, stronę IMGW i lokalne portale, i nadal nie wie, co konkretnie ma zrobić. Jej marzenie: „Chcę zapytać po ludzku, co mam zrobić, i dostać konkretną listę rzeczy dla mojej rodziny i mojego adresu, a nie ogólny komunikat dla całego województwa”.


## Ocena z perspektywy persony (Marta)

- **Plus:** jedno miejsce zamiast pięciu stron, odpowiedź „dla mnie”, konkretne kroki zamiast ogólników
- **Plus:** obsługa przed / w trakcie / po zdarzeniu — po powodzi też nie wie, co robić (woda pitna, prąd, zgłoszenie szkody)
- **Wątpliwość:** „Skąd mam wiedzieć, że AI nie zmyśla? Jeśli powie, że nie zaleje, a zaleje?” → odpowiedzi muszą pokazywać źródło i datę danych oraz jasno mówić, czego nie wiadomo
- **Wątpliwość:** „Nie będę sama codziennie pytać — chcę, żeby to mnie ostrzegło” → czy aplikacja jest tylko reaktywna (pytanie → odpowiedź), czy też proaktywna (powiadomienia dla zapisanego adresu)?
- **Wątpliwość:** „Mama nie ogarnie czatu” → prosty interfejs, gotowe przyciski / szybkie pytania, czytelny tekst

## Poufność

- Projekt **nie jest tajny**; repo **publiczne** (link w zgłoszeniu)
- Brak klientów — `client_names_allowed` nie dotyczy
- Dane źródłowe wyłącznie publiczne (strony rządowe i otwarte API)
- **Dane wrażliwe:** adres / lokalizacja użytkownika, treść jego pytań (mogą zdradzać sytuację rodzinną, zdrowotną) → nie logować ich w repo, nie commitować przykładowych rozmów z prawdziwymi danymi
- **Sekrety:** klucze API (LLM, Airly itp.) tylko w `.env`, `.env` w `.gitignore`, w repo tylko `.env.example`
- Zasada hackathonu: wyraźne oddzielenie pracy z HackYeah od wcześniejszej; ujawnienie użycia AI, zewnętrznych API i źródeł danych w zgłoszeniu

## Wnioski i ryzyka

- **Największa wartość i największe ryzyko to ta sama rzecz: personalizacja.** Agent nie może „przewidywać” zalania sam z siebie — musi opierać się na danych (ostrzeżenia IMGW, stany wód, mapy zagrożenia powodziowego) i cytować źródło. Inaczej jury (i Marta) zapyta o odpowiedzialność za błędną radę
- **Twierdzenie o podatnościach Alertu RCB** — jeśli trafi do prezentacji, potrzebuje źródła; bezpieczniej pozycjonować projekt jako **uzupełnienie** RCB (personalizacja, agregacja, wskazówki), a nie jego zastępstwo
- **Scraping (tvp.pl, Tauron)** bywa kruchy i ograniczony regulaminem — na demo potrzebny cache / dane zapasowe, żeby prezentacja nie zależała od cudzych stron
- **Demo musi pokazać konkretną sytuację** (wymóg zadania) — np. scenariusz „wzrost stanu wody, mieszkanka z Dębnik pyta o swoją ulicę”; dane realne albo zasymulowany scenariusz oznaczony jako symulacja
- **Zasięg 24h, 3 osoby** — trzeba twardo ciąć zakres; agregacja kilku źródeł + jeden dopracowany scenariusz > wiele płytkich

## Otwarte pytania / założenia

| # | Temat | Decyzja |
|---|-------|---------|
| P1 | Tryb działania | Tylko odpowiedzi na pytania (reaktywnie). Push / proaktywne ostrzeżenia — w przyszłości, poza PoC |
| P2 | Platforma | Aplikacja webowa (PoC) |
| P3 | Demo | Oba scenariusze: panel **na żywo** (realne dane) + osobna zakładka **Demo** (symulowany scenariusz, oznaczony) |
| P4 | Zagrożenia | Powódź, jakość powietrza, wyłączenia prądu + **mapa schronów**; **pożar i atak bombowy obowiązkowo na demie** |
| P5 | Języki | Tylko polski; angielski w przyszłości |
| P6 | Źródło | „AITLY” = **Airly** |
| P7 | Role | Autor integruje agenta AI; scraping i pobieranie danych — backend |
| P8 | Nazwa | **KryzIO** |
| — | Persona | Tylko persona główna (Marta); poboczna odrzucona |
