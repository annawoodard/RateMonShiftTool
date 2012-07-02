#!/usr/bin/env python

#from AndrewGetRun import GetRun
from DatabaseParser import *
from ReadConfig import RateMonConfig
import sys
import os
import cPickle as pickle
import getopt
import time
from colors import *
from TablePrint import *
from AddTableInfo_db import MoreTableInfo
from math import *

WBMPageTemplate = "http://cmswbm/cmsdb/servlet/RunSummary?RUN=%s&DB=cms_omds_lb"
WBMRunInfoPage = "https://cmswbm/cmsdb/runSummary/RunSummary_1.html"

RefRunNameTemplate = "RefRuns/%s/Run_%s.pk"

# define a function that clears the terminal screen
def clear():
    print("\x1B[2J")


def usage():
    print sys.argv[0]+" [Options]"
    print "This script gets the current HLT trigger rates and compares them to a reference run"
    print "Options: "
    print "--AllowedDiff=<diff>                 Report only if difference in trigger rate is greater than <diff>%"
    print "--CompareRun=<Run #>                 Compare run <Run #> to the reference run (Default = Current Run)"
    print "--FindL1Zeros                        Look for physics paths with 0 L1 rate"    
    print "--FirstLS=<ls>                       Specify the first lumisection to consider. This will set LSSlidingWindow to -1"
    print "--NumberLS=<#>                       Specify the last lumisection to consider. Make sure LastLS > LSSlidingWindow"
    print "                                        or set LSSlidingWindow = -1"  
    print "--IgnoreLowRate=<rate>               Ignore triggers with an actual and expected rate below <rate>"
    print "--ListIgnoredPaths                   Prints the paths that are not compared by this script and their rate in the CompareRun"
    print "--PrintLumi                          Prints Instantaneous, Delivered, and Live lumi by LS for the run"
    print "--RefRun=<Run #>                     Specifies <Run #> as the reference run to use (Default in defaults.cfg)"
    print "--ShowPSTriggers                     Show prescaled triggers in rate comparison"
    print "--sortBy=<field>                     Sort the triggers by field.  Valid fields are: name, rate, rateDiff"
    print "--force                              Override the check for collisions run"
    print "--help                               Print this help"

def pickYear():
    global thisyear
    thisyear="2012"
    ##print "Year set to ",thisyear

def main():
    pickYear()
    try:
        opt, args = getopt.getopt(sys.argv[1:],"",["AllowedDiff=","CompareRun=","FindL1Zeros",\
                                                   "FirstLS=","NumberLS=","IgnoreLowRate=","ListIgnoredPaths",\
                                                   "PrintLumi","RefRun=","ShowPSTriggers","force","sortBy=","help"])
    except getopt.GetoptError, err:
        print str(err)
        usage()
        sys.exit(2)

    Config = RateMonConfig(os.path.abspath(os.path.dirname(sys.argv[0])))
    for o,a in opt:
        if o=="--ConfigFile":
            Config.CFGfile=a
    Config.ReadCFG()


    if "NoV" in Config.FitFileName:
        Config.NoVersion=True
    print "NoVersion=",Config.NoVersion

    AllowedRateDiff   = Config.DefAllowRateDiff
    CompareRunNum     = ""
    FindL1Zeros       = False
    FirstLS           = 9999
    NumLS             = -10
    IgnoreThreshold   = Config.DefAllowIgnoreThresh
    ListIgnoredPaths  = False
    PrintLumi         = False
    RefRunNum         = int(Config.ReferenceRun)
    ShowPSTriggers    = True
    Force             = False
    SortBy            = ""

    ShifterMode       = int(Config.ShifterMode) # get this from the config, but can be overridden by other options
    
   ##  if int(Config.ShifterMode):
##         print "ShifterMode!!"
##     else:
##         print "ExpertMode"

    if Config.LSWindow > 0:
        NumLS = -1*Config.LSWindow

    for o,a in opt: # get options passed on the command line
        if o=="--AllowedDiff":
            AllowedRateDiff = float(a)
        elif o=="--CompareRun":
            CompareRunNum=int(a)
            ShifterMode = False
        elif o=="--FindL1Zeros":
            FindL1Zeros = True
        elif o=="--FirstLS":
            FirstLS = int(a)
            ShifterMode = False
        elif o=="--NumberLS":
            NumLS = int(a)
        elif o=="--IgnoreLowRate":
            IgnoreThreshold = float(a)
        elif o=="--ListIgnoredPaths":
            ListIgnoredPaths=True
            ShifterMode = False
        elif o=="--PrintLumi":
            PrintLumi = True
        elif o=="--RefRun":
            RefRunNum=int(a)
        elif o=="--ShowPSTriggers":
            ShowPSTriggers=True
        elif o=="--sortBy":
            SortBy = a
        elif o=="--force":
            Force = True
        elif o=="--help":
            usage()
            sys.exit(0)
        else:
            print "Invalid Option "+a
            sys.exit(1)

        
    RefLumisExists = False
    """
    RefRunFile=RefRunNameTemplate % str(RefRunNum)
    if RefRunNum > 0:
        RefRates = {}
        for Iterator in range(1,100):
            if RefLumisExists:  ## Quits at the end of a run
                if max(RefLumis[0]) <= (Iterator+1)*10:
                    break

                    RefRunFile = RefRunNameTemplate % str( RefRunNum*100 + Iterator )  # place to save the reference run info
            print "RefRunFile=",RefRunFile
            if not os.path.exists(RefRunFile[:RefRunFile.rfind('/')]):  # folder for ref run file must exist
                print "Reference run folder does not exist, please create" # should probably create programmatically, but for now force user to create
                print RefRunFile[:RefRunFile.rfind('/')]
                sys.exit(0)

            if not os.path.exists(RefRunFile):  # if the reference run is not saved, get it from wbm
                print "Reference Run File for run "+str(RefRunNum)+" iterator "+str(Iterator)+" does not exist"
                print "Creating ..."
                try:
                    RefParser = GetRun(RefRunNum, RefRunFile, True, Iterator*10, (Iterator+1)*10)
                    print "parsing"
                except:
                    print "GetRun failed from LS "+str(Iterator*10)+" to "+str((Iterator+1)*10)
                    continue
                    
            else: # otherwise load it from the file
                RefParser = pickle.load( open( RefRunFile ) )
                print "loading"
            if not RefLumisExists:
                RefLumis = RefParser.LumiInfo
                RefLumisExists = True

            try:
                RefRates[Iterator] = RefParser.TriggerRates # get the trigger rates from the reference run
                LastSuccessfulIterator = Iterator
            except:
                print "Failed to get rates from LS "+str(Iterator*10)+" to "+str((Iterator+1)*10)
    
    """
    RefRunFile = RefRunNameTemplate % (thisyear,RefRunNum)
    RefParser = DatabaseParser()
    ##print "Reference Run: "+str(RefRunNum)
    if RefRunNum > 0:
        print "Geting RefRunFile",RefRunFile
        if not os.path.exists(RefRunFile[:RefRunFile.rfind('/')]):  # folder for ref run file must exist
            print "Reference run folder does not exist, please create" # should probably create programmatically, but for now force user to create
            print RefRunFile[:RefRunFile.rfind('/')]
            sys.exit(0)
            s
            return
        if not os.path.exists(RefRunFile):
            print "RefRunFile does not exist"
            # create the reference run file
            try:
                RefParser.RunNumber = RefRunNum
                RefParser.ParseRunSetup()
                print "RefParser is setup"
                #RefParser.GetAllTriggerRatesByLS()
                #RefParser.Save( RefRunFile )
            except e:
                print "PROBLEM GETTING REFERNCE RUN"
                raise  
        else:
            RefParser = pickle.load( open( RefRunFile ) )
            
    # OK, Got the Reference Run
    # Now get the most recent run

    SaveRun = False
    if CompareRunNum=="":  # if no run # specified on the CL, get the most recent run
        CompareRunNum,isCol,isGood = GetLatestRunNumber()
        
            
        if not isGood:
            print "NO TRIGGER KEY FOUND for run ",CompareRunNum

            ##sys.exit(0)

        if not isCol:
            print "Most Recent run, "+str(CompareRunNum)+", is NOT collisions"
            print "Monitoring only stream A and Express"
            #if not Force:
            #    sys.exit(0) # maybe we should walk back and try to find a collisions run, but for now just exit

        else:
            print "Most Recent run is "+str(CompareRunNum)
    else:
        CompareRunNum,isCol,isGood = GetLatestRunNumber(CompareRunNum)
        if not isGood:
            print "NO TRIGGER KEY FOUND for run ", CompareRunNum
            ##sys.exit(0)

    
    HeadParser = DatabaseParser()
    HeadParser.RunNumber = CompareRunNum
        
    try:
        HeadParser.ParseRunSetup()
        HeadLumiRange = HeadParser.GetLSRange(FirstLS,NumLS,isCol)
        LastGoodLS=HeadParser.GetLastLS(isCol)
        CurrRun=CompareRunNum
        print "done good"
    except:
        print "exception"
        HeadLumiRange=[]
        LastGoodLS=-1
        CurrRun=CompareRunNum
        isGood=0
        
    if len(HeadLumiRange) is 0:
        print "No lumisections that are taking physics data 0"
        HeadLumiRange = HeadParser.GetLSRange(FirstLS,NumLS,False)
        if len(HeadLumiRange)>0:
            isGood=1
            isCol=0
        ##sys.exit(0)
    
    
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

### Now actually compare the rates, make tables and look at L1. Loops for ShifterMode
        #CheckTriggerList(HeadParser,RefRunNum,RefRates,RefLumis,LastSuccessfulIterator,ShowPSTriggers,AllowedRateDiff,IgnoreThreshold,Config)
    
    ###isGood=1##if there is a trigger key
    try:
        while True:
            
            if isGood:
                LastGoodLS=HeadParser.GetLastLS(isCol)
                if not isCol:
                    ##clear()
                    MoreTableInfo(HeadParser,HeadLumiRange,Config,False)
                else:
                    if (len(HeadLumiRange)>0):
                        RunComparison(HeadParser,RefParser,HeadLumiRange,ShowPSTriggers,AllowedRateDiff,IgnoreThreshold,Config,ListIgnoredPaths,SortBy)
                        if FindL1Zeros:
                            CheckL1Zeros(HeadParser,RefRunNum,RefRates,RefLumis,LastSuccessfulIterator,ShowPSTriggers,AllowedRateDiff,IgnoreThreshold,Config)
                    else:
                        print "No lumisections that are taking physics data 1"
            if ShifterMode:
                #print "Shifter Mode. Continuing"
                pass
            else:
                print "Expert Mode. Quitting."
                sys.exit(0)

            
            print "Sleeping for 1 minute before repeating  "
            for iSleep in range(20):
                write(".")
                sys.stdout.flush()
                time.sleep(3)
            write("  Updating\n")
            sys.stdout.flush()
            
            ##print "\nminLS=",min(HeadLumiRange),"Last LS=",HeadParser.GetLastLS(isCol),"run=",HeadParser.RunNumber
            ###Get a new run if DAQ stops
            ##print "\nLastGoodLS=",LastGoodLS

            ##### NEED PLACEHOLDER TO COMPARE CURRENT RUN TO LATEST RUN #####
            
            NewRun,isCol,isGood = GetLatestRunNumber(9999999)  ## update to the latest run and lumi range
            
            try:
                maxLumi=max(HeadLumiRange)
            except:
                maxLumi=0
            
            ##### THESE ARE CONDITIONS TO GET NEW RUN #####
            if maxLumi>(LastGoodLS+1) or not isGood or NewRun!=CurrRun:
                print "Trying to get new Run"
                try:
                    HeadParser = DatabaseParser()
                    HeadParser.RunNumber = NewRun
                    HeadParser.ParseRunSetup()
                    CurrRun,isCol,isGood=GetLatestRunNumber(9999999)
                    FirstLS=9999
                    HeadLumiRange = HeadParser.GetLSRange(FirstLS,NumLS,isCol)    
                    if len(HeadLumiRange) is 0:
                        HeadLumiRange = HeadParser.GetLSRange(FirstLS,NumLS,False)
                        print "No lumisections that are taking physics data 2"
                        if len(HeadLumiRange)>0:
                            isGood=1
                            isCol=0
                            
                            
                    LastGoodLS=HeadParser.GetLastLS(isCol)
                    ##print CurrRun, isCol, isGood
                except:
                    isGood=0
                    isCol=0
                    print "failed"
                
                                
                
                
            ##CurrRun,isCol,isGood = GetLatestRunNumber(CurrRun)  ## update to the latest run and lumi range
            else:
                try:
                    HeadParser.ParseRunSetup()
                    HeadLumiRange = HeadParser.GetLSRange(FirstLS,NumLS,isCol)
                    if len(HeadLumiRange) is 0:
                        HeadLumiRange = HeadParser.GetLSRange(FirstLS,NumLS,False)
                        print "No lumisections that are taking physics data"
                        if len(HeadLumiRange)>0:
                            isGood=1
                            isCol=0
                    LastGoodLS=HeadParser.GetLastLS(isCol)
                
                except:
                    isGood=0
                    isCol=0
                    clear()
                    print "NO TRIGGER KEY FOUND YET for run", NewRun ,"repeating search"
                
    
            ## try:
##                 HeadParser.GetLumiInfo()
##                 if len(HeadParser.Active)>0:
##                     isGood=1
##                     ##print "setting to good"
##             except:
##                 pass

                
        #end while True
    #end try
    except KeyboardInterrupt:
        print "Quitting. Peace Out."

            
def RunComparison(HeadParser,RefParser,HeadLumiRange,ShowPSTriggers,AllowedRateDiff,IgnoreThreshold,Config,ListIgnoredPaths,SortBy):
    Header = ["Trigger Name","Actual","Expected","% Inc","Cur PS","Comments"]
    Data   = []
    Warn   = []
    IgnoredRates=[]
    
    [HeadAvInstLumi,HeadAvLiveLumi,HeadAvDeliveredLumi,HeadAvDeadTime,HeadPSCols] = HeadParser.GetAvLumiInfo(HeadLumiRange)
    ##[HeadUnprescaledRates, HeadTotalPrescales, HeadL1Prescales, HeadTriggerRates] = HeadParser.UpdateRun(HeadLumiRange)
    HeadUnprescaledRates = HeadParser.UpdateRun(HeadLumiRange)
    [PSColumnByLS,InstLumiByLS,DeliveredLumiByLS,LiveLumiByLS,DeadTimeByLS,PhysicsByLS,ActiveByLS] = HeadParser.LumiInfo
    deadtimebeamactive=HeadParser.GetDeadTimeBeamActive(HeadLumiRange)
    try:
        pkl_file = open(Config.FitFileName, 'rb')
        FitInput = pickle.load(pkl_file)
        pkl_file.close()
        ##print "fit file name=",Config.FitFileName
        
    except:
        print "No fit file specified"
        sys.exit(2)
        
    try:    
        refrunfile="RefRuns/%s/Rates_HLT_10LS_JPAP.pkl" % (thisyear)
        pkl_file = open(refrunfile, 'rb')
        RefRatesInput = pickle.load(pkl_file)
        pkl_file.close()
    except:
        RefRatesInput={}
        print "Didn't open ref file"


    trig_list=Config.MonitorList
    
    if Config.NoVersion:
        trig_list=[]
        FitInputNoV={}
        
        for trigger in Config.MonitorList:
            trig_list.append(StripVersion(trigger))
        for trigger in FitInput.iterkeys():
            FitInputNoV[StripVersion(trigger)]=FitInput[trigger]
        FitInput=FitInputNoV
    
    
    ##trig_list=Config.MonitorList
    for HeadName in HeadUnprescaledRates:
        
        HeadNameNoV=StripVersion(HeadName)
        
        if RefParser.RunNumber == 0:  ##  If not ref run then just use trigger list           
            if Config.NoVersion:
                if HeadNameNoV not in trig_list and not ListIgnoredPaths:
                    continue
                if HeadNameNoV not in FitInput.keys() and not ListIgnoredPaths:
                    continue
            else:       
                if HeadName not in trig_list and not ListIgnoredPaths:
                    continue
                if HeadName not in FitInput.keys() and not ListIgnoredPaths:
                    continue
        else:
            if HeadUnprescaledRates[HeadName][2]<0.5:
                continue
            
            ##if HeadUnprescaledRates[HeadName][0]>1.9:
            ##    continue
            
        
        ##masked_triggers = ["AlCa_", "DST_", "HLT_L1", "HLT_L2", "HLT_Zero"]
        masked_triggers = ["AlCa_", "DST_", "HLT_L1", "HLT_Zero"]
        masked_trig = False
        for mask in masked_triggers:
            if str(mask) in HeadName:
                masked_trig = True
        if masked_trig:
            continue

        skipTrig=False
        TriggerRate = round(HeadUnprescaledRates[HeadName][2],2)
        if RefParser.RunNumber == 0:  ## Use rate prediction functions
           
            
            PSCorrectedExpectedRate = Config.GetExpectedRate(HeadName,FitInput,RefRatesInput,HeadAvLiveLumi,HeadAvDeliveredLumi,deadtimebeamactive)
            

            #if PSCorrectedExpectedRate[0] < 0:  ##This means we don't have a prediction for this trigger
            #    continue
            try:
                ExpectedRate = round((PSCorrectedExpectedRate[0] / HeadUnprescaledRates[HeadName][1]),2)
            except:
                ExpectedRate=0.
                #print "No rate for ", HeadName

            PerDiff=0
            VC = ""
            if ExpectedRate>0:
                PerDiff = int(round( (TriggerRate-ExpectedRate)/ExpectedRate,2 )*100)
            else:
                PerDiff=-999.
                if ExpectedRate==0:
                    VC="0 expected rate"
                else:
                    VC="lt 0 expected rate"

            if TriggerRate < IgnoreThreshold and (ExpectedRate < IgnoreThreshold and ExpectedRate!=0):
                continue

            
            
            Data.append([HeadName,TriggerRate,ExpectedRate,PerDiff,round(HeadUnprescaledRates[HeadName][1],1),VC]) 

        else:  ## Use a reference run
            ## cheap trick to only get triggers in list when in shifter mode
            #print "shifter mode=",int(Config.ShifterMode)
            

            
           
            ##if not HeadParser.AvgL1Prescales[HeadParser.HLTSeed[HeadName]]==1:
            ##    continue
            
            RefInstLumi = 0
            RefIterator = 0

            RefStartIndex = ClosestIndex(HeadAvInstLumi,RefParser.GetAvLumiPerRange())
            
            RefLen   = -10
            
            
            RefUnprescaledRates = RefParser.UpdateRun(RefParser.GetLSRange(RefStartIndex,RefLen))
            [RefAvInstLumi,RefAvLiveLumi,RefAvDeliveredLumi,RefAvDeadTime,RefPSCols] = RefParser.GetAvLumiInfo(RefParser.GetLSRange(RefStartIndex,RefLen))
            deadtimebeamactive=RefParser.GetDeadTimeBeamActive(RefParser.GetLSRange(RefStartIndex,RefLen))
            
            RefRate = -1
            for k,v in RefUnprescaledRates.iteritems():
                #if StripVersion(HeadName) == StripVersion(k): # versions may not match
                if HeadName==k:
                    RefRate = RefUnprescaledRates[k][2]
                    
            try:
                ScaledRefRate = round( (RefRate*HeadAvLiveLumi/RefAvLiveLumi*(1-deadtimebeamactive)), 2  )
                
            except ZeroDivisionError:
                ScaledRefRate=0
                
            
        
            ##print HeadName,"ScaledRefRate=",ScaledRefRate
            if ScaledRefRate == 0:
                PerDiff = 100
            else:
                PerDiff = int( round( (TriggerRate - ScaledRefRate)/ScaledRefRate , 2)*100)

            if TriggerRate < IgnoreThreshold and ScaledRefRate < IgnoreThreshold:
                continue

            VC = ""
            Data.append([HeadName,TriggerRate,ScaledRefRate,PerDiff,round((HeadUnprescaledRates[HeadName][1]),1),VC])

    SortedData = []
    if SortBy == "":
        SortedData = Data # don't do any sorting
        if RefParser.RunNumber>0:
            SortedData=sorted(Data, key=lambda entry: abs(entry[3]),reverse=True) 
    elif SortBy == "name":
        SortedData=sorted(Data, key=lambda entry: entry[0])
    elif SortBy == "rate":
        SortedData=sorted(Data, key=lambda entry: entry[1],reverse=True)
    elif SortBy == "rateDiff":
        SortedData=sorted(Data, key=lambda entry: abs(entry[3]),reverse=True)
    else:
        print "Invalid sorting option %s\n"%SortBy
        SortedData = Data

    #check for triggers above the warning threshold
    Warn=[]
    for entry in SortedData:
        if abs(entry[3]) > AllowedRateDiff:
            Warn.append(True)
        else:
            Warn.append(False)

    PrettyPrintTable(Header,SortedData,[80,10,10,10,10,20],Warn)

    MoreTableInfo(HeadParser,HeadLumiRange,Config)

def CheckTriggerList(HeadParser,RefRunNum,RefRates,RefLumis,LastSuccessfulIterator,ShowPSTriggers,AllowedRateDiff,IgnoreThreshold,Config):
    print "checking trigger list"

def CheckL1Zeros(HeadParser,RefRunNum,RefRates,RefLumis,LastSuccessfulIterator,ShowPSTriggers,AllowedRateDiff,IgnoreThreshold,Config):
    L1Zeros=[]
    IgnoreBits = ["L1_PreCollisions","L1_InterBunch_Bsc","L1_BeamHalo","L1_BeamGas_Hf"]
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
            if HeadParser.TriggerRates[key][4].find('L1_BeamHalo')==-1 and HeadParser.TriggerRates[key][4].find('L1_PreCollisions')==-1 and HeadParser.TriggerRates[key][4].find('L1_InterBunch_Bsc')==-1:
                
                L1Zeros.append(HeadParser.TriggerRates[key][4])
                print "L1Zeros=", L1Zeros
        
    if len(L1Zeros) == 0:
       #print "It looks like no masked L1 bits seed trigger paths"
        pass
    else:
        print "The following seeds are used to seed HLT bits but accept 0 events:"
    #print "The average lumi of this run is: "+str(round(HeadParser.LumiInfo[6],1))+"e30"
        for Seed in L1Zeros:
            print Seed
        
if __name__=='__main__':
    global thisyear
    main()
