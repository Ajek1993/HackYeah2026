# 03 — User stories (runda 1)

> KryzIO · tryb uproszczony · model pyta, autor odpowiada

## US-01 · Adres poza Krakowem
Jako Marta chcę zapytać o zalanie działki mamy w Skawinie (tuż za granicą Krakowa), żeby wiedzieć, czy jechać ją zabezpieczyć.

**Pytanie:** Co agent robi, gdy pytanie dotyczy miejsca poza Krakowem — odmawia, odpowiada „Brak danych”, czy próbuje odpowiedzieć na podstawie danych regionalnych (np. ostrzeżenia IMGW dla powiatu)?

**Odpowiedź:** Komunikat, że apliakacja jest dostępna narazie tylko na terenie Krakowa.

## US-02 · Pytanie spoza tematu
Jako Marta, po otrzymaniu odpowiedzi o powodzi, pytam agenta „a jaki przepis na pierogi poleciłbyś?” albo „kto wygra wybory?”.

**Pytanie:** Jak agent reaguje na pytania niezwiązane z bezpieczeństwem — grzecznie odmawia i wraca do tematu, czy odpowiada normalnie?

**Odpowiedź:** Grzecznie odmawia i wrca do tematu, krótko, daje ostrzeżenie zeby nie marnrowac tokenów.

## US-03 · Zagrożenie życia teraz
Jako Marta piszę w panice: „Woda wlewa się do piwnicy, mama nie może zejść ze schodów, co robić?!”.

**Pytanie:** Czy w sytuacji bezpośredniego zagrożenia agent ma najpierw (i wyraźnie, np. czerwonym banerem) kazać dzwonić na 112, zanim poda jakiekolwiek inne kroki? Czy coś jeszcze ma się wtedy zmienić w interfejsie?

**Odpowiedź:** dzwoń 112 + poradnik co ma robić w przypadku powodzi

## US-04 · Sprzeczne lub nieaktualne dane
Jako Marta pytam o jakość powietrza na Dębnikach, a Airly (cache sprzed 2h) pokazuje „dobra”, a GIOŚ (świeższe dane) „zła”.

**Pytanie:** Co agent pokazuje, gdy źródła się różnią albo dane są stare — oba wyniki z datami, tylko najświeższy, czy najgorszy (zasada ostrożności)? Od ilu godzin dane uznajemy za nieaktualne?

**Odpowiedź:** najświezszy

## US-05 · Odpowiedzialność za radę
Jako Marta dostaję od agenta odpowiedź „Na Kobierzyńskiej nie ma obecnie ostrzeżenia powodziowego”, zostaję w domu, a w nocy ulicę zalewa.

**Pytanie:** Jak agent ma formułować odpowiedzi, żeby nie dawać fałszywego poczucia bezpieczeństwa? Czy każda odpowiedź ma mieć stały dopisek (np. „KryzIO nie zastępuje komunikatów służb — w razie zagrożenia słuchaj RCB / 112”)? Kto w prezentacji „bierze odpowiedzialność” za treść rad?

**Odpowiedź:** ma mieć dopisek że nie zastępuje służb. System państowy jest nadrzednuy, kryzio jest tylko uzupłenieniem tego sytemu i wspraciem w komuniakcji.

## US-06 · Demo pomylone z rzeczywistością
Jako Marta otwieram zakładkę Demo, uruchamia się scenariusz ataku bombowego, robię zrzut ekranu i wysyłam rodzinie na WhatsAppie bez kontekstu.

**Pytanie:** Jak mocno oznaczamy symulację — czy wystarczy baner „SYMULACJA”, czy np. znak wodny na całym ekranie (widoczny na zrzucie), inny kolor całej aplikacji, potwierdzenie przy wejściu do Demo?

**Odpowiedź:** Demo będzie tylko na prezentacjiu, w docelowej apliajci nie bedzie dema!!

## US-07 · Źródło nie działa w trakcie prezentacji
Jako członek zespołu prezentuję KryzIO jury, a strona IMGW / Tauron akurat nie odpowiada albo zmieniła układ i scraping się wysypał.

**Pytanie:** Co widzi użytkownik w panelu na żywo i w czacie, gdy jedno ze źródeł jest niedostępne — ostatnie zapisane dane z oznaczeniem daty, komunikat „źródło niedostępne”, czy ukrywamy ten kafelek?

**Odpowiedź:** ostatnie dane z datą wyraźnie zaznaczoną że to sprzed jakeigos czasu.

## US-08 · Senior i dostępność
Jako mama Marty (74 lata, słaby wzrok) dostaję telefon od córki z otwartym KryzIO i mam sama sprawdzić, gdzie jest najbliższy schron.

**Pytanie:** Jakie minimum dostępności przyjmujemy na PoC — duża czcionka / tryb wysokiego kontrastu, odczyt odpowiedzi na głos, wpisywanie głosem? Co z tego jest MVP, a co przyszłością?

**Odpowiedź:** narazie tylko duża czcionka i dobry kontrtast

## Wnioski z rundy

- **Zasięg:** zapytania o miejsca poza Krakowem → stały komunikat „KryzIO działa na razie tylko na terenie Krakowa” (bez prób odpowiedzi z danych regionalnych)
- **Off-topic:** krótka, grzeczna odmowa + powrót do tematu bezpieczeństwa; odpowiedź krótka, żeby nie zużywać tokenów (limit długości odpowiedzi off-topic)
- **Zagrożenie życia:** wykrycie sytuacji „tu i teraz” → na górze wyraźny komunikat „Dzwoń 112”, pod nim kroki z poradnika dla danego typu zdarzenia (np. powódź)
- **Konflikt źródeł:** pokazujemy **najświeższy** odczyt (z datą i źródłem)
- **Próg nieaktualności (propozycja do potwierdzenia):** dane starsze niż 3h oznaczamy jako nieaktualne
- **Dopisek prawny przy każdej odpowiedzi:** „KryzIO nie zastępuje komunikatów służb. Nadrzędny jest państwowy system ostrzegania (RCB, 112) — KryzIO jest jego uzupełnieniem i wsparciem w komunikacji.” — ta sama narracja w prezentacji
- **Demo:** zakładka Demo istnieje **tylko w wersji prezentacyjnej** (włączana flagą konfiguracyjną); w docelowej aplikacji nie ma trybu Demo → US-06 przestaje być ryzykiem produkcyjnym, w wersji prezentacyjnej wystarczy baner SYMULACJA
- **Źródło niedostępne:** pokazujemy ostatnie zapisane dane z wyraźnym oznaczeniem „dane sprzed X godz.” (w czacie i panelu)
- **Dostępność PoC:** duża czcionka i dobry kontrast (WCAG AA); odczyt głosowy i wpisywanie głosem — przyszłość
