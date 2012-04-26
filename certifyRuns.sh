 #!/bin/bash 

for run in `cat runList.txt` 
  do
  echo Producing Plots for run $run
  ./DatabaseRatePredictor.py --secondary --TriggerList=monitorlist_Apr_Core_2012.list --fitFile=Fits/2012/Fit_HLT_NoV_10LS_Run190782to191276.pkl ${run}
  root -b -l -q 'dumpToPDF.C("HLT_1LS_ls_vs_rawrate_Run'${run}'-'${run}'.root")'  
  
done
