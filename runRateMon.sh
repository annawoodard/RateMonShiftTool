#!/bin/bash

while true; do

  clear
  echo -n "Script was last run  "
  date

  /nfshome0/slaunwhj/RateMon/stable/RateMonitorShifter.py --CompareRun=167102 --ConfigFile="$PWD/allLumis.cfg"

  sleep 30s

done