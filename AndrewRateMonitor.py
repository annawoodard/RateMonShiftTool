#!/usr/bin/env python

from AndrewGetRun import GetRun
from AndrewWBMParser import AndrewWBMParser
from ReadConfig import RateMonConfig
import sys
import os
import cPickle as pickle
import getopt
import time
from colors import *
from TablePrint import *
from math import *

WBMPageTemplate = "http://cmswbm/cmsdb/servlet/RunSummary?RUN=%s&DB=cms_omds_lb"
WBMRunInfoPage = "https://cmswbm/cmsdb/runSummary/RunSummary_1.html"

RefRunNameTemplate = "RefRuns/Run_%s.pk"

def usage():
    print sys.argv[0]+" [Options]"
    print "This script gets the current HLT trigger rates and compares them to a reference run"
    print "Options: "
    print "--AllowedDiff=<diff>                 Report only if difference in trigger rate is greater than <diff>% (Default = "+str(DefaultAllowedRateDiff*100)+"% )"
    print "--CompareRun=<Run #>                 Compare run <Run #> to the reference run (Default = Current Run)"
    print "--FindL1Zeros                        Look for physics paths with 0 L1 rate"    
    print "--FirstLS=<ls>                       Specify the first lumisection to consider. This will set LSSlidingWindow to -1"
    print "--LastLS=<ls>                        Specify the last lumisection to consider. Make sure LastLS > LSSlidingWindow"
    print "                                        or set LSSlidingWindow = -1"  
    print "--IgnoreLowRate=<rate>               Ignore triggers with an actual and expected rate below <rate> (Default = "+str(DefaultIgnoreThreshold)+")"
    print "--ListIgnoredPaths                   Prints the paths that are not compared by this script and their rate in the CompareRun"
    print "--PrintLumi                          Prints Instantaneous, Delivered, and Live lumi by LS for the run"
    print "--RefRun=<Run #>                     Specifies <Run #> as the reference run to use (Default in defaults.cfg)"
    print "--ShowPSTriggers                     Show prescaled triggers in rate comparison"
    print "--help                               Print this help"
    
def main():
    try:
        opt, args = getopt.getopt(sys.argv[1:],"",["AllowedDiff=","CompareRun=","FindL1Zeros",\
                                                   "FirstLS=","LastLS=","IgnoreLowRate=","ListIgnoredPaths",\
                                                   "PrintLumi","RefRun=","ShowPSTriggers","help"])
    except getopt.GetoptError, err:
        print str(err)
        usage()
        sys.exit(2)

    Config = RateMonConfig(os.path.abspath(os.path.dirname(sys.argv[0])))
    for o,a in opt:
        if o=="--ConfigFile":
            Config.CFGfile=a
    Config.ReadCFG()
     
    AllowedRateDiff   = Config.DefAllowRateDiff
    CompareRunNum     = ""
    FindL1Zeros       = True
    FirstLS           = 999999
    LastLS            = 111111
    IgnoreThreshold   = Config.DefAllowIgnoreThresh
    ListIgnoredPaths  = False
    PrintLumi         = False
    RefRunNum         = int(Config.ReferenceRun)
    ShowPSTriggers    = True

    if Config.LSWindow > 0:
        FirstLS = -1*Config.LSWindow

    for o,a in opt: # get options passed on the command line
        if o=="--AllowedDiff":
            AllowedRateDiff = float(a)/100.0
        elif o=="--CompareRun":
            CompareRunNum=int(a)
        elif o=="--FindL1Zeros":
            FindL1Zeros = True
        elif o=="--FirstLS":
            FirstLS = int(a)
        elif o=="--LastLS":
            LastLS = int(a)
        elif o=="--IgnoreLowRate":
            IgnoreThreshold = float(a)
        elif o=="--ListIgnoredPaths":
            ListIgnoredPaths=True
        elif o=="--PrintLumi":
            PrintLumi = True
        elif o=="--RefRun":
            RefRunNum=int(a)
        elif o=="--ShowPSTriggers":
            ShowPSTriggers=True
        elif o=="--help":
            usage()
            sys.exit(0)
        else:
            print "Invalid Option "+a
            sys.exit(1)

    RefLumisExists = False
    if RefRunNum > 0:
        RefRates = {}
        for Iterator in range(1,100):

            if RefLumisExists:  ## Quits at the end of a run
                if max(RefLumis[0]) <= (Iterator+1)*10:
                    break

            RefRunFile = RefRunNameTemplate % str( RefRunNum*100 + Iterator )  # place to save the reference run info

            if not os.path.exists(RefRunFile[:RefRunFile.rfind('/')]):  # folder for ref run file must exist
                print "Reference run folder does not exist, please create" # should probably create programmatically, but for now force user to create
                print RefRunFile[:RefRunFile.rfind('/')]
                sys.exit(0)

            if not os.path.exists(RefRunFile):  # if the reference run is not saved, get it from wbm
                print "Reference Run File for run "+str(RefRunNum)+" iterator "+str(Iterator)+" does not exist"
                print "Creating ..."
                try:
                    RefParser = GetRun(RefRunNum, RefRunFile, True, Iterator*10, (Iterator+1)*10)
                except:
                    print "GetRun failed from LS "+str(Iterator*10)+" to "+str((Iterator+1)*10)
                    continue
                    
            else: # otherwise load it from the file
                RefParser = pickle.load( open( RefRunFile ) )

            if not RefLumisExists:
                RefLumis = RefParser.LumiInfo
                RefLumisExists = True

            try:
                RefRates[Iterator] = RefParser.TriggerRates # get the trigger rates from the reference run
                LastSuccessfulIterator = Iterator
            except:
                print "Failed to get rates from LS "+str(Iterator*10)+" to "+str((Iterator+1)*10)


    # OK, Got the Reference Run
    # Now get the most recent run

    SaveRun = False
    if CompareRunNum=="":  # if no run # specified on the CL, get the most recent run
        RunListParser = AndrewWBMParser()

        RunListParser._Parse(WBMRunInfoPage)  # this is the page that lists all the runs in the last 24 hours with at least 1 trigger
        RunListPage = RunListParser.ParsePage1()
        if RunListPage == '':  # this will be '' if the mode of the most recent run is not l1_hlt_collisions/v*
            print "Most Recent run, "+str(RunListParser.RunNumber)+", is NOT collisions"
            sys.exit(0) # maybe we should walk back and try to find a collisions run, but for now just exit
        CompareRunNum = RunListParser.RunNumber
        print "Most Recent run is "+CompareRunNum

    HeadRunFile = RefRunNameTemplate % CompareRunNum

    if os.path.exists(HeadRunFile):  # check if a run file for the run we want to compare already exists, it probably won't but just in case we don't have to interrogate WBM
        HeadParser = pickle.load( open( HeadRunFile ) )
    else:
        HeadParser = GetRun(CompareRunNum,HeadRunFile,SaveRun,FirstLS,LastLS)

    if PrintLumi:
        for LS in HeadParser.LumiInfo[0]:
            try:
                if (LS < FirstLS or LS > LastLS) and not FirstLS==999999:
                    continue
                print str(LS)+'  '+str(round(HeadParser.LumiInfo[2][LS],1))+'  '+str(round((HeadParser.LumiInfo[3][LS] - HeadParser.LumiInfo[3][LS-1])*1000/23.3,0))+'  '+str(round((HeadParser.LumiInfo[4][LS] - HeadParser.LumiInfo[4][LS-1])*1000/23.3,0))
            except:
                print "Lumisection "+str(LS-1)+" was not parsed from the LumiSections page"
                                                                                                                                 
        sys.exit(0)
    if RefRunNum == 0:
        RefRates = 0
        RefLumis = 0
        LastSuccessfulIterator = 0

    RunComparison(HeadParser,RefRunNum,RefRates,RefLumis,LastSuccessfulIterator,ShowPSTriggers,AllowedRateDiff,IgnoreThreshold,Config)

    if FindL1Zeros:
        L1Zeros=[]
        for key in HeadParser.TriggerRates:
            ## Skip events in the skip list
            skipTrig=False
            ##for trig in Config.ExcludeList:
                ##if not trigN.find(trig) == -1:
                    ##skipTrig=True
                    ##break
            if skipTrig:
                continue
                ## if no events pass the L1, add it to the L1Zeros list if not already there
            if HeadParser.TriggerRates[key][1]==0 and not HeadParser.TriggerRates[key][4] in L1Zeros:
                L1Zeros.append(HeadParser.TriggerRates[key][4])
        if len(L1Zeros) == 0:
            print "It looks like no masked L1 bits seed trigger paths"
        else:
            print "The following seeds are used to seed HLT bits but accept 0 events:"
            print "The average lumi of this run is: "+str(round(HeadParser.LumiInfo[6],1))+"e30"
            for Seed in L1Zeros:
                print Seed

            
def RunComparison(HeadParser,RefRunNum,RefRates,RefLumis,Iterator,ShowPSTriggers,AllowedRateDiff,IgnoreThreshold,Config):

    Header = ["Trigger Name","Actual","Expected","% Inc","Cur PS","Comments"]
    Data   = []
    Warn   = []
    IgnoredRates=[]

    LumiInfo = HeadParser.LumiInfo
    TriggerRates = HeadParser.TriggerRates
    TriggerInfo = HeadParser.TriggerInfo
    PrescaleValues = HeadParser.PrescaleValues
    TotalPSInfo = HeadParser.TotalPSInfo
    CorrectedPSInfo = HeadParser.CorrectedPSInfo
    
    [LumiSection,PSColumnByLS,InstLumiByLS,DeliveredLumiByLS,LiveLumiByLS,AvInstLumi,AvDeliveredLumi,AvLiveLumi] = LumiInfo
    [L1TriggerMode, HLTTriggerMode, HLTSeed] = TriggerInfo
    [L1Prescale,HLTPrescale,MissingPrescale] = PrescaleValues
    [L1_zero,HLT_zero,IdealPrescale,IdealHLTPrescale,n1,n2,L1,L2,H1,H2] = TotalPSInfo
    [RealPrescale,xLS,L1,L2,H1,H2] = CorrectedPSInfo

    for key in TriggerRates:
##  SKIP triggers in the skip list
        skipTrig=False
        ##for trig in ExcludeList:
            ##if not headTrigN.find(trig) == -1:
                ##skipTrig=True
                ##break
        ##if skipTrig:
            ##IgnoredRates.append([headTrigN,headTrigRate])  # get the current rates of the ignored paths
            ##continue

        if L1_zero[key] == True or HLT_zero[key] == True:
            continue
                
        [TriggerRate,L1Pass,PSPass,RealHLTPrescale,Seed,StartLS,EndLS] = TriggerRates[key]

        OverallPrescale = RealPrescale[key]

        PSCorrectedRate = TriggerRate * OverallPrescale
        #print str(key)+" made it here with TriggerRate = "+str(TriggerRate)+", PSCorrectedRate = "+str(PSCorrectedRate)


        if RefRunNum == 0:  ## Use rate prediction functions
            PSCorrectedExpectedRate = Config.GetExpectedRate(key,AvLiveLumi)
            if PSCorrectedExpectedRate < 0:  ##This means we don't have a prediction for this trigger
                continue
            ExpectedRate = round((PSCorrectedExpectedRate / OverallPrescale),2)
            PerDiff=0
            if ExpectedRate>0:
                PerDiff = int(round( (TriggerRate-ExpectedRate)/ExpectedRate,2 )*100)
            if abs(PerDiff) > AllowedRateDiff/max(sqrt(TriggerRate),sqrt(ExpectedRate)):
                Warn.append(True)
            else:
                Warn.append(False)

            if TriggerRate < IgnoreThreshold and ExpectedRate < IgnoreThreshold:
                continue

            VC = ""
            Data.append([key,TriggerRate,ExpectedRate,PerDiff,OverallPrescale,VC]) 
            continue

        else:  ## Use a reference run

            if not L1Prescale[HLTSeed[key]][StartLS] == 1 or not L1Prescale[HLTSeed[key]][EndLS] == 1:
                continue
            
            RefInstLumi = 0
            RefIterator = 0
            
            for Iterator2 in range(1,Iterator+1):
                if abs(RefLumis[2][Iterator2*10] - AvInstLumi) < abs(RefInstLumi - AvInstLumi):
                    RefInstLumi = RefLumis[2][Iterator2*10]
                    RefIterator = int(Iterator2)

            RefRate = RefRates[RefIterator]
            RefAvDeliveredLumi = (RefLumis[3][(RefIterator+1)*10] - RefLumis[3][RefIterator*10])*1000/(23.3*10)
            RefAvLiveLumi = (RefLumis[4][(RefIterator+1)*10] - RefLumis[4][RefIterator*10])*1000/(23.3*10)

            try:
                ScaledRefRate = round( ((RefRate[key][0]*RefRate[key][3])/OverallPrescale)*(AvLiveLumi/RefAvLiveLumi), 2)
            except:
                print "Maybe trigger "+str(key)+" does not exist in the reference run?"

            if ScaledRefRate == 0:
                PerDiff = 100
            else:
                PerDiff = int( round( (TriggerRate - ScaledRefRate)/ScaledRefRate , 2)*100)

            if TriggerRate < IgnoreThreshold and ScaledRefRate < IgnoreThreshold:
                continue

            if abs(PerDiff) > AllowedRateDiff/max(sqrt(TriggerRate),sqrt(ScaledRefRate)):
                Warn.append(True)
            else:
                Warn.append(False)
            VC = ""
            Data.append([key,TriggerRate,ScaledRefRate,PerDiff,OverallPrescale,VC]) 
            continue
            
    PrettyPrintTable(Header,Data,[80,10,10,10,10,20],Warn)

                
if __name__=='__main__':
    main()
