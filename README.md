# hybrid-video-topology
Unifying the best of p2p, SFU and MCUs topologies.


Roadmap
-------

Innen 14. juni: Fullføre experiments
Innen 17. juni: Fullføre suggested solution
Innen 20. juni: Solution må virke
Innen 23. juni: Fullføre background/intro/konk
Innen 25. juni: Dra ting sammen og lese korrektur
Innen 27. juni: Sommerferie?


Lab tc
------

Hosts med tc-tilgang: 02 04 06 08 09 10 13 14 15 16 17 19 21 22 27 28 30

Labprosedyre:
    * Kjør ntpdate -q no.pool.ntp.org for å finne lokalt offset
    * Kjør clock.py som kontinuerlig printer lokal tid med ms
    * På hver host, beregn inngående latency fra hva som blir sett på skjermen fra alle andre (Fra graphicsmagick: import -window root screen.png)
    * Kjør regelmessige dumps av sendte bytes på hver maskin, slik at deltaet utgjør brukt båndbredde.
    * ???
    * Profit!

### Chrome

Trenger chrome, last ned .deb, pakk ut til en lokal mappe og kjør derfra (ligger nå som chrome.sh på shared root-boksene).

Må settes opp fra "scratch" på hver PC siden de ikke kan kjøres samtidig med delt mappe, opprettes derfor en mappe i /tmp hvor innstillingene lagres.

### Hangouts

Logg inn som en bruker, start samtale, del skjerm, kjør ntpdate -q no.pool.ntp.org og python clock.py
Mål data

### appear.in

Start chrome, gå til url, kjør capture.sh-skriptet.
