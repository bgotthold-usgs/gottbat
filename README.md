# NABat Acoustic ML

This is a application developed to process full spectrum .wav files based on ML research conducted by the NABat Team.

## Requirements

- python 3.7 or later
- OS level windowing system compatible with tkinter

  ```
      pip3 install -r requirements.txt
  ```

### Installing Standalone Python with Pyenv and Brew on MacOS

```
brew install xz, pyenv

env \
PATH="$(brew --prefix tcl-tk)/bin:$PATH" LDFLAGS="-L$(brew --prefix tcl-tk)/lib" CPPFLAGS="-I$(brew --prefix tcl-tk)/include" PKG_CONFIG_PATH="$(brew --prefix tcl-tk)/lib/pkgconfig" CFLAGS="-I$(brew --prefix tcl-tk)/include" PYTHON_CONFIGURE_OPTS="--with-tcltk-includes='-I$(brew --prefix tcl-tk)/include' --with-tcltk-libs='-L$(brew --prefix tcl-tk)/lib -ltcl8.6 -ltk8.6' --enable-framework" pyenv install 3.7.10
```

## Running GUI Application

```
python3 nabat_ml_gui.py
```

## Running as library

```
# -p path to directory containing wav files
# -g GRTS Cell ID
# -u detector identifier if streaming results

python3 nabat_ml_cli.py -p ~/Downloads/Example_calls/test -g 77474 -u df3048a2-fa0e-11eb-9528-02fb14f25dd5
```

## Building standalone application for macOS 10.15.7 Catalina

```
bash build_macOS.sh
```

## Provisional Software Statement

Under USGS Software Release Policy, the software codes here are considered preliminary, not released officially, and posted to this repo for informal sharing among colleagues.

This software is preliminary or provisional and is subject to revision. It is being provided to meet the need for timely best science. The software has not received final approval by the U.S. Geological Survey (USGS). No warranty, expressed or implied, is made by the USGS or the U.S. Government as to the functionality of the software and related material nor shall the fact of release constitute any such warranty. The software is provided on the condition that neither the USGS nor the U.S. Government shall be held liable for any damages resulting from the authorized or unauthorized use of the software.
