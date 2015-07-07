# μz
μz is a mania-style rhythm game, written in Python 2.7 using Pygame. It can load beatmaps from [**osu!**](https://osu.ppy.sh/) (osu!mania mode), [**SIFTrain**](https://github.com/kbz/SIFTrain) and [**LLpractice**](https://github.com/yjhatfdu/LLpractice), as well as its own beatmap format. Support for other formats may be added in the future.

μz also features a simple (but useful) tool to assist with beatmap creation, BeatmapBuilder. Currently, it can export beatmaps in μz and SIFTrain formats.

# Installation
You must have [Python 2.7](https://www.python.org/) and [Pygame 1.9.1](http://pygame.org/) or higher in order to run μz. Python 3 and above is not supported; lower versions of Pygame may work, but are not tested

**Note:** there are currently no official builds of Pygame for 64bit Windows systems. If you use Win64, you'll have to either install the 32bit version of Python, or an unofficial 64bit version of Pygame from [here](http://www.lfd.uci.edu/~gohlke/pythonlibs/).

Installing μz is optional, you can simply run it using the **run.py** file found in this repository.

If you want to install μz system-wide, run the following command inside the repository folder:
    
    ./setup.py install

or:

    ./setup.py develop
    
The installation requires the [**setuptools**](https://pypi.python.org/pypi/setuptools) Python package. You may need root/administrator privileges to execute those commands. If you're on Windows, omit the ./ prefix. The later command will link your muz installation with the git repository clone folder, so you can update it later by simply running ```git pull```.

# Running
Currently, μz has no graphical user interface, except for the actual game part. It must be invoked from the command line, and its behaviour is controlled with command line arguments and a configuration file.

In this guide, ```muz``` will refer to the command used to run the game. If you installed μz as described in the previous section, you'll instead have to run

    python2 -m muz

, where python2 is the Python 2.7 interpreter executable. If you did not, then use

    ./run.py

If you run μz without arguments, it will print an unhelpful help message with a list of options and exit.

To play a specific beatmap, run:

    muz "name of the beatmap (case-sensitive)"

To list all installed beatmaps, run:

    muz -l

On decent operating systems, you can filter the output with ```grep``` to find a specific beatmap:

    muz -l | grep -i "binetsu"

To play a beatmap with note positions randomized:

    muz --random "beatmap"

Replace all holds with two simple notes:

    muz --no-holds "beatmap"
    
Play in "insane" mode, where extra notes are added to the beatmap:

    muz --insane "beatmap"

Let the computer play by itself perfectly and enjoy the show:

    muz --autoplay "beatmap"
    
You can, of course, combine any of those options:

    muz --autoplay --random --insane "beatmap"

# Beatmaps
μz comes with no beatmaps by default, you'll have to obtain them yourself. Once obtained, they have to be placed in the **μz user directory**: ```~/.muz/```, or  ```C:\Users\yourname\.muz\``` on Windows. If this directory doesn't exist, create it.

A few beatmaps known to work with μz can be found [**here**](http://thebadasschoobs.org/static/muz/).

Source files for beatmaps made for μz can be found [**here**](https://github.com/nexAkari/muz-beatmaps).

### osu!
osu! beatmaps can be downloaded [**here**](https://osu.ppy.sh/p/beatmaplist).

You must have an osu! account in order to download any beatmaps, at least from the official site. The registration is free, however, it's required that you log into osu! at least once to activate your account.

Most osu!mania beatmaps are supported. Non-mania maps may work, but are not guaranteed to be playable.

To install osu! beatmaps, simply place the osz files into the user directory, as mentioned above. Note that the osz filename usually doesn't match with the name of the beatmap(s) it contains. Use ```muz -l``` to find the actual beatmap name(s).

### SIFTrain
SIFTrain beatmaps can be found in [**this repository**](https://github.com/kbz/beatmap-repo). They are beatmaps from Love Live! School Idol Festival, and come with no music - you'll have to obtain it yourself.

To install these beatmaps, create a ```beatmaps``` directory inside the user directory. Inside that directory, also create the ```datafiles``` and ```soundfiles``` directories. Put the beatmaps (```.rs``` files) in ```beatmaps/datafiles```, and the music in ```beatmaps/soundfiles```. The naming convention is just like in SIFTrain: the music files should have the same name as the beatmaps they are used by, minus the difficulty suffix. Either ogg or mp3 should work for the music format, but ogg is prefered.

### LLpractice
μz can automatically download and install beatmaps from [m.tianyi9.com](https://m.tianyi9.com/#/index). Visit the site and click on the song you want to get. Look at the URL, there should be a **live_id** parameter. Copy its value, and run:

    python2 -m muz.beatmap.formats.tianyi9 ID

, where **ID** is the value of **live_id** from the URL. The download may take a while, be patient. After it's done, the beatmap should appear in ```muz -l```.

# Configuration
μz can be customized with a configuration file. The config location can be specified with the ```--config``` argument. By default, it's the ```config.json``` file inside the μz user directory. This file doesn't exist by default - you have to create it if you want to change settings. μz will write a ```config.default.json``` file containing the default settings inside the user directory every time it's ran. You can copy this file as ```config.js``` and then edit the later. If your custom config is missing any settings, the default values for them will be used. If it contains any unrecognized settings or values of invalid type, you'll get a warning when the game is ran.

# Known issues
 * Support for mp3 files is limited, [as stated in the Pygame documentation](https://www.pygame.org/docs/ref/music.html). For this reason, μz will try to load an ogg file of the same name whenever a beatmap wants to play an mp3 file. If you have issues with mp3 playback, try to re-encode the offending file in OGG Vorbis and put it in ```~/.muz/beatmaps``` or wherever the beatmap expects it to be in. μz can convert mp3s automatically if you have [**pydub**](http://pydub.com/) and [**ffmpeg**](https://www.ffmpeg.org/) installed. This feature is, however, disabled by default, because it's not always needed. If you want to use it, you have to enable the **"auto-convert-mp3"** option under the **"vfs"** section in the configuration file.
