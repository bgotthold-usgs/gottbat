# Nabat-Acoustic-ML

## Installing Python

```
brew install xz

env \
PATH="$(brew --prefix tcl-tk)/bin:$PATH" LDFLAGS="-L$(brew --prefix tcl-tk)/lib" CPPFLAGS="-I$(brew --prefix tcl-tk)/include" PKG_CONFIG_PATH="$(brew --prefix tcl-tk)/lib/pkgconfig" CFLAGS="-I$(brew --prefix tcl-tk)/include" PYTHON_CONFIGURE_OPTS="--with-tcltk-includes='-I$(brew --prefix tcl-tk)/include' --with-tcltk-libs='-L$(brew --prefix tcl-tk)/lib -ltcl8.6 -ltk8.6' --enable-framework" pyenv install 3.7.10
```

## Building for macOS 10.15.7 Catalina

```
bash build_macOS.sh
```

## gottbat cli

```
python3 nabat_ml_cli.py -p ~/Downloads/Example_calls/test -g 77474 -u df3048a2-fa0e-11eb-9528-02fb14f25dd5
```

## Recording audio on Pi

```
arecord -d 10 -f S16 -r 384000 -t wav --device plughw:Ultr ~/wav/new.wav -c 1
```

## Tensorflow on Pi

https://www.bitsy.ai/3-ways-to-install-tensorflow-on-raspberry-pi/

```
pip3 install https://github.com/bitsy-ai/tensorflow-arm-bin/releases/download/v2.4.0-rc2/tensorflow-2.4.0rc2-cp37-none-linux_armv7l.whl
```

@reboot echo "$(date)" >> ~/boot.txt
@reboot bash /home/pi/NABat/gottbat/process.sh
@reboot bash /home/pi/NABat/gottbat/record.sh
