#!/bin/sh
# create  sfcsm location conf and scripts

INKPATHETC='/opt/sfcsm/etc'
INKPATHBIN='/opt/sfcsm/bin'

mkdir -pv $INKPATHETC $INKPATHBIN
cp sfcsm-template.conf $INKPATHETC/sfcsm.conf
cp sfcsmProbe/cephprobe.py $INKPATHBIN
cp sfcsmProbe/sysprobe.py  $INKPATHBIN
cp sfcsmProbe/daemon.py  $INKPATHBIN
