#!/bin/bash

rm -rf build dist
python --version
python setup.py py2app -i "pkg_resources.py2_warn" -p "llvmlite,spectrogram,prediction,librosa,tensorflow,matplotlib,scipy,resampy,sklearn,numpy,h5py,tkinter,requests" 
nl=$'\n'
sed -i '' 's|import site as _site|import site as _site'"\\${nl}"'_site.ENABLE_USER_SITE = True|' dist/nabat_ml_gui.app/Contents/Resources/lib/python3.7/tensorflow/__init__.py
cp build_deps/liblzma.5.dylib dist/nabat_ml_gui.app/Contents/Frameworks/liblzma.5.dylib
cp build_deps/libsndfile.dylib dist/nabat_ml_gui.app/Contents/Frameworks/libsndfile.dylib