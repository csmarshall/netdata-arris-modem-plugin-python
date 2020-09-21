# netdata-arris-surfboard-modem-plugin-python
netdata python.d collector for Arris Surfboard DOCSIS Cable Modem downstream/upstream stats

## To install:
This script scrapes the private admin interface of 192.168.100.1/cmconnectionstatus.html exposed on the cable modem, if your interface is compatible you shouldn't need to do any configuration more than simply copying (or symlinking if your OS supports it) the script into place
1. Stop netdata, OS Specific:
```zsh
user@netdata:/usr/www/netdata % sudo service netdata stop
Password:
netdata stopped.
user@netdata:/usr/www/netdata %
```

2. Checkout the repo:
```zsh
user@netdata:~ % git clone git@github.com:csmarshall/netdata-arris-surfboard-modem-plugin-python.git
Cloning into 'netdata-arris-surfboard-modem-plugin-python'...
remote: Enumerating objects: 13, done.
remote: Counting objects: 100% (13/13), done.
remote: Compressing objects: 100% (12/12), done.
remote: Total 13 (delta 3), reused 8 (delta 0), pack-reused 0
Receiving objects: 100% (13/13), 5.63 KiB | 5.63 MiB/s, done.
Resolving deltas: 100% (3/3), done.
```

3. cd to you're netdata base install dir, This is where you installed netdata, in this example: /usr/www/netdata, but by default this *may* be "/"
```zsh
user@netdata:~ % cd /usr/www/netdata
```

4. Symlink the charts script from your checkout from the checked out repo *into* your netdata install:
```zsh
user@netdata:/usr/www/netdata % sudo ln -s ~/netdata-arris-surfboard-plugin-python/arris_surfboard.chart.py ./usr/libexec/netdata/python.d/arris_surfboard.chart.py
Password:
user@netdata:/usr/www/netdata % ls -la ./usr/libexec/netdata/python.d/arris_surfboard.chart.py
lrwxr-xr-x 1 root daemon 78 Sep 17 15:05 ./usr/libexec/netdata/python.d/arris_surfboard.chart.py -> /home/user/netdata-arris-surfboard-modem-plugin-python/arris_surfboard.chart.py
```

5. OPTIONAL?: Symlink the stub config into place:
```zsh
user@netdata:/usr/www/netdata % sudo ln -sf ~/work/netdata-arris-surfboard-modem-plugin-python/arris_surfboard.conf ./usr/lib/netdata/conf.d/python.d/arris_surfboard.conf
Password:
user@netdata:/usr/www/netdata % ls -la ./usr/lib/netdata/conf.d/python.d/arris_surfboard.conf
lrwxr-xr-x 1 root netdata 86 Sep 17 15:11 ./usr/lib/netdata/conf.d/python.d/arris_surfboard.conf -> /home/user/work/netdata-arris-surfboard-modem-plugin-python/arris_surfboard.conf
```
Then edit the config if you so choose:
```zsh
user@netdata:/usr/www/netdata % cd etc/netdata
user@netdata:/usr/www/netdata/etc/netdata %  sudo ./edit-config python.d/arris_surfboard.conf
```
The only real variable here is the "update_every", which will work to emit a metric every X seconds, my modem takes 9 seconds to respond, so the default "update_every" for the script is 15, with the connect timing out being 3 seconds before.  That way I can update as quickly as possible, with a little buffer added to deal with being nice'd by the OS' scheduler.

6. Test that the plugin works for your modem:
```zsh
user@netdata:/usr/www/netdata/etc/netdata % sudo -u netdata /bin/bash /usr/www/netdata/usr/libexec/netdata/plugins.d/python.d.plugin arris_surfboard debug trace
Password:
```
This will update to the console, an example is given in examples/debug_output.txt


7. Restart netdata, obviously this is OS specific:
```zsh
user@netdata:/usr/www/netdata % sudo service netdata restart
netdata not running? (check /usr/www/netdata/var/run/netdata/netdata.pid).
Starting netdata.
2020-09-17 13:34:07: netdata INFO  : MAIN : SIGNAL: Not enabling reaper
user@netdata:/usr/www/netdata %
```

8. Profit 😎
![Plugin Screenshot](/examples/Screen%20Shot%202020-09-17%20at%2021.26.10.png)

## Notes:
* This is for the [Arris Surfboard Family](https://www.arris.com/surfboard/products/cable-modems/) family of DOCSIS Cable Modems, I tested with the [SB8200](https://www.arris.com/surfboard/products/cable-modems/sb8200/) but I have a loose memory of this similar UI existing in previous generations, and possibly even legacy Motorola surfboard devices, though there might need to be some slight modifications due to HTML changes.
* If you're looking for other Arris cable modem products you may want to look at @theY4Kman's [plugin](https://github.com/theY4Kman/netdata-arris-modem-plugin-python), it was the starting point for this script, and hopefully should work if your modem exposes a "cgi-bin" style status page.
* My modem seems to have a roughly 9~ second delay when querying these stats:
```zsh
% for A in {1..100}; do echo "${A},$(curl -w '%{time_total}\n' -o /dev/null -s http://192.168.100.1/cmconnectionstatus.html)" ; done | recs fromcsv -k run,time | recs collate -a p50_time=perc,50,time
{"p50_time":"8.797505"}
```
As a result, I've increase the default interval to 15 seconds to be safe, but you may want to tweak it, but for me this seems like a happy medium, as far as I know there's no impact to the dataplane of the modem from querying these stats so frequently.
* I've added arris_surfboard_swinfo.chart.py to record the uptime and sofware revision of the modem in a seperate set of graphs (I didn't spend the time to get it into the same set of graphs)

## Todo:
* Alarms for modem uptime, or software changes?
* Possibly submit this upstream?
* Change the default icon in the UI?
* See if there's a way to reduce the interval?
