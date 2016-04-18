# [PiClockRadio](http://www.jdhp.org/projects_en.html)

Copyright (c) 2013,2014 Jeremie DECOCK (http://www.jdhp.org)

## Description

TODO...

## Dependencies

- python-feedparser
- soft-on-off-screen-switch (https://github.com/jeremiedecock/soft-on-off-screen-switch)

## Install

TODO...

## Create a dedicated user

adduser piclockradio ... TODO...

This user have to be in group audio (and video, plugdev, input ?)
It's recommanded to automatically start Xserver and automatically logon
piclockradio in Xserver at startup (see rpi-config script). <TODO>

As specified in `screen_on` script:

    POWER MANAGEMENT SHOULD BE DISABLED IN `/etc/xdg/lxsession/LXDE/autostart`:

```
 @xset s off
 @xset -dpms
```

(power management can be reset manually from ssh with `DISPLAY=:0 xset s reset`)

Additionally, you should remove the xscreensaver line.

## TODO

- Debian package
- Complete this file (see <TODO> tags)

## Crontab example

```
0 8 * * 1-5   ogg123 -d au -f - /usr/share/sounds/piclockradio/test.oga | aplay

# Radio (new version) ###

#mon
15 7 * * 1   DISPLAY=:0 /usr/bin/piclockradio -r mpr -d 7200
#thu
15 7 * * 2   DISPLAY=:0 /usr/bin/piclockradio -r mpr -d 7200
#wed
15 8 * * 3   DISPLAY=:0 /usr/bin/piclockradio -r mpr -d 3600
#tue
15 7 * * 4   DISPLAY=:0 /usr/bin/piclockradio -r mpr -d 7200
#fri
15 7 * * 5   DISPLAY=:0 /usr/bin/piclockradio -r mpr -d 7200

# Radio (former version) ###

#mon
15 6 * * 1   /usr/bin/radio_mpr.sh 7200
#thu
15 6 * * 2   /usr/bin/radio_mpr.sh 7200
#wed
15 7 * * 3   /usr/bin/radio_mpr.sh 3600
#tue
15 6 * * 4   /usr/bin/radio_mpr.sh 7200
#fri
15 6 * * 5   /usr/bin/radio_mpr.sh 7200

# Speach ###

17 8 * * 3         echo "It's time to wake up." | festival --tts

# alarm at 9pm (sun to thur)

0 21 * * 0-4   aplay /usr/share/sounds/piclockradio/test.wav
```

## License

PiClockRadio is distributed under the [MIT License](http://opensource.org/licenses/MIT).
