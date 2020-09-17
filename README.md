# netdata-arris-sb8200-modem-plugin-python
netdata python.d collector for Arris Surfboard 8200 Modem downstream/upstream stats

## Notes:
* My modem seems to have a roughly 9~ second delay when querying these stats:
```zsh
% for A in {1..100}; do echo "${A},$(curl -w '%{time_total}\n' -o /dev/null -s http://192.168.100.1/cmconnectionstatus.html)" ; done | recs fromcsv -k run,time | recs collate -a p50_time=perc,50,time
{"p50_time":"8.797505"}
```
As a result, I've increase the default interval to 20 seconds to be safe, you may want to tweak it, but for me this seems like a happy medium, as far as I know there's no impact to the dataplane of the modem from querying these stats so frequently.
* I only have a Surfboard 8200, but possibly any Surfboard modem that supports the "cmconnectionstatus.html" page may work.
* I can't thank @theY4Kman enough for the initial framework, [his plugin]|(https://github.com/theY4Kman/netdata-arris-modem-plugin-python) should hopefully work if your modem exposes a "cgi-bin" style status page.

## Todo:
* Fix the graphs...
* Instructions to install
* Change the default icon?
* See if there's a way to reduce the interval?