#!/usr/bin/env python

from Page1Parser import Page1Parser
from GetRun import GetRun
import sys
import os
import cPickle as pickle
import getopt
import time
from ReadConfig import RateMonConfig
from colors import *

WBMPageTemplate = "http://cmswbm/cmsdb/servlet/RunSummary?RUN=%s&DB=cms_omds_lb"
WBMRunInfoPage = "https://cmswbm/cmsdb/runSummary/RunSummary_1.html"

RefRunNameTemplate = "RefRuns/Run_%s.pk"

# define a function that clears the terminal screen
def clear():
    print("\x1B[2J")

def usage():
    print sys.argv[0]+" [Options]"
    print "This script monitors some HLT paths for bizarre rates"
    print "Options: "
    print "--CompareRun=<Run #>                 Compare run <Run #> to the reference run (Default = Current Run)"
    print "--AllowedDiff=<diff>                 Report only if difference in trigger rate is greater than <diff>%"
    print "--ZerosOnly                          Only report if trigger rate is 0"
    print "--FindL1Zeros                        Look for physics paths with 0 L1 rate"
    print "--ListIgnoredPaths                   Prints the paths that are not compared by this script and their rate in the CompareRun"
    print "--ConfigFile=<file>                  Specify a configuration file (Default = defaults.cfg)"
    print "--FirstLS=<ls>                       Specify the first lumisection to consider. This will set LSSlidingWindow to -1"
    print "--LastLS=<ls>                        Specify the last lumisection to consider. Make sure LastLS > LSSlidingWindow"
    print "                                        or set LSSlidingWindow = -1"  
    print "--help                               Print this help"
    
def main():
    try:
        opt, args = getopt.getopt(sys.argv[1:],"",["IgnoreVersion","ZerosOnly","CompareRun=","AllowedDiff=",\
                                                   "IgnoreLowRate=","FindL1Zeros","ListIgnoredPaths","ConfigFile=",\
                                                   "FirstLS=","LastLS=","help"])
    except getopt.GetoptError, err:
        print str(err)
        usage()
        sys.exit(2)

    Config = RateMonConfig(os.path.abspath(os.path.dirname(sys.argv[0])))
    for o,a in opt:
        if o=="--ConfigFile":
            Config.CFGfile=a
    Config.ReadCFG()
    
    IgnoreVersion     = False
    ZerosOnly         = False
    ListIgnoredPaths  = False
    AllowedRateDiff   = Config.DefAllowRateDiff
    IgnoreThreshold   = Config.DefAllowIgnoreThresh
    CompareRunNum     = ""
    FindL1Zeros       = Config.FindL1Zeros
    FirstLS           = 999999
    EndEndLS          = 111111
    LastLS            = FirstLS+10
    RefRunNum         = int(Config.ReferenceRun)
    NWarnPSZero       = 1
    
    if Config.LSWindow > 0:
        FirstLS = -1*Config.LSWindow


    
    for o,a in opt: # get options passed on the command line
        if o=="--IgnoreVersion":
            IgnoreVersion=True
        elif o=="--ZerosOnly":
            ZerosOnly=True
        elif o=="--CompareRun":
            CompareRunNum=a
        elif o=="--AllowedDiff":
            AllowedRateDiff = float(a)
        elif o=="--IgnoreLowRate":
            IgnoreThreshold = float(a)
        elif o=="--FindL1Zeros":
            FindL1Zeros=True
        elif o=="--ListIgnoredPaths":
            ListIgnoredPaths=True
        elif o=="--FirstLS":
            FirstLS = int(a)
        elif o=="--LastLS":
            EndEndLS = int(a)
        elif o=="--ConfigFile":
            print "Using your custom config file ... %s" % (a)
        elif o=="--help":
            usage()
            sys.exit(0)
        else:
            print "Invalid Option "+a
            sys.exit(1)
        # end else
    #end for

    try:
        NPSZeros = 0
        while True:
            ### Get the most recent run
            SaveRun=False
            if CompareRunNum=="":  # if no run # specified on the CL, get the most recent run
                RunListParser = Page1Parser()

                RunListParser._Parse(WBMRunInfoPage)  # this is the page that lists all the runs in the last 24 hours with at least 1 trigger
                RunListPage = RunListParser.ParsePage1()
                
                if RunListPage == '':  # this will be '' if the mode of the most recent run is not l1_hlt_collisions/v*
                    print "WBM info page is "+WBMRunInfoPage
                    print "Most Recent run"+" is NOT collisions"
                    sys.exit(0) # maybe we should walk back and try to find a collisions run, but for now just exit
                CompareRunNum = RunListParser.RunNumber
                print "Most Recent run is "+CompareRunNum
            else:
                SaveRun=False
            HeadRunFile = RefRunNameTemplate % CompareRunNum
            RefRunFile  = RefRunNameTemplate % str(RefRunNum)
                        

            if not os.path.exists(RefRunFile[:RefRunFile.rfind('/')]):  # folder for ref run file must exist
                print "Reference run folder does not exist, please create" # should probably create programmatically, but for now force user to create
                print RefRunFile[:RefRunFile.rfind('/')]
                sys.exit(0)

            if not os.path.exists(RefRunFile) and RefRunNum != 0:  # if the reference run is not saved, get it from wbm
                    print "Updated reference run file"
                    RefParser = GetRun(RefRunNum, RefRunFile, True)
            else: # otherwise load it from the file
                if RefRunNum != 0:
                    RefParser = pickle.load( open( RefRunFile ) )
                    print "going to ref run file"
                    
            if os.path.exists(HeadRunFile):  # check if a run file for the run we want to compare already exists, it probably won't but just in case we don't have to interrogate WBM
                
                HeadParser = pickle.load( open( HeadRunFile ) )
            else:
                HeadParser = GetRun(CompareRunNum,HeadRunFile,SaveRun,FirstLS,EndEndLS)

            if HeadParser.FirstLS==-1:
                print bcolors.OKBLUE+">> Stable Beams NOT yet declared, be patient..."+bcolors.ENDC
                sys.exit(0)

            HeadRates = HeadParser.TriggerRates

            write=sys.stdout.write

            write('#'*50+'\n')
            write('Please include all info below in any elog posts\nPost to elog HLT on call\nIt may be helpful to experts\n')
            write('#'*50+'\n')

            write('Script called with following command line:\n\n')

            for thing in sys.argv:
                write (thing)
                write ("\n")

            write('\nUsing the following parameters:\n')
            write('IgnoreVersion = %s\n' % (IgnoreVersion) )
            write('ZerosOnly = %s\n' % (ZerosOnly) )
            write('CompareRun = %s\n' % (CompareRunNum)  )
            write('AllowedDiff = %s\n' % (AllowedRateDiff) )
            write('IgnoreLowRate = %s\n' % (IgnoreThreshold) )
            write('FindL1Zeros = %s\n' % (FindL1Zeros) )
            write('ListIgnoredPaths = %s\n' %(ListIgnoredPaths))
            write('FirstLS = %s\n' % (FirstLS))
            write('LastLS = %s\n'  % (EndEndLS))
            write('ConfigFile = %s\n\n' % (Config.CFGfile))
            ##write('RefRunFile = %s\n' % (RefRunFile))
            

            nameBufLen=60
            RateBuffLen=10
            write('*'*(nameBufLen+3*RateBuffLen+10))
            write ('\nCalculation using FirstLS = %s to LastLS = %s of run %s \n' % (HeadParser.FirstLS, HeadParser.LastLS, CompareRunNum))

            write("The average delivered lumi of these lumi sections is:       ")
            write(str(round(HeadParser.AvDeliveredLumi,1))+"e30"+"\n")
            write("The average live (recorded) lumi of these lumi sections is: ")
            if HeadParser.AvLiveLumi==0:
                write(bcolors.FAIL)
            elif HeadParser.AvLiveLumi<100:
                write(bcolors.WARNING)

            write(str(round(HeadParser.AvLiveLumi,1))+"e30")
            write(bcolors.ENDC+"\n")

            ###DT from calculation
            write("The average deadtime of these lumi sections is:              ")
            if HeadParser.AvDeadtime > 5:
                write(bcolors.FAIL)
            elif HeadParser.AvDeadtime > 10:
                write(bcolors.WARNING)
            else:
                write(bcolors.OKBLUE)
            write(str(round(HeadParser.AvDeadtime,1))+"%")
            write(bcolors.ENDC+"\n")


            ### DT from L1 page 
            write("The DeadTimeBeamActive of these lumi sections is:              ")
            if float(HeadParser.DeadTime[1]) > 5:
                write(bcolors.FAIL)
            elif float(HeadParser.DeadTime[1]) > 10:
                write(bcolors.WARNING)
            else:
                write(bcolors.OKBLUE)
            write(str(round(float(HeadParser.DeadTime[1]),1))+"%")
            write(bcolors.ENDC+"\n")
            write("The DeadTime of these lumi sections is:              ")
            write(str(round(float(HeadParser.DeadTime[0]),1))+"%\n")

            print "Using prescale column "+str(HeadParser.PrescaleColumnString)
            
            if HeadParser.PrescaleColumnString=="0":
                if NPSZeros >= NWarnPSZero:
                    write(bcolors.FAIL)
                    write("WARNING:  You are using prescale column 0 in Lumi Section %s!  This is the emergency column and should only be used if there is no other way to take data\n" % (HeadParser.LastLS)  )
                    write("If this is a mistake FIX IT NOW \nif not, the TFM and HLT DOC must be informed\n\n")
                    write(bcolors.ENDC)
                    raw_input("Press ENTER to continue...")
                    write("\n\n")
                else:
                    NPSZeros+=1
            else:
                NPSZeros=0
                

            write('*'*(nameBufLen+3*RateBuffLen+10)+'\n')
            write('* Trigger Name'+' '*(nameBufLen-17)+'*  PS  *  Actual  * Expected * % Diff    *\n')
            write('*'*(nameBufLen+3*RateBuffLen+10)+'\n')    

            IgnoredRates=[]
            LargeRateDifference=False
            for headTrigN,headTrigRate,headTrigPS,headL1 in HeadRates:
                headTrigNNoVersion = headTrigN[:headTrigN.rfind('_')]
                if not Config.AnalyzeTrigger(headTrigNNoVersion): ## SKIP triggers in the skip list
                    continue
                ExpectedRate = Config.GetExpectedRate(headTrigNNoVersion,HeadParser.AvLiveLumi)
                ExpectedRate = round((ExpectedRate / headTrigPS),2)
                Prescale = round(headTrigPS,1)
                PerDiff=0
                if ExpectedRate>0:
                    PerDiff = int(round( (headTrigRate-ExpectedRate)/ExpectedRate,2 )*100)
                ##Write Line ##
                if headTrigRate==0:
                    write(bcolors.FAIL)
                elif abs(PerDiff) > AllowedRateDiff:
                    write(bcolors.FAIL)
                else:
                    write(bcolors.OKGREEN)
                write('* '+headTrigN+' '*(nameBufLen-len(headTrigN)-5)+'*')
                write(' '*(RateBuffLen-4-len(str(Prescale))-1)+str(Prescale)+' *')
                write(' '*(RateBuffLen-len(str(headTrigRate))-1)+str(headTrigRate)+' *')
                write(' '*(RateBuffLen-len(str(ExpectedRate))-1)+str(ExpectedRate)+' *')
                if ExpectedRate>0:
                    if abs(PerDiff) > AllowedRateDiff/2:
                        ###write(' '+' '*(RateBuffLen-len(str(PerDiff))-2)+str(PerDiff)+'%')
                        write('   '+' '*(RateBuffLen-len(str(PerDiff))-4)+str(PerDiff)+'%')
                    else:
                        ###write('  good    ')
                        write(' good'+' '*(RateBuffLen-len(str(PerDiff))-6)+str(PerDiff)+'%')
                else:
                    write('          ')
                write(' *')
                if headTrigRate==0:
                    write(" << TRIGGER RATE IS ZERO! INFORM SHIFT LEADER & CALL HLT DOC")
                elif abs(PerDiff) > AllowedRateDiff:
                    write(" << LARGE RATE DIFFERENCE: POST IN HLT on call ELOG")
                    LargeRateDifference=True # this means we automatically check the reference run
                write(bcolors.ENDC+'\n')

            CallDOC=False
            if ( LargeRateDifference or Config.CompareReference ) and RefRunNum != 0:
                if LargeRateDifference:
                    write(bcolors.WARNING)
                    print """
                    \n\n
                    ********************************************************************
                    A trigger in this run has a substantial difference from expectations.\n
                    Comparing the current run to a reference run
                    ********************************************************************
                    """
                    write(bcolors.ENDC)
                else:
                    print "\n\n Comparing to reference Run:\n\n"

                write('*'*(nameBufLen+3*RateBuffLen+2)+'\n')
                write('* Trigger Name'+' '*(nameBufLen-17)+'* Actual   * Expected * % Diff    *\n')
                write('*'*(nameBufLen+3*RateBuffLen+2)+'\n')    

                NotFound=[]
                for headTrigN,headTrigRate,headTrigPS,headL1 in HeadRates:
                    headTrigNNoVersion = headTrigN[:headTrigN.rfind('_')]
                    if not Config.AnalyzeTrigger(headTrigNNoVersion): ## SKIP triggers in the skip list
                        continue
                    ExpectedRate=-1
                    for refTrigN,refTrigRate,refTrigPS,refLa in RefParser.TriggerRates:
                        refTrigNNoVersion = refTrigN[:refTrigN.rfind('_')]
                        if refTrigNNoVersion == headTrigNNoVersion:
                            ExpectedRate = round(refTrigRate * HeadParser.AvLiveLumi/RefParser.AvLiveLumi,2)
                            break
                    if ExpectedRate==-1:
                        NotFound.append(headTrigNNoVersion)
                        continue
                    PerDiff=0
                    if ExpectedRate>0:
                        PerDiff = int(round( (headTrigRate-ExpectedRate)/ExpectedRate,2 )*100)
                    ##Write Line ##
                    if headTrigRate==0:
                        write(bcolors.FAIL)
                    elif abs(PerDiff) >AllowedRateDiff:
                        write(bcolors.FAIL)
                    else:
                        write(bcolors.OKGREEN)
                    write('* '+headTrigN+' '*(nameBufLen-len(headTrigN)-5)+'*')
                    write(' '*(RateBuffLen-len(str(headTrigRate))-1)+str(headTrigRate)+' *')
                    write(' '*(RateBuffLen-len(str(ExpectedRate))-1)+str(ExpectedRate)+' *')
                    if ExpectedRate>0:
                        if abs(PerDiff) > AllowedRateDiff/2:
                            write(' '+' '*(RateBuffLen-len(str(PerDiff))-2)+str(PerDiff)+'%')
                        else:
                            write('  good    ')                
                    else:
                        write('          ')
                    write(' *')
                    if headTrigRate==0:
                        write(" << TRIGGER RATE IS ZERO! CALL HLT DOC")
                        CallDOC=True
                    elif abs(PerDiff) > AllowedRateDiff:
                        write(" << LARGE RATE DIFFERENCE WITH REFERENCE RUN")
                        CallDOC=True
                    write(bcolors.ENDC+'\n')

            if CallDOC:
                write(bcolors.FAIL)
                print "\nSomething looks very wrong in this run"
                print "If there is no obvious reason for this (subdetector out, etc.): **inform the SHIFT LEADER and call the HLT DOC!**"
                raw_input("Press Enter to continue ... ")
                write(bcolors.ENDC)

            if FindL1Zeros:
                L1Zeros=[]
                IgnoreBits = ["L1_PreCollisions","L1_InterBunch_Bsc","L1_BeamHalo","L1_BeamGas_Hf"]
                for trigN,L1Pass,PSPass,PAccept,SeedName in HeadParser.Nevts:
                    ## Skip events in the skip list
                    trigNNoVersion = trigN[:trigN.rfind('_')]
                    if Config.AnalyzeTrigger(trigNNoVersion):
                        continue
                        ## if no events pass the L1, add it to the L1Zeros list if not already there
                    if SeedName in IgnoreBits:
                        continue
                    if L1Pass==0 and not SeedName in L1Zeros and SeedName.find("BeamGas")==-1 and SeedName.find('L1_SingleMuOpen')==-1 and SeedName.find('L1_BeamHalo')==-1 and SeedName.find('L1_InterBunch_Bsc')==-1 and SeedName.find('L1_PreCollisions')==-1:
                        L1Zeros.append(SeedName)
                if len(L1Zeros) == 0:
                    pass
                #print bcolors.OKGREEN+">>>  L1 Seeds are fine"+bcolors.ENDC
                else:
                    print "\n\n\n"
                    print ">>> The following seeds are used to seed HLT bits but accept 0 events:"
                    if len(L1Zeros)<10:
                        print bcolors.WARNING
                        for Seed in L1Zeros:
                            print Seed
                        print bcolors.ENDC
                    else:
                        print bcolors.FAIL
                        print "\n************************"
                        print   "**MANY L1 seeds are 0!**"
                        print   "**    If in doubt     **"
                        print   "** Call the TFM/HLT!  **"
                        print   "************************"
                        print bcolors.ENDC
                print '\n\n'
            # end if find l1 zeros
            print "Sleeping for 1 minute before repeating  "
            for iSleep in range(6):
                for iDot in range(iSleep+1):
                    print ".",
                print "."
                time.sleep(10)
            clear()
        # End of while True
    #end of try
    except KeyboardInterrupt:
        print "Quitting the program"

        
if __name__=='__main__':
    main()
