#!/usr/bin/env python

from DatabaseParser import *
from GetListOfRuns import *
import sys
import os
from numpy import *
import pickle
import getopt
from StreamMonitor import StreamMonitor

from ROOT import gROOT, TCanvas, TF1, TGraph, TGraphErrors, TPaveStats, gPad, gStyle
from ROOT import TFile, TPaveText, TBrowser
from ROOT import gBenchmark
import array
import math
from ReadConfig import RateMonConfig
from TablePrint import *
from selectionParser import selectionParser

def usage():
    print sys.argv[0]+" [options] <list of runs>"
    print "This script is used to generate fits and do secondary shifter validation"
    print "<list of runs>                       this is a list of the form: a b c-d e f-g, specifying individual runs and/or run ranges"
    print "                                     be careful with using ranges (c-d), it is highly recommended to use a JSON in this case"
    print "options: "
    print "--makeFits                           run in fit making mode"
    print "--secondary                          run in secondary shifter mode"
    print "--TMD                                put in TMD predictions"
    print "--fitFile=<path>                     path to the fit file"
    print "--json=<path>                        path to the JSON file"
    print "--TriggerList=<path>                 path to the trigger list (without versions!)"
    print "--maxdt=<max deadtime>               Mask LS above max deadtime threshold"
    print "--All                                Mask LS with any red LS on WBM LS page (not inc castor zdc etc)"
    print "--Mu                                 Mask LS with Mu off"
    print "--HCal                               Mask LS with HCal barrel off"
    print "--Tracker                            Mask LS with Tracker barrel off"
    print "--ECal                               Mask LS with ECal barrel off"
    print "--EndCap                             Mask LS with EndCap sys off, used in combination with other subsys"
    print "--Beam                               Mask LS with Beam off"
    print "--NoVersion                          Ignore version numbers"
    print "--linear                             Force Linear fits"
    print "--inst                               Fits using inst not delivered"
    print "--TMDerr                             Use errors from TMD predictions"
    print "--write                              Writes fit info into csv, for ranking nonlinear triggers"
    print "--AllTriggers                        Run for all triggers instead of specifying a trigger list"
    
class Modes:
    none,fits,secondary = range(3)

def pickYear():
    global thisyear
    thisyear="2012"
    print "Year set to ",thisyear


def main():
    try:
        
        ##set year to 2012
        pickYear()
        
        try:
            opt, args = getopt.getopt(sys.argv[1:],"",["makeFits","secondary","fitFile=","json=","TriggerList=","maxdt=","All","Mu","HCal","Tracker","ECal","EndCap","Beam","NoVersion","linear","inst","TMDerr","write","AllTriggers"])
            
        except getopt.GetoptError, err:
            print str(err)
            usage()
            sys.exit(2)
            
##     if len(args)<1:
##         print "\nPlease specify at least 1 run to look at\n"
##         usage()
##         sys.exit(0)


##### RUN LIST ########
        run_list=[]
    
        if len(args)<1:
            inputrunlist=[]
            print "No runs specified"
            runinput=raw_input("Enter run range in form <run1> <run2> <run3> or <run1>-<run2>:")
            inputrunlist.append(runinput)

            
            if runinput.find(' ')!=-1:
                args=runinput.split(' ')
            else:
                args.append(runinput)    
            
            
        
        for r in args:
            if r.find('-')!=-1:  # r is a run range
                rrange = r.split('-')
                if len(rrange)!=2:
                    print "Invalid run range %s" % (r,)
                    sys.exit(0)
                try:
                    for rr in range(int(rrange[0]),int(rrange[1])+1):
                        run_list.append(rr)
                except:
                    print "Invalid run range %s" % (r,)
                    sys.exit(0)
            else: # r is not a run range
                try:
                    run_list.append(int(r))
                except:
                    print "Invalid run %s" % (r,)
        
    
##### READ CMD LINE ARGS #########
        mode = Modes.none
        fitFile = ""
        jsonfile = ""
        trig_list = []
        max_dt=-1.0
        subsys=-1.0
        NoVersion=False
        linear=False
        do_inst=False
        TMDerr=False
        wp_bool=False
        all_triggers=False        
        SubSystemOff={'All':False,'Mu':False,'HCal':False,'ECal':False,'Tracker':False,'EndCap':False,'Beam':False}
        for o,a in opt:
            if o == "--makeFits":
                mode = Modes.fits
            elif o == "--secondary":
                mode = Modes.secondary
            elif o == "--fitFile":
                fitFile = str(a)
            elif o == "--json":
                jsonfile = a
            elif o=="--maxdt":
                max_dt = float(a)               
            elif o=="--All":
                subsys=1
                SubSystemOff["All"]=True
            elif o=="--Mu":
                subsys=1
                SubSystemOff["Mu"]=True
            elif o=="--HCal":
                SubSystemOff["HCal"]=True
                subsys=1
            elif o=="--Tracker":
                SubSystemOff["Tracker"]=True
                subsys=1
            elif o=="--ECal":
                SubSystemOff["ECal"]=True
                subsys=1
            elif o=="--EndCap":
                SubSystemOff["EndCap"]=True
                subsys=1
            elif o=="--Beam":
                SubSystemOff["Beam"]=True
                subsys=1
            elif o=="--NoVersion":
                NoVersion=True
            elif o=="--linear":
                linear=True
            elif o=="--inst":
                do_inst=True
            elif o=="--TMDerr":
                TMDerr=True
            elif o=="--write":
                wp_bool=True
            elif o=="--AllTriggers":
                all_triggers=True                
            elif o == "--TriggerList":
                try:
                    f = open(a)
                    for entry in f:
                        if entry.startswith('#'):
                            continue
                        if entry.find(':')!=-1:
                            entry = entry[:entry.find(':')]   ## We can point this to the existing monitor list, just remove everything after ':'!
                            if entry.find('#')!=-1:
                                entry = entry[:entry.find('#')]   ## We can point this to the existing monitor list, just remove everything after ':'!                    
                        trig_list.append( entry.rstrip('\n'))
                except:
                    print "\nInvalid Trigger List\n"
                    sys.exit(0)
            else:
                print "\nInvalid Option %s\n" % (str(o),)
                usage()
                sys.exit(2)

        print "\n\n"
###### MODES #########
        
        if mode == Modes.none: ## no mode specified
            print "\nNo operation mode specified!\n"
            modeinput=raw_input("Enter mode, --makeFits or --secondary:")
            print "modeinput=",modeinput
            if not (modeinput=="--makeFits" or modeinput=="--secondary"):
                print "not either"
                usage()
                sys.exit(0)
            elif modeinput == "--makeFits":
                mode=Modes.fits
            elif modeinput =="--secondary":
                mode=Modes.secondary
            else:
                print "FATAL ERROR: No Mode specified"
                sys.exit(0)
        
        if mode == Modes.fits:
            print "Running in Fit Making mode\n\n"
        elif mode == Modes.secondary:
            print "Running in Secondary Shifter mode\n\n"
        else:  ## should never get here, but exit if we do
            print "FATAL ERROR: No Mode specified"
            sys.exit(0)

        if fitFile=="" and not mode==Modes.fits:
            print "\nPlease specify fit file. These are available:\n"
            path="Fits/%s/" % (thisyear)  # insert the path to the directory of interest
            dirList=os.listdir(path)
            for fname in dirList:
                print fname
            fitFile = path+raw_input("Enter fit file in format Fit_HLT_10LS_Run176023to180252.pkl: ")
            
        ##usage()
        ##sys.exit(0)
        elif fitFile=="":
            NoVstr=""
            if NoVersion:
                NoVstr="NoV_"
            if not do_inst:
                fitFile="Fits/%s/Fit_HLT_%s10LS_Run%sto%s.pkl" % (thisyear,NoVstr,min(run_list),max(run_list))
            else:
                fitFile="Fits/%s/Fit_inst_HLT_%s10LS_Run%sto%s.pkl" % (thisyear,NoVstr,min(run_list),max(run_list))
            
        if "NoV" in fitFile:
            NoVersion=True
        

###### TRIGGER LIST #######
        
        if trig_list == [] and not all_triggers:
        
            print "\nPlease specify list of triggers\n"
            print "Available lists are:"
            dirList=os.listdir(".")
            for fname in dirList:
                entry=fname
                if entry.find('.')!=-1:
                    extension = entry[entry.find('.'):]   ## We can point this to the existing monitor list, just remove everything after ':'!
                    if extension==".list":
                        print fname
            trig_input=raw_input("\nEnter triggers in format HLT_IsoMu30_eta2p1 or a .list file: ")
        
            if trig_input.find('.')!=-1:
                extension = trig_input[trig_input.find('.'):]
                if extension==".list":
                    try:
                        fl=open(trig_input)
                    except:
                        print "Cannot open file"
                        usage()
                        sys.exit(0)
                    
                    for line in fl:
                        if line.startswith('#'):
                            continue
                        if len(line)<1:
                            continue
                                        
                        if len(line)>=2:
                            arg=line.rstrip('\n').rstrip(' ').lstrip(' ')
                            trig_list.append(arg)
                        else:
                            arg=''
                else:
                    trig_list.append(trig_input)
        
    ## Can use any combination of LowestRunNumber, HighestRunNumber, and NumberOfRuns -
    ## just modify "ExistingRuns.sort" and for "run in ExistingRuns" accordingly

        if jsonfile=="":
            JSON=[]
        else:
            print "Using JSON: %s" % (jsonfile,)
            JSON = GetJSON(jsonfile) ##Returns array JSON[runs][ls_list]

   

        ###### TO CREATE FITS #########
        if mode == Modes.fits:
            trig_name = "HLT"
            num_ls = 10
            physics_active_psi = True ##Requires that physics and active be on, and that the prescale column is not 0
            #JSON = [] ##To not use a JSON file, just leave the array empty
            debug_print = False
            no_versions=False
            min_rate = 0.0
            print_table = False
            data_clean = True ##Gets rid of anomalous rate points, reqires physics_active_psi (PAP) and deadtime < 20%
            ##plot_properties = [varX, varY, do_fit, save_root, save_png, fit_file]
            if not do_inst:
                plot_properties = [["delivered", "rate", True, True, False, fitFile]]
            else:
                plot_properties = [["inst", "rate", True, True, False, fitFile]]
        
            masked_triggers = ["AlCa_", "DST_", "HLT_L1", "HLT_Zero"]
            save_fits = True
            if max_dt==-1.0:
                max_dt=0.08 ## no deadtime cutuse 2.0
            force_new=True
            print_info=True
            if subsys==-1.0: 
                SubSystemOff={'All':False,'Mu':False,'HCal':False,'ECal':False,'Tracker':False,'EndCap':False,'Beam':True}
    

        ###### TO SEE RATE VS PREDICTION ########
        if mode == Modes.secondary:
            trig_name = "HLT"
            num_ls = 1
            physics_active_psi = True
            debug_print = False
            no_versions=False
            min_rate = 0.0
            print_table = False
            data_clean = True
            ##plot_properties = [varX, varY, do_fit, save_root, save_png, fit_file]
            plot_properties = [["ls", "rawrate", False, True, False,fitFile]]
            ## rate is calculated as: (measured rate, deadtime corrected) * prescale [prediction not dt corrected]
            ## rawrate is calculated as: measured rate [prediction is dt corrected]

            masked_triggers = ["AlCa_", "DST_", "HLT_L1", "HLT_Zero"]
            save_fits = False
            if max_dt==-1.0:
                max_dt=2.0 ## no deadtime cut=2.0
            force_new=True
            print_info=True
            if subsys==-1.0:
                SubSystemOff={'All':True,'Mu':False,'HCal':False,'ECal':False,'Tracker':False,'EndCap':False,'Beam':True}
    
        for k in SubSystemOff.iterkeys():
            print k,"=",SubSystemOff[k],"   ",
        print " "

        ########  END PARAMETERS - CALL FUNCTIONS ##########
        [Rates,LumiPageInfo]= GetDBRates(run_list, trig_name, trig_list, num_ls, max_dt, physics_active_psi, JSON, debug_print, force_new, SubSystemOff,NoVersion,all_triggers)
        rootFileName = MakePlots(Rates, LumiPageInfo, run_list, trig_name, trig_list, num_ls, min_rate, max_dt, print_table, data_clean, plot_properties, masked_triggers, save_fits, debug_print,SubSystemOff, print_info,NoVersion, linear, do_inst, TMDerr,wp_bool,all_triggers)

    except KeyboardInterrupt:
        print "Wait... come back..."




def GetDBRates(run_list,trig_name,trig_list, num_ls, max_dt, physics_active_psi,JSON,debug_print, force_new, SubSystemOff,NoVersion,all_triggers):
    
    Rates = {}
    LumiPageInfo={}
    ## Save in RefRuns with name dependent on trig_name, num_ls, JSON, and physics_active_psi
    if JSON:
        #print "Using JSON file"
        if physics_active_psi:
            RefRunNameTemplate = "RefRuns/%s/Rates_%s_%sLS_JPAP.pkl" 
        else:
            RefRunNameTemplate = "RefRuns/%s/Rates_%s_%sLS_JSON.pkl" 
    else:
        print "Using Physics and Active ==1"
        if physics_active_psi:
            RefRunNameTemplate = "RefRuns/%s/Rates_%s_%sLS_PAP.pkl"
        else:
            RefRunNameTemplate = "RefRuns/%s/Rates_%s_%sLS.pkl"
        
    
    RefRunFile = RefRunNameTemplate % (thisyear,trig_name,num_ls)
    RefRunFileHLT = RefRunNameTemplate % (thisyear,"HLT",num_ls)

    print "RefRun=",RefRunFile
    print "RefRunFileHLT",RefRunFileHLT
    if not force_new:
        try: ##Open an existing RefRun file with the same parameters and trigger name
            pkl_file = open(RefRunFile, 'rb')
            Rates = pickle.load(pkl_file)
            pkl_file.close()
            os.remove(RefRunFile)
            print "using",RefRunFile
            
            
        except:
            try: ##Open an existing RefRun file with the same parameters and HLT for trigger name
                pkl_file = open(RefRunFileHLT)
                HLTRates = pickle.load(pkl_file)
                for key in HLTRates:
                    if trig_name in str(key):
                        Rates[key] = HLTRates[key]
                #print str(RefRunFile)+" does not exist. Creating ..."
            except:
                print str(RefRunFile)+" does not exist. Creating ..."
         
## try the lumis file
    RefLumiNameTemplate = "RefRuns/%s/Lumis_%s_%sLS.pkl"      
    RefLumiFile= RefLumiNameTemplate % (thisyear,"HLT",num_ls)
    if not force_new:
        try:
            pkl_lumi_file = open(RefLumiFile, 'rb')
            LumiPageInfo = pickle.load(pkl_lumi_file)
            pkl_lumi_file.close()
            os.remove(RefLumiFile)
            print "using",RefLumiFile
        except:
            print str(RefLumiFile)+" doesn't exist. Make it..."


    trig_list_noV=[]
    for trigs in trig_list:
        trig_list_noV.append(StripVersion(trigs))
    
    if NoVersion:
        trig_list=trig_list_noV
        
    for RefRunNum in run_list:
        if JSON:
            if not RefRunNum in JSON:
                continue
        try:            
            ExistsAlready = False
            for key in Rates:
                if RefRunNum in Rates[key]["run"]:
                    ExistsAlready = True
                    break
            
            
            LumiExistsLAready=False
            for v in LumiPageInfo.itervalues():
                if RefRunNum == v["Run"]:
                    LumiExistsAlready=True
                    break
            if ExistsAlready and LumiExistsAlready:
                continue
                    
           
        except:
            print "Getting info for run "+str(RefRunNum)
        
        if RefRunNum < 1:
            continue
        ColRunNum,isCol,isGood = GetLatestRunNumber(RefRunNum)
        if not isGood:
            print "Run ",RefRunNum, " is not Collisions"
            
            continue
        
        if not isCol:
            print "Run ",RefRunNum, " is not Collisions"
            
            continue
        
        print "calculating rates and green lumis for run ",RefRunNum
       
        if True: ##Placeholder
            if True: #May replace with "try" - for now it's good to know when problems happen
                RefParser = DatabaseParser()
                RefParser.RunNumber = RefRunNum
                RefParser.ParseRunSetup()
                RefLumiRangePhysicsActive = RefParser.GetLSRange(1,9999) ##Gets array of all LS with physics and active on
                RefLumiArray = RefParser.GetLumiInfo() ##Gets array of all existing LS and their lumi info
                RefLumiRange = []
                RefMoreLumiArray = RefParser.GetMoreLumiInfo()#dict with keys as bits from lumisections WBM page and values are dicts with key=LS:value=bit

                for iterator in RefLumiArray[0]: ##Makes array of LS with proper PAP and JSON properties
                    ##cheap way of getting PSCol None-->0
                    if RefLumiArray[0][iterator] not in range(1,9):
                        RefLumiArray[0][iterator]=0
                        
                    
                    if not physics_active_psi or (RefLumiArray[5][iterator] == 1 and RefLumiArray[6][iterator] == 1 and RefMoreLumiArray["b1pres"][iterator]==1 and RefMoreLumiArray["b2pres"][iterator]==1 and RefMoreLumiArray["b1stab"][iterator] and RefMoreLumiArray["b2stab"][iterator]==1):
                        if not JSON or RefRunNum in JSON:
                            if not JSON or iterator in JSON[RefRunNum]:
                                RefLumiRange.append(iterator)
                    #print iterator, RefLumiArray[0][iterator], "active=",RefLumiArray[5][iterator],"physics=",RefLumiArray[6][iterator]
                    #print "hbhea=",RefMoreLumiArray['hbhea'][iterator]
                    
                try:
                    nls = RefLumiRange[0]
                    LSRange = {}
                except:
                    print "Run "+str(RefRunNum)+" has no good LS"
                    continue
                if num_ls > len(RefLumiRange):
                    print "Run "+str(RefRunNum)+" is too short: from "+str(nls)+" to "+str(RefLumiRange[-1])+", while num_ls = "+str(num_ls)
                    continue
                while nls < RefLumiRange[-1]-num_ls:
                    LSRange[nls] = []
                    counter = 0
                    for iterator in RefLumiRange:
                        if iterator >= nls and counter < num_ls:
                            LSRange[nls].append(iterator)
                            counter += 1
                    nls = LSRange[nls][-1]+1

                #print "Run "+str(RefRunNum)+" contains LS from "+str(min(LSRange))+" to "+str(max(LSRange))
                for nls in sorted(LSRange.iterkeys()):
                    TriggerRates = RefParser.GetHLTRates(LSRange[nls])

                    ## Clumsy way to append Stream A. Should choose correct method for calculating stream a based on ps column used in data taking.
                    if 'HLT_Stream_A' in trig_list:
                        config = RateMonConfig(os.path.abspath(os.path.dirname(sys.argv[0])))
                        config.ReadCFG()
                        stream_mon = StreamMonitor() 
                        core_a_rates = stream_mon.getStreamACoreRatesByLS(RefParser,LSRange[nls],config).values()
                        avg_core_a_rate = sum(core_a_rates)/len(LSRange[nls])
                        TriggerRates['HLT_Stream_A'] = [1,1,avg_core_a_rate,avg_core_a_rate]

                    [inst, live, delivered, dead, pscols] = RefParser.GetAvLumiInfo(LSRange[nls])
                    deadtimebeamactive=RefParser.GetDeadTimeBeamActive(LSRange[nls])

                    physics = 1
                    active = 1
                    psi = 99
                    for iterator in LSRange[nls]: ##Gets lowest value of physics, active, and psi in the set of lumisections
                        if RefLumiArray[5][iterator] == 0:
                            physics = 0
                        if RefLumiArray[6][iterator] == 0:
                            active = 0
                        if RefLumiArray[0][iterator] < psi:
                            psi = RefLumiArray[0][iterator]

                    MoreLumiMulti=LumiRangeGreens(RefMoreLumiArray,LSRange,nls,RefRunNum,deadtimebeamactive)
                    
                    if inst < 0 or live < 0 or delivered < 0:
                        print "Run "+str(RefRunNum)+" LS "+str(nls)+" inst lumi = "+str(inst)+" live lumi = "+str(live)+", delivered = "+str(delivered)+", physics = "+str(physics)+", active = "+str(active)


                    
                    LumiPageInfo[nls]=MoreLumiMulti

                    for key in TriggerRates:
                        if NoVersion:
                            name = StripVersion(key)
                        else:
                            name=key
                        if not name in trig_list:
                            if all_triggers:
                                trig_list.append(name)
                            else:
                                continue
                         
                        if not Rates.has_key(name):
                            Rates[name] = {}
                            Rates[name]["run"] = []
                            Rates[name]["ls"] = []
                            Rates[name]["ps"] = []
                            Rates[name]["inst_lumi"] = []
                            Rates[name]["live_lumi"] = []
                            Rates[name]["delivered_lumi"] = []
                            Rates[name]["deadtime"] = []
                            Rates[name]["rawrate"] = []
                            Rates[name]["rate"] = []
                            Rates[name]["rawxsec"] = []
                            Rates[name]["xsec"] = []
                            Rates[name]["physics"] = []
                            Rates[name]["active"] = []
                            Rates[name]["psi"] = []

                            
                        [avps, ps, rate, psrate] = TriggerRates[key]
                        Rates[name]["run"].append(RefRunNum)
                        Rates[name]["ls"].append(nls)
                        Rates[name]["ps"].append(ps)
                        Rates[name]["inst_lumi"].append(inst)
                        Rates[name]["live_lumi"].append(live)
                        Rates[name]["delivered_lumi"].append(delivered)
                        Rates[name]["deadtime"].append(deadtimebeamactive)
                        Rates[name]["rawrate"].append(rate)
                        if live == 0:
                            Rates[name]["rate"].append(0)
                            Rates[name]["rawxsec"].append(0.0)
                            Rates[name]["xsec"].append(0.0)
                        else:
                            Rates[name]["rate"].append(psrate/(1.0-deadtimebeamactive))                            
                            Rates[name]["rawxsec"].append(rate/live)
                            Rates[name]["xsec"].append(psrate/live)
                        Rates[name]["physics"].append(physics)
                        Rates[name]["active"].append(active)
                        Rates[name]["psi"].append(psi)

                        
                        #for keys, values in MoreLumiMulti.iteritems():
                        #    Rates[name][keys].append(values)
                            #print nls, name, keys, values
                                             
    RateOutput = open(RefRunFile, 'wb') ##Save new Rates[] to RefRuns
    pickle.dump(Rates, RateOutput, 2)
    RateOutput.close()
    LumiOutput = open(RefLumiFile,'wb')
    pickle.dump(LumiPageInfo,LumiOutput, 2)
    LumiOutput.close()
    
    
    return [Rates,LumiPageInfo]

def MakePlots(Rates, LumiPageInfo, run_list, trig_name, trig_list, num_ls, min_rate, max_dt, print_table, data_clean, plot_properties, masked_triggers, save_fits, debug_print, SubSystemOff, print_info,NoVersion, linear,do_inst, TMDerr,wp_bool,all_triggers):
    min_run = min(run_list)
    max_run = max(run_list)

    priot.has_been_called=False
    
    InputFit = {}
    OutputFit = {}
    first_trigger=True

    
    [[varX, varY, do_fit, save_root, save_png, fit_file]] = plot_properties

    RootNameTemplate = "%s_%sLS_%s_vs_%s_Run%s-%s.root"
    RootFile = RootNameTemplate % (trig_name, num_ls, varX, varY, min_run, max_run)

    if not do_fit:
        try:
            pkl_file = open(fit_file, 'rb')
            InputFit = pickle.load(pkl_file)
            
        except:
            print "ERROR: could not open fit file: %s" % (fit_file,)
    if save_root:
        try:
            os.remove(RootFile)
        except:
            pass

    trig_list_noV=[]
    for trigs in trig_list:
        trig_list_noV.append(StripVersion(trigs))
    if NoVersion:
        trig_list=trig_list_noV
    
    ## check that all the triggers we ask to plot are in the input fit
    if not save_fits:
        goodtrig_list = []
        FitInputNoV={}
        for trig in trig_list:
            
            if NoVersion:
                for trigger in InputFit.iterkeys():
                    FitInputNoV[StripVersion(trigger)]=InputFit[trigger]
                InputFit=FitInputNoV
                
                    
                
            else:
                if not InputFit.has_key(trig):
                    print "WARNING:  No Fit Prediction for Trigger %s, SKIPPING" % (trig,)
                else:
                    goodtrig_list.append(trig)
                trig_list = goodtrig_list

    

    for print_trigger in sorted(Rates):
        ##Limits Rates[] to runs in run_list
        NewTrigger = {}
        
        if not print_trigger in trig_list:
            if all_triggers:
                trig_list.append(print_trigger)
            else:
                print "not in trig_list:",print_trigger, trig_list
                continue
        
        for key in Rates[print_trigger]:
            NewTrigger[key] = []
        for iterator in range (len(Rates[print_trigger]["run"])):
            if Rates[print_trigger]["run"][iterator] in run_list:
                for key in Rates[print_trigger]:
                    NewTrigger[key].append(Rates[print_trigger][key][iterator])
        Rates[print_trigger] = NewTrigger
        
        
        meanrawrate = sum(Rates[print_trigger]["rawrate"])/len(Rates[print_trigger]["rawrate"])
        
        if not trig_name in print_trigger:
            print "failed",trig_name, print_trigger
            continue
        
        if meanrawrate < min_rate:
            continue
        masked_trig = False
        for mask in masked_triggers:
            if str(mask) in print_trigger:
                masked_trig = True
        if masked_trig:
            continue
        
        OutputFit[print_trigger] = {}

        lowlumi = 0
        meanlumi_init = median(Rates[print_trigger]["live_lumi"])
        meanlumi = 0
        highlumi = 0
        lowxsec = 0
        meanxsec = 0
        highxsec = 0
        nlow = 0
        nhigh = 0
        
        for iterator in range(len(Rates[print_trigger]["rate"])):
            if Rates[print_trigger]["live_lumi"][iterator] <= meanlumi_init:
                if ( Rates[print_trigger]["rawrate"][iterator] > 0.04 and Rates[print_trigger]["physics"][iterator] == 1 and Rates[print_trigger]["active"][iterator] == 1 and Rates[print_trigger]["deadtime"][iterator] < max_dt and Rates[print_trigger]["psi"][iterator] > 0 and Rates[print_trigger]["live_lumi"] > 500):
                    meanxsec+=Rates[print_trigger]["xsec"][iterator]
                    lowxsec+=Rates[print_trigger]["xsec"][iterator]
                    meanlumi+=Rates[print_trigger]["live_lumi"][iterator]
                    lowlumi+=Rates[print_trigger]["live_lumi"][iterator]
                    nlow+=1
            if Rates[print_trigger]["live_lumi"][iterator] > meanlumi_init:
                if ( Rates[print_trigger]["rawrate"][iterator] > 0.04 and Rates[print_trigger]["physics"][iterator] == 1 and Rates[print_trigger]["active"][iterator] == 1 and Rates[print_trigger]["deadtime"][iterator] < max_dt and Rates[print_trigger]["psi"][iterator] > 0 and Rates[print_trigger]["live_lumi"] > 500):
                    meanxsec+=Rates[print_trigger]["xsec"][iterator]
                    highxsec+=Rates[print_trigger]["xsec"][iterator]
                    meanlumi+=Rates[print_trigger]["live_lumi"][iterator]
                    highlumi+=Rates[print_trigger]["live_lumi"][iterator]
                    nhigh+=1
        try:
            meanxsec = meanxsec/(nlow+nhigh)
            meanlumi = meanlumi/(nlow+nhigh)
            slopexsec = ( (highxsec/nhigh) - (lowxsec/nlow) ) / ( (highlumi/nhigh) - (lowlumi/nlow) )
        except:
            #print str(print_trigger)+" has no good datapoints - setting initial xsec slope estimate to 0"
            meanxsec = median(Rates[print_trigger]["xsec"])
            meanlumi = median(Rates[print_trigger]["live_lumi"])
            slopexsec = 0

        [run_t,ls_t,ps_t,inst_t,live_t,delivered_t,deadtime_t,rawrate_t,rate_t,rawxsec_t,xsec_t,psi_t,e_run_t,e_ls_t,e_ps_t,e_inst_t,e_live_t,e_delivered_t,e_deadtime_t,e_rawrate_t,e_rate_t,e_rawxsec_t,e_xsec_t,e_psi_t,rawrate_fit_t,rate_fit_t,rawxsec_fit_t,xsec_fit_t,e_rawrate_fit_t,e_rate_fit_t,e_rawxsec_fit_t,e_xsec_fit_t] = MakePlotArrays()

        if not do_fit:
                                
            FitType = InputFit[print_trigger][0]
            X0 = InputFit[print_trigger][1]
            X1 = InputFit[print_trigger][2]
            X2 = InputFit[print_trigger][3]
            X3 = InputFit[print_trigger][4]
            sigma = InputFit[print_trigger][5]*3#Display 3 sigma band to show outliers more clearly
            X0err= InputFit[print_trigger][7]
            ##print print_trigger," X0err=",X0err
            #print str(print_trigger)+"  "+str(FitType)+"  "+str(X0)+"  "+str(X1)+"  "+str(X2)+"  "+str(X3)
            #if (first_trigger):
            #    print '%20s % 10s % 6s % 5s % 5s % 3s % 4s' % ('trigger', 'fit type ', 'cubic', 'quad', '  linear', ' c ', 'Chi2')
            #    first_trigger=False
            #print '%20s % 10s % 2.2g % 2.2g % 2.2g % 2.2g % 2.2g' % (print_trigger, FitType, X3, X2, X1, X0, Chi2)
            #print '{}, {}, {:02.2g}, {:02.2g}, {:02.2g}, {:02.2g} '.format(print_trigger, FitType, X0, X1, X2, X3)
        ## we are 2 lumis off when we start! -gets worse when we skip lumis
        it_offset=0
        for iterator in range(len(Rates[print_trigger]["rate"])):
            if not Rates[print_trigger]["run"][iterator] in run_list:
                continue
            prediction = meanxsec + slopexsec * (Rates[print_trigger]["live_lumi"][iterator] - meanlumi)
            realvalue = Rates[print_trigger]["xsec"][iterator]
            
            
            if pass_cuts(data_clean, realvalue, prediction, meanxsec, Rates, print_trigger, iterator, num_ls,LumiPageInfo,SubSystemOff,max_dt,print_info, trig_list):
                
                run_t.append(Rates[print_trigger]["run"][iterator])
                ls_t.append(Rates[print_trigger]["ls"][iterator])
                ps_t.append(Rates[print_trigger]["ps"][iterator])
                inst_t.append(Rates[print_trigger]["inst_lumi"][iterator])
                live_t.append(Rates[print_trigger]["live_lumi"][iterator])
                delivered_t.append(Rates[print_trigger]["delivered_lumi"][iterator])
                deadtime_t.append(Rates[print_trigger]["deadtime"][iterator])
                rawrate_t.append(Rates[print_trigger]["rawrate"][iterator])
                rate_t.append(Rates[print_trigger]["rate"][iterator])
                rawxsec_t.append(Rates[print_trigger]["rawxsec"][iterator])
                xsec_t.append(Rates[print_trigger]["xsec"][iterator])
                psi_t.append(Rates[print_trigger]["psi"][iterator])

                e_run_t.append(0.0)
                e_ls_t.append(0.0)
                e_ps_t.append(0.0)
                e_inst_t.append(14.14)
                e_live_t.append(14.14)
                e_delivered_t.append(14.14)
                e_deadtime_t.append(0.01)
                e_rawrate_t.append(math.sqrt(Rates[print_trigger]["rawrate"][iterator]/(num_ls*23.3)))
                e_rate_t.append(Rates[print_trigger]["ps"][iterator]*math.sqrt(Rates[print_trigger]["rawrate"][iterator]/(num_ls*23.3)))
                e_psi_t.append(0.0)
                if live_t[-1] == 0:
                    e_rawxsec_t.append(0)
                    e_xsec_t.append(0)
                else:
                    try: 
                        e_rawxsec_t.append(math.sqrt(Rates[print_trigger]["rawrate"][iterator]/(num_ls*23.3))/Rates[print_trigger]["live_lumi"][iterator])
                        e_xsec_t.append(Rates[print_trigger]["ps"][iterator]*math.sqrt(Rates[print_trigger]["rawrate"][iterator]/(num_ls*23.3))/Rates[print_trigger]["live_lumi"][iterator])
                    except:
                        e_rawxsec_t.append(0.)
                        e_xsec_t.append(0.)
                if not do_fit:
                    if not do_inst:
                        if FitType == "expo":
                            rate_prediction = X0 + X1*math.exp(X2+X3*delivered_t[-1])
                        else:
                            rate_prediction = X0 + X1*delivered_t[-1] + X2*delivered_t[-1]*delivered_t[-1] + X3*delivered_t[-1]*delivered_t[-1]*delivered_t[-1]
##                     if rate_t[-1] < 0.7 * rate_prediction or rate_t[-1] > 1.4 * rate_prediction:
##                         print str(run_t[-1])+"  "+str(ls_t[-1])+"  "+str(print_trigger)+"  "+str(ps_t[-1])+"  "+str(deadtime_t[-1])+"  "+str(rate_prediction)+"  "+str(rate_t[-1])+"  "+str(rawrate_t[-1])
                    else:
                        if FitType == "expo":
                            rate_prediction = X0 + X1*math.exp(X2+X3*inst_t[-1])
                        else:
                            rate_prediction = X0 + X1*inst_t[-1] + X2*inst_t[-1]*inst_t[-1] + X3*inst_t[-1]*inst_t[-1]*inst_t[-1]

                    if live_t[-1] == 0:
                        rawrate_fit_t.append(0)
                        rate_fit_t.append(0)
                        rawxsec_fit_t.append(0)
                        xsec_fit_t.append(0)
                        e_rawrate_fit_t.append(0)
                        e_rate_fit_t.append(sigma)
                        e_rawxsec_fit_t.append(0)
                        e_xsec_fit_t.append(0)
                        #print "live_t=0", ls_t[-1], rawrate_fit_t[-1]
                    else:
                        if ps_t[-1]>0.0:
                            rawrate_fit_t.append(rate_prediction*(1.0-deadtime_t[-1])/(ps_t[-1]))
                        else:
                            rawrate_fit_t.append(0.0)
                        
                        rate_fit_t.append(rate_prediction)                        
                        e_rate_fit_t.append(sigma)
                        rawxsec_fit_t.append(rawrate_fit_t[-1]/live_t[-1])
                        xsec_fit_t.append(rate_prediction*(1.0-deadtime_t[-1])/live_t[-1])
                        try:
                            
                            if not TMDerr:
                                e_rawrate_fit_t.append(sigma*rawrate_fit_t[-1]/rate_fit_t[-1])
                                e_rawxsec_fit_t.append(sigma*rawxsec_fit_t[-1]/rate_fit_t[-1])
                                e_xsec_fit_t.append(sigma*xsec_fit_t[-1]/rate_fit_t[-1])
                            ###error from TMD predictions, calculated at 5e33
                            else:
                                e_rawrate_fit_t.append(X0err*inst_t[-1]/5000.)
                                e_rawxsec_fit_t.append(X0err/live_t[-1]*inst_t[-1]/5000.)
                                e_xsec_fit_t.append(X0err/live_t[-1]*inst_t[-1]/5000.)
                                
                        except:
                            print print_trigger, "has no fitted rate for LS", Rates[print_trigger]["ls"][iterator]
                            e_rawrate_fit_t.append(sigma)
                            e_rawxsec_fit_t.append(sigma)
                            e_xsec_fit_t.append(sigma)
                        #print "live_t>0", ls_t[-1], rawrate_fit_t[-1]

                ##print iterator, iterator, "ls=",ls_t[-1],"rate=",round(rawrate_t[-1],2), "deadtime=",round(deadtime_t[-1],2),"rawrate_fit=",round(rawrate_fit_t[-1],2),"max it=",len(Rates[print_trigger]["rate"])
                
                if (print_info and num_ls==1 and (fabs(rawrate_fit_t[-1]-rawrate_t[-1])>2.5*sqrt(sum(Rates[print_trigger]["rawrate"])/len(Rates[print_trigger]["rawrate"])))):
                    pass
                    ###print '%-60s has a bad prediction, run=%-10s LS=%-4s' % (print_trigger, Rates[print_trigger]["run"][iterator], Rates[print_trigger]["ls"][iterator])

            else: ##If the data point does not pass the data_clean filter
                #print "not passed", iterator, ls_t[-1], rawrate_fit_t[-1]
                if debug_print:
                    print str(print_trigger)+" has xsec "+str(round(Rates[print_trigger]["xsec"][iterator],6))+" at lumi "+str(round(Rates[print_trigger]["live_lumi"][iterator],2))+" where the expected value is "+str(prediction)

        ## End "for iterator in range(len(Rates[print_trigger]["rate"])):" loop

        AllPlotArrays = [run_t,ls_t,ps_t,inst_t,live_t,delivered_t,deadtime_t,rawrate_t,rate_t,rawxsec_t,xsec_t,psi_t,e_run_t,e_ls_t,e_ps_t,e_inst_t,e_live_t,e_delivered_t,e_deadtime_t,e_rawrate_t,e_rate_t,e_rawxsec_t,e_xsec_t,e_psi_t,rawrate_fit_t,rate_fit_t,rawxsec_fit_t,xsec_fit_t,e_rawrate_fit_t,e_rate_fit_t,e_rawxsec_fit_t,e_xsec_fit_t]
        
        [VX, VXE, VY, VYE, VF, VFE] = GetVXVY(plot_properties, fit_file, AllPlotArrays)
        
        if save_root or save_png:
            c1 = TCanvas(str(varX),str(varY))
            c1.SetName(str(print_trigger)+"_"+str(varY)+"_vs_"+str(varX))
       
        try:
            gr1 = TGraphErrors(len(VX), VX, VY, VXE, VYE)
        except:
            print "No lumisections with events for", print_trigger, "probably due to v high deadtime"
            continue
        gr1.SetName("Graph_"+str(print_trigger)+"_"+str(varY)+"_vs_"+str(varX))
        gr1.GetXaxis().SetTitle(varX)
        gr1.GetYaxis().SetTitle(varY)
        gr1.SetTitle(str(print_trigger))
        gr1.SetMinimum(0)
        gr1.SetMaximum(1.2*max(VY))
        #gr1.GetXaxis().SetLimits(min(VX)-0.2*max(VX),1.2*max(VX))
        gr1.GetXaxis().SetLimits(0,1.2*max(VX))
        gr1.SetMarkerStyle(8)
        
            
        if fit_file:
            gr1.SetMarkerSize(0.8)
        else:
            gr1.SetMarkerSize(0.5)
        gr1.SetMarkerColor(2)

        if not do_fit:
            gr3 = TGraphErrors(len(VX), VX, VF, VXE, VFE)
            gr3.SetMarkerStyle(8)
            gr3.SetMarkerSize(0.4)
            gr3.SetMarkerColor(4)
            gr3.SetFillColor(4)
            gr3.SetFillStyle(3003)
            
        if do_fit:
            if "rate" in varY and not linear:
                
                f1a=0
                f1a = TF1("f1a","pol2",0,8000)
                f1a.SetLineColor(4)
                f1a.SetLineWidth(2)
                #f1a.SetParLimits(0,0,0.2*(sum(VY)/len(VY))+0.8*min(VY))
                #f1a.SetParLimits(1,0,2.0*max(VY)/(max(VX)*max(VX)))
                gr1.Fit("f1a","QN","rob=0.90")


                f1d=0
                f1d = TF1("f1d","pol1",0,8000)#linear
                f1d.SetLineColor(4)
                f1d.SetLineWidth(2)
                #f1a.SetParLimits(0,0,0.2*(sum(VY)/len(VY))+0.8*min(VY))
                #f1a.SetParLimits(1,0,2.0*max(VY)/(max(VX)*max(VX)))
                gr1.Fit("f1d","QN","rob=0.90")     
                                
                f1b = 0
                f1c = 0
                meanps = median(Rates[print_trigger]["ps"])
                av_rte = mean(VY)
                
                if True:
                    f1b = TF1("f1b","pol3",0,8000)
                    f1b.SetLineColor(2)
                    f1b.SetLineWidth(2)
##                     f1b.SetParLimits(0,0,0.2*(sum(VY)/len(VY))+0.8*min(VY))
##                     f1b.SetParLimits(1,0,f1a.GetParameter(1)+0.0000001)
##                     f1b.SetParLimits(2,0,f1a.GetParameter(2)+0.0000000001)
##                     f1b.SetParLimits(3,0,2.0*max(VY)/(max(VX)*max(VX)*max(VX)))
                    gr1.Fit("f1b","QN","rob=0.90")
##                     #if f1b.GetChisquare()/f1b.GetNDF() < f1a.GetChisquare()/f1a.GetNDF():
##                     #print "X0 = "+str(f1a.GetParameter(0))+" X1 = "+str(f1a.GetParameter(1))+" X2 = "+str(f1a.GetParameter(2))
##                     #print str(print_trigger)+" f1a Chi2 = "+str(10*f1a.GetChisquare()*math.sqrt(len(VY))/(math.sqrt(sum(VY))*num_ls*f1a.GetNDF()))+", f1b Chi2 = "+str(10*f1b.GetChisquare()*math.sqrt(len(VY))/(math.sqrt(sum(VY))*num_ls*f1b.GetNDF()))
##                     #print "X0 = "+str(f1b.GetParameter(0))+" X1 = "+str(f1b.GetParameter(1))+" X2 = "+str(f1b.GetParameter(2))+" X3 = "+str(f1b.GetParameter(3))
##                     if (first_trigger):
##                         print '%-60s %4s  x0             x1                    x2                    x3                   chi2     ndf chi2/ndf' % ('trigger', 'type')
                        
##                         first_trigger=False
                    
                    
                    
                    f1c = TF1("f1c","[0]+[1]*expo(2)",0,8000)
                    f1c.SetLineColor(3)
                    f1c.SetLineWidth(2)
                    f1c.SetParLimits(0,0,0.2*(sum(VY)/len(VY))+0.8*min(VY))
                    f1c.SetParLimits(1,max(VY)/math.exp(10.0),max(VY)/math.exp(2.0))
                    f1c.SetParLimits(2,0.0,0.0000000001)
                    f1c.SetParLimits(3,2.0/max(VX),10.0/max(VX))
                    gr1.Fit("f1c","QN","rob=0.90")
##                     #if f1c.GetChisquare()/f1c.GetNDF() < f1a.GetChisquare()/f1a.GetNDF():
##                     #print str(print_trigger)+" f1a Chi2 = "+str(10*f1a.GetChisquare()*math.sqrt(len(VY))/(math.sqrt(sum(VY))*num_ls*f1a.GetNDF()))+", f1c Chi2 = "+str(10*f1c.GetChisquare()*math.sqrt(len(VY))/(math.sqrt(sum(VY))*num_ls*f1c.GetNDF()))
##                     #print "X0 = "+str(f1c.GetParameter(0))+" X1 = "+str(f1c.GetParameter(1))+" X2 = "+str(f1c.GetParameter(2))+" X3 = "+str(f1c.GetParameter(3))
                    

                    ## if (f1c.GetChisquare()/f1c.GetNDF() < f1b.GetChisquare()/f1b.GetNDF() and f1c.GetChisquare()/f1c.GetNDF() < f1a.GetChisquare()/f1a.GetNDF()):
##                         print '%-60s expo % .2f+/-%.2f   % .2e+/-%.1e   % .2e+/-%.1e   % .2e+/-%.1e   %7.2f   %4.0f   %5.3f ' % (print_trigger, f1c.GetParameter(0), f1c.GetParError(0), f1c.GetParameter(1), f1c.GetParError(1), 0                  , 0                 , 0                  , 0                 , f1c.GetChisquare(), f1c.GetNDF(), f1c.GetChisquare()/f1c.GetNDF())
##                     elif (f1b.GetChisquare()/f1b.GetNDF() < f1a.GetChisquare()/f1a.GetNDF()):
##                         print '%-60s cube % .2f+/-%.2f   % .2e+/-%.1e   % .2e+/-%.1e   % .2e+/-%.1e   %7.2f   %4.0f   %5.3f ' % (print_trigger, f1b.GetParameter(0), f1b.GetParError(0), f1b.GetParameter(1), f1b.GetParError(1), f1b.GetParameter(2), f1b.GetParError(2), f1b.GetParameter(3), f1b.GetParError(3), f1b.GetChisquare(), f1b.GetNDF(), f1b.GetChisquare()/f1b.GetNDF())
##                     else:
                    
#                print f1a.GetChisquare()/f1a.GetNDF(), f1b.GetChisquare()/f1b.GetNDF(), f1c.GetChisquare()/f1c.GetNDF() 
                    
            else: ##If this is not a rate plot
                f1a = TF1("f1a","pol1",0,8000)
                f1a.SetLineColor(4)
                f1a.SetLineWidth(2)
                if "xsec" in varY:
                    f1a.SetParLimits(0,0,meanxsec*1.5)
                    if slopexsec > 0:
                        f1a.SetParLimits(1,0,max(VY)/max(VX))
                    else:
                        f1a.SetParLimits(1,2*slopexsec,-2*slopexsec)
                else:
                    f1a.SetParLimits(0,-1000,1000)
                gr1.Fit("f1a","Q","rob=0.80")

                if (first_trigger):
                        print '%-60s %4s  x0             x1                    x2                    x3                   chi2     ndf chi2/ndf' % ('trigger', 'type')
                        first_trigger=False
                try:
                    print '%-60s | line | % .2f | +/-%.2f |   % .2e | +/-%.1e |   % .2e | +/-%.1e |   % .2e | +/-%.1e |   %7.2f |   %4.0f |   %5.3f | ' % (print_trigger, f1a.GetParameter(0), f1a.GetParError(0), f1a.GetParameter(1), f1a.GetParError(1), 0                  , 0                 , 0                  , 0                 , f1a.GetChisquare(), f1a.GetNDF(), f1a.GetChisquare()/f1a.GetNDF())
                except:
                    pass
                
        if print_table or save_fits:
            if not do_fit:
                print "Can't have save_fits = True and do_fit = False"
                continue
            try:
                if (f1c.GetChisquare()/f1c.GetNDF() < (f1a.GetChisquare()/f1a.GetNDF()-1) and (f1b.GetChisquare()/f1b.GetNDF() < f1a.GetChisquare()/f1a.GetNDF()-1)):
                    print '%-60s | expo | % .2f | +/-%.2f |   % .2e | +/-%.1e |   % .2e | +/-%.1e |   % .2e | +/-%.1e |   %7.2f |   %4.0f |   %5.3f | ' % (print_trigger, f1c.GetParameter(0) , f1c.GetParError(0) , f1c.GetParameter(1) , f1c.GetParError(1) , f1c.GetParameter(2), f1c.GetParError(2) ,f1c.GetParameter(3), f1c.GetParError(3) ,f1c.GetChisquare() , f1c.GetNDF() , f1c.GetChisquare()/f1c.GetNDF())
                    f1c.SetLineColor(1)                    
                    priot(wp_bool,print_trigger,meanps,f1d,f1c,"expo",av_rte)                    
                    sigma = CalcSigma(VX, VY, f1c)*math.sqrt(num_ls)                    
                    OutputFit[print_trigger] = ["expo", f1c.GetParameter(0) , f1c.GetParameter(1) , f1c.GetParameter(2) , f1c.GetParameter(3) , sigma , meanrawrate, f1c.GetParError(0) , f1c.GetParError(1) , f1c.GetParError(2) , f1c.GetParError(3)]

                elif (f1b.GetChisquare()/f1b.GetNDF() < (f1a.GetChisquare()/f1a.GetNDF()-1)):
                    print '%-60s | cube | % .2f | +/-%.2f |   % .2e | +/-%.1e |   % .2e | +/-%.1e |   % .2e | +/-%.1e |   %7.2f |   %4.0f |   %5.3f | ' % (print_trigger, f1b.GetParameter(0) , f1b.GetParError(0) , f1b.GetParameter(1) , f1b.GetParError(1) , f1b.GetParameter(2), f1b.GetParError(2) ,f1b.GetParameter(3), f1b.GetParError(3), f1b.GetChisquare() , f1b.GetNDF() , f1b.GetChisquare()/f1b.GetNDF())
                    f1b.SetLineColor(1)
                    priot(wp_bool,print_trigger,meanps,f1d,f1b,"cubic",av_rte)
                    sigma = CalcSigma(VX, VY, f1b)*math.sqrt(num_ls)                                        
                    OutputFit[print_trigger] = ["poly", f1b.GetParameter(0) , f1b.GetParameter(1) , f1b.GetParameter(2) , f1b.GetParameter(3) , sigma , meanrawrate, f1b.GetParError(0) , f1b.GetParError(1) , f1b.GetParError(2) , f1b.GetParError(3)]

                else:
                    print '%-60s | quad | % .2f | +/-%.2f |   % .2e | +/-%.1e |   % .2e | +/-%.1e |   % .2e | +/-%.1e |   %7.2f |   %4.0f |   %5.3f | ' % (print_trigger, f1a.GetParameter(0) , f1a.GetParError(0) , f1a.GetParameter(1) , f1a.GetParError(1) , f1a.GetParameter(2), f1a.GetParError(2), 0                  , 0                 , f1a.GetChisquare() , f1a.GetNDF() , f1a.GetChisquare()/f1a.GetNDF())
                    f1a.SetLineColor(1)
                    priot(wp_bool,print_trigger,meanps,f1d,f1a,"quad",av_rte)
                    sigma = CalcSigma(VX, VY, f1a)*math.sqrt(num_ls)
                    OutputFit[print_trigger] = ["poly", f1a.GetParameter(0) , f1a.GetParameter(1) , f1a.GetParameter(2) , 0.0 , sigma , meanrawrate, f1a.GetParError(0) , f1a.GetParError(1) , f1a.GetParError(2) , 0.0]

            except ZeroDivisionError:
                print "No NDF for",print_trigger,"skipping"
 
        if save_root or save_png:
            gr1.Draw("APZ")
            if not do_fit:
                gr3.Draw("P3")
            if do_fit:
                f1a.Draw("same")
                try:
                    f1b.Draw("same")
                    f1c.Draw("same")
                    f1d.Draw("same")
                except:
                    True
            c1.Update()
            if save_root:
                myfile = TFile( RootFile, 'UPDATE' )
                c1.Write()
                myfile.Close()
            if save_png:
                c1.SaveAs(str(print_trigger)+"_"+str(varY)+"_vs_"+str(varX)+".png")
                
            
            ##print print_trigger, OutputFit[print_trigger]
    if save_root:
        print "Output root file is "+str(RootFile)

    if save_fits:
        #FitNameTemplate = "Fits/%/Fit_%s_%sLS_Run%sto%s.pkl" % (thisyear)
        #FitFile = FitNameTemplate % (trig_name, num_ls, min_run, max_run)
        if os.path.exists(fit_file):
            os.remove(fit_file)
        FitOutputFile = open(fit_file, 'wb')
        pickle.dump(OutputFit, FitOutputFile, 2)
        FitOutputFile.close()
        print "Output fit file is "+str(fit_file)

    if print_table:
        print "The expo fit is of the form p0+p1*e^(p2*x), poly is p0+(p1/10^3)*x+(p2/10^6)*x^2+(p3/10^9)*x^3, where x is Deliv. Lumi."
        print '%60s%10s%10s%10s%10s%10s%10s%10s' % ("Trig", "fit", "p0", "p1", "p2", "p3", "Chi2", "Av raw")
        for print_trigger in OutputFit:
            _trigger = (print_trigger[:56] + '...') if len(print_trigger) > 59 else print_trigger
            try:
                if OutputFit[print_trigger][0] == "poly":
                    print '%60s%10s%10s%10s%10s%10s%10s' % (_trigger, OutputFit[print_trigger][0], round(OutputFit[print_trigger][1],3), round(OutputFit[print_trigger][2],6)*1000, round(OutputFit[print_trigger][3],9)*1000000, round(OutputFit[print_trigger][4],12)*1000000000, round(OutputFit[print_trigger][5],2), round(OutputFit[print_trigger][6],3))
                else:
                    print '%60s%10s%10s%10s%10s%10s%10s' % (_trigger, OutputFit[print_trigger][0], OutputFit[print_trigger][1], OutputFit[print_trigger][2], OutputFit[print_trigger][3], OutputFit[print_trigger][4], round(OutputFit[print_trigger][5],2), round(OutputFit[print_trigger][6],3))
            except:
                print str(print_trigger)+" is somehow broken"
    return RootFile

  ############# SUPPORTING FUNCTIONS ################


def CalcSigma(var_x, var_y, func):
    residuals = []
    for x, y in zip(var_x,var_y):
        residuals.append(y - func.Eval(x,0,0))

    res_squared = [i*i for i in residuals]
    if len(res_squared) > 2:
        sigma = math.sqrt(sum(res_squared)/(len(res_squared)-2))
    else:
        sigma = 0
    return sigma

def GetJSON(json_file):

    input_file = open(json_file)
    file_content = input_file.read()
    inputRange = selectionParser(file_content)
    JSON = inputRange.runsandls()
    return JSON
    ##JSON is an array: JSON[run_number] = [1st ls, 2nd ls, 3rd ls ... nth ls]

def MakePlotArrays():
    run_t = array.array('f')
    ls_t = array.array('f')
    ps_t = array.array('f')
    inst_t = array.array('f')
    live_t = array.array('f')
    delivered_t = array.array('f')
    deadtime_t = array.array('f')
    rawrate_t = array.array('f')
    rate_t = array.array('f')
    rawxsec_t = array.array('f')
    xsec_t = array.array('f')
    psi_t = array.array('f')
    
    e_run_t = array.array('f')
    e_ls_t = array.array('f')
    e_ps_t = array.array('f')
    e_inst_t = array.array('f')
    e_live_t = array.array('f')
    e_delivered_t = array.array('f')
    e_deadtime_t = array.array('f')
    e_rawrate_t = array.array('f')
    e_rate_t = array.array('f')
    e_rawxsec_t = array.array('f')
    e_xsec_t = array.array('f')
    e_psi_t = array.array('f')
    
    rawrate_fit_t = array.array('f')
    rate_fit_t = array.array('f')
    rawxsec_fit_t = array.array('f')
    xsec_fit_t = array.array('f')
    e_rawrate_fit_t = array.array('f')
    e_rate_fit_t = array.array('f')
    e_rawxsec_fit_t = array.array('f')
    e_xsec_fit_t = array.array('f')
    
    return [run_t,ls_t,ps_t,inst_t,live_t,delivered_t,deadtime_t,rawrate_t,rate_t,rawxsec_t,xsec_t,psi_t,e_run_t,e_ls_t,e_ps_t,e_inst_t,e_live_t,e_delivered_t,e_deadtime_t,e_rawrate_t,e_rate_t,e_rawxsec_t,e_xsec_t,e_psi_t,rawrate_fit_t,rate_fit_t,rawxsec_fit_t,xsec_fit_t,e_rawrate_fit_t,e_rate_fit_t,e_rawxsec_fit_t,e_xsec_fit_t]


def GetVXVY(plot_properties, fit_file, AllPlotArrays):

    VF = "0"
    VFE = "0"

    [run_t,ls_t,ps_t,inst_t,live_t,delivered_t,deadtime_t,rawrate_t,rate_t,rawxsec_t,xsec_t,psi_t,e_run_t,e_ls_t,e_ps_t,e_inst_t,e_live_t,e_delivered_t,e_deadtime_t,e_rawrate_t,e_rate_t,e_rawxsec_t,e_xsec_t,e_psi_t,rawrate_fit_t,rate_fit_t,rawxsec_fit_t,xsec_fit_t,e_rawrate_fit_t,e_rate_fit_t,e_rawxsec_fit_t,e_xsec_fit_t] = AllPlotArrays
    for varX, varY, do_fit, save_root, save_png, fit_file in plot_properties:
        if varX == "run":
            VX = run_t
            VXE = run_t_e
        elif varX == "ls":
            VX = ls_t
            VXE = e_ls_t
        elif varX == "ps":
            VX = ps_t
            VXE = e_ps_t
        elif varX == "inst":
            VX = inst_t
            VXE = e_inst_t
        elif varX == "live":
            VX = live_t
            VXE = e_live_t
        elif varX == "delivered":
            VX = delivered_t
            VXE = e_delivered_t
        elif varX == "deadtime":
            VX = deadtime_t
            VXE = e_deadtime_t
        elif varX == "rawrate":
            VX = rawrate_t
            VXE = e_rawrate_t
        elif varX == "rate":
            VX = rate_t
            VXE = e_rate_t
        elif varX == "rawxsec":
            VX = rawxsec_t
            VXE = e_rawxsec_t
        elif varX == "xsec":
            VX = xsec_t
            VXE = e_xsec_t
        elif varX == "psi":
            VX = psi_t
            VXE = e_psi_t
        else:
            print "No valid variable entered for X"
            continue
        if varY == "run":
            VY = run_t
            VYE = run_t_e
        elif varY == "ls":
            VY = ls_t
            VYE = e_ls_t
        elif varY == "ps":
            VY = ps_t
            VYE = e_ps_t
        elif varY == "inst":
            VY = inst_t
            VYE = e_inst_t
        elif varY == "live":
            VY = live_t
            VYE = e_live_t
        elif varY == "delivered":
            VY = delivered_t
            VYE = e_delivered_t
        elif varY == "deadtime":
            VY = deadtime_t
            VYE = e_deadtime_t
        elif varY == "rawrate":
            VY = rawrate_t
            VYE = e_rawrate_t
            if fit_file:
                VF = rawrate_fit_t
                VFE = e_rawrate_fit_t
        elif varY == "rate":
            VY = rate_t
            VYE = e_rate_t
            if fit_file:
                VF = rate_fit_t
                VFE = e_rate_fit_t
        elif varY == "rawxsec":
            VY = rawxsec_t
            VYE = e_rawxsec_t
            if fit_file:
                VF = rawxsec_fit_t
                VFE = e_rawxsec_fit_t
        elif varY == "xsec":
            VY = xsec_t
            VYE = e_xsec_t
            if fit_file:
                VF = xsec_fit_t
                VFE = e_xsec_fit_t
        elif varY == "psi":
            VY = psi_t
            VYE = e_psi_t
        else:
            print "No valid variable entered for Y"
            continue

    return [VX, VXE, VY, VYE, VF, VFE]

def pass_cuts(data_clean, realvalue, prediction, meanxsec, Rates, print_trigger, iterator, num_ls,LumiPageInfo,SubSystemOff, max_dt, print_info, trig_list):
    it_offset=0
    Passed=True
    subsystemfailed=[]
    
    if num_ls==1:
        ##fit is 2 ls ahead of real rate
        

        LS=Rates[print_trigger]["ls"][iterator]
        #print "ls=",LS,
        LSRange=LumiPageInfo[LS]["LSRange"]
        #print LSRange,
        LS2=LSRange[-1]
        #LS2=LSRange.pop()
        #print "LS2=",LS2

        #print LumiPageInfo[LS]
        lumidict={}
        lumidict=LumiPageInfo[LS]
        

        
            
            
        if print_info:
            if (iterator==0 and print_trigger==trig_list[0]):
                print '%10s%10s%10s%10s%10s%10s%10s%15s%20s' % ("Status", "Run", "LS", "Physics", "Active", "Deadtime", " MaxDeadTime", " Passed all subsystems?", " List of Subsystems failed")
            
        ## if SubSystemOff["All"]:
##             for keys in LumiPageInfo[LS]:
##                 #print LS, keys, LumiPageInfo[LS][keys]
##                 if not LumiPageInfo[LS][keys]:
##                     Passed=False
##                     subsystemfailed.append(keys)
##                     break
##         else:
        if SubSystemOff["Mu"] or SubSystemOff["All"]:
            if not (LumiPageInfo[LS]["rpc"] and LumiPageInfo[LS]["dt0"] and LumiPageInfo[LS]["dtp"] and LumiPageInfo[LS]["dtm"] and LumiPageInfo[LS]["cscp"] and LumiPageInfo[LS]["cscm"]):
                Passed=False
                subsystemfailed.append("Mu")
        if SubSystemOff["HCal"] or SubSystemOff["All"]:
            if not (LumiPageInfo[LS]["hbhea"] and LumiPageInfo[LS]["hbheb"] and LumiPageInfo[LS]["hbhec"]):
                Passed=False
                subsystemfailed.append("HCal")
            if (SubSystemOff["EndCap"]  or SubSystemOff["All"]) and not (LumiPageInfo[LS]["hf"]):
                Passed=False
                subsystemfailed.append("HCal-EndCap")
        if SubSystemOff["ECal"] or SubSystemOff["All"]:
            if not (LumiPageInfo[LS]["ebp"] and LumiPageInfo[LS]["ebm"]):
                Passed=False
                subsystemfailed.append("ECal")
            if (SubSystemOff["EndCap"] or SubSystemOff["All"]) and not (LumiPageInfo[LS]["eep"] and LumiPageInfo[LS]["eem"] and LumiPageInfo[LS]["esp"] or LumiPageInfo[LS]["esm"]):
                Passed=False
                subsystemfailed.append("ECal-EndCap")
        if SubSystemOff["Tracker"] or SubSystemOff["All"]:
            if not (LumiPageInfo[LS]["tob"] and LumiPageInfo[LS]["tibtid"] and LumiPageInfo[LS]["bpix"] and LumiPageInfo[LS]["fpix"]):
                Passed=False
                subsystemfailed.append("Tracker")
            if (SubSystemOff["EndCap"] or SubSystemOff["All"]) and not (LumiPageInfo[LS]["tecp"] and LumiPageInfo[LS]["tecm"]):
                Passed=False
                subsystemfailed.append("Tracker-EndCap")
        if SubSystemOff["Beam"] or SubSystemOff["All"]:
            if not(LumiPageInfo[LS]["b1pres"] and LumiPageInfo[LS]["b2pres"] and LumiPageInfo[LS]["b1stab"] and LumiPageInfo[LS]["b2stab"]):
                Passed=False
                subsystemfailed.append("Beam")
    else:
        
        Passed=True
            
    
        
    if not data_clean or (
        
        Rates[print_trigger]["physics"][iterator] == 1
        and Rates[print_trigger]["active"][iterator] == 1
        and Rates[print_trigger]["deadtime"][iterator] < max_dt
        #and Rates[print_trigger]["psi"][iterator] > 0
        and Passed
        ):
        #print LS, "True"
        if (print_info and num_ls==1 and (realvalue <0.4*prediction or realvalue>2.5*prediction)):
            pass
            ##print '%-60s%10s%10s%10s%10s%10s%10s%10s%15s%20s' % (print_trigger,"Passed", Rates[print_trigger]["run"][iterator], LS, Rates[print_trigger]["physics"][iterator], Rates[print_trigger]["active"][iterator], round(Rates[print_trigger]["deadtime"][iterator],2), max_dt, Passed, subsystemfailed)
        
        return True
    else:
        
        if (print_info and print_trigger==trig_list[0] and num_ls==1):
            print '%10s%10s%10s%10s%10s%10s%10s%15s%20s' % ("Failed", Rates[print_trigger]["run"][iterator], LS, Rates[print_trigger]["physics"][iterator], Rates[print_trigger]["active"][iterator], round(Rates[print_trigger]["deadtime"][iterator],2), max_dt, Passed, subsystemfailed)
        
        return False


#### LumiRangeGreens ####    
####inputs: RefMoreLumiArray --dict with lumi page info in LS by LS blocks,
####        LRange           --list range over lumis,
####        nls              --number of lumisections
####        RefRunNum        --run number
####
####outputs RangeMoreLumi    --lumi page info in dict LSRange blocks with lumi, added items Run and LSRange
def LumiRangeGreens(RefMoreLumiArray,LSRange,nls,RefRunNum,deadtimebeamactive):
  
    RangeMoreLumi={}
    for keys,values in RefMoreLumiArray.iteritems():
        RangeMoreLumi[keys]=1
  
    for iterator in LSRange[nls]:
        for keys, values in RefMoreLumiArray.iteritems():
            if RefMoreLumiArray[keys][iterator]==0:
                RangeMoreLumi[keys]=0
    RangeMoreLumi['LSRange']=LSRange[nls]
    RangeMoreLumi['Run']=RefRunNum
    RangeMoreLumi['DeadTimeBeamActive']=deadtimebeamactive
    return RangeMoreLumi
                        
#### CheckLumis ####
####inputs: 
####        PageLumiInfo      --dict of LS with dict of some lumipage info
####        Rates            --dict of triggernames with dict of info
def checkLS(Rates, PageLumiInfo,trig_list):
    rateslumis=Rates[trig_list[-1]]["ls"]
    keys=PageLumiInfo.keys()
    print "lumi run=",PageLumiInfo[keys[-1]]["Run"]
    ll=0
    for ls in keys:
        print ls,rateslumis[ll]
        ll=ll+1
    return False




if __name__=='__main__':
    global thisyear
    main()
