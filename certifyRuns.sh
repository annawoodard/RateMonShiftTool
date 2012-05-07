#!/bin/bash 
#Usage ./certifyRuns.sh runList TriggerList firstFitRun lastFitRun fitFile fitRootFile JSONFile

runList=runList.txt
TriggerList=monitorlist_Apr_Core_2012.list
firstFitRun=190782
lastFitRun=191276
fitFile=Fits/2012/Fit_HLT_NoV_10LS_Run${firstFitRun}to${lastFitRun}.pkl
fitRootFile=HLT_10LS_delivered_vs_rate_Run${firstFitRun}-${lastFitRun}.root
JSONFile=Cert_190456-191276_8TeV_PromptReco_Collisions12_JSON.txt

if [ $# -ge 1 ]; then
    runList=${1}
fi
if [ $# -ge 2 ]; then
    TriggerList=${2}
fi
if [ $# -ge 3 ]; then
    firstFitRun=${3}
fi
if [ $# -ge 4 ]; then
    lastFitRun=${4}
fi
if [ $# -ge 5 ]; then
    fitFile=${5}
fi
if [ $# -ge 6 ]; then
    fitRootFile=${6}
fi
if [ $# -ge 7 ]; then
    JSONFile=${7}
fi

echo Certifying runs from file $runList
echo Using Trigger List $TriggerList from run $firstFitRun to $lastFitRun 
echo Fit files are $fitFile $fitRootFile 
echo JSON file is $JSONFile

#if fit file doesn't exist, make it!!!
if [ ! -f $fitFile ]; then
    echo Fit file do not exist, creating
    ./DatabaseRatePredictor.py --makeFits --TriggerList=$TriggerList --linear --NoVersion --json=$JSONFile ${firstFitRun}-${lastFitRun}
    echo Done making fit file.
fi

for run in `cat $runList` 
  do
  echo Producing Plots for run $run
  ./DatabaseRatePredictor.py --Beam --secondary --TriggerList=${TriggerList} --fitFile=${fitFile} ${run}
  root -b -l -q 'dumpToPDF.C("HLT_1LS_ls_vs_rawrate_Run'${run}'-'${run}'.root", "'${fitRootFile}'")'  
  
done

echo Done.