# hybrid-video-topology
Unifying the best of p2p, SFU and MCUs topologies.


Roadmap
-------

By 25.03: Have benchmarked existing solutions, found their bandwidth utilization, latency and CPU usage in the example conversations.

By 06.04: Have finalized the algorithm for route selection, but maybe with imperfect parameters. Write about the physical test setup.

By 06.05: Have tested the algorithm on the example setup to find the best parameters

By 13.05: Finalized the introduction, background and experiments chapters

By 20.05: Write the results and discussion chapters

By 27.05: Finalize the rest

By 04.06: Get feedback and incorporate changes

Lab tc
------

Hosts med tc-tilgang: 02 04 06 08 09 10 13 14 15 16 17 19 21 22 27

Labprosedyre:
    * Kjør ntpdate -q no.pool.ntp.org for å finne lokalt offset
    * Kjør clock.py som kontinuerlig printer lokal tid med ms
    * På hver host, beregn inngående latency fra hva som blir sett på skjermen fra alle andre (Fra graphicsmagick: import -window root screen.png)
    * Kjør regelmessige dumps av sendte bytes på hver maskin, slik at deltaet utgjør brukt båndbredde.
    * ???
    * Profit!

### Hangouts

Trenger chrome, last ned .deb, pakk ut til en lokal mappe og kjør derfra (ligger nå som chrome.sh på shared root-boksene).
Logg inn som en bruker, start samtale, del skjerm, kjør ntpdate -q no.pool.ntp.org og python clock.py
Mål data
