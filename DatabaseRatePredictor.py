#!/usr/bin/env python

from DatabaseParser import *
from GetListOfRuns import *
import sys
import os
from numpy import *
import pickle
import getopt

from ROOT import gROOT, TCanvas, TF1, TGraph, TGraphErrors, TPaveStats, gPad, gStyle
from ROOT import TFile, TPaveText, TBrowser
from ROOT import gBenchmark
import array
import math
from ReadConfig import RateMonConfig

from selectionParser import selectionParser

def usage():
    print sys.argv[0]+" [options] <list of runs>"
    print "This script is used to generate fits and do secondary shifter validation"
    print "<list of runs>                       this is a list of the form: a b c-d e f-g, specifying individual runs and/or run ranges"
    print "                                     be careful with using ranges (c-d), it is highly recommended to use a JSON in this case"
    print "options: "
    print "--makeFits                           run in fit making mode"
    print "--secondary                          run in secondary shifter mode"
    print "--fitFile=<path>                     path to the fit file"
    print "--json=<path>                        path to the JSON file"
    print "--TriggerList=<path>                 path to the trigger list (without versions!)"

class Modes:
    none,fits,secondary = range(3)

def main():
    try:
        try:
            opt, args = getopt.getopt(sys.argv[1:],"",["makeFits","secondary","fitFile=","json=","TriggerList="])
            
        except getopt.GetoptError, err:
            print str(err)
            usage()
            sys.exit(2)
            
##     if len(args)<1:
##         print "\nPlease specify at least 1 run to look at\n"
##         usage()
##         sys.exit(0)

        run_list=[]
        
        print "args=",args
        if len(args)<1:
            inputrunlist=[]
            print "No runs specified"
            runinput=raw_input("Enter run range in form <run1> <run2> <run3> or <run1>-<run2>:")
            print "runinput=",runinput
            inputrunlist.append(runinput)

            
            if runinput.find(' ')!=-1:
                args=runinput.split(' ')
            else:
                args.append(runinput)    
            
            print "inputrunlist=",inputrunlist
            print "args=",args
        print "args again=",args
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
        print "modified run list=",run_list
    

        mode = Modes.none
        fitFile = ""
        jsonfile = ""
        trig_list = []
    
        for o,a in opt:
            if o == "--makeFits":
                mode = Modes.fits
            elif o == "--secondary":
                mode = Modes.secondary
            elif o == "--fitFile":
                fitFile = str(a)
            elif o == "--json":
                jsonfile = a
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
            path="Fits/2011/"  # insert the path to the directory of interest
            dirList=os.listdir(path)
            for fname in dirList:
                print fname
            fitFile = raw_input("Enter fit file in format Fit_HLT_10LS_Run176023to180252.pkl: ")
        ##usage()
        ##sys.exit(0)
        elif fitFile=="":
            fitFile="Fits/2011/Fit_HLT_10LS_Run%sto%s.pkl" % (min(run_list),max(run_list))
            print "fit file=",fitFile

        if trig_list == []:
        
            print "\nPlease specify list of triggers\n"
            print "Available lists are:"
            dirList=os.listdir(".")
            for fname in dirList:
                entry=fname
                if entry.find('.')!=-1:
                    extension = entry[entry.find('.'):]   ## We can point this to the existing monitor list, just remove everything after ':'!
                    if extension==".list":
                        print fname
            trig_input=raw_input("\nEnter triggers in format HLT_IsoMu24_eta2p1 or a .list file: ")
        
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
        
                    
            
            
        ##usage()
        ##sys.exit(0)

    
    
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
            min_rate = 0.1
            print_table = False
            data_clean = True ##Gets rid of anomalous rate points, reqires physics_active_psi (PAP) and deadtime < 20%
            ##plot_properties = [varX, varY, do_fit, save_root, save_png, fit_file]
            plot_properties = [["delivered", "rate", True, True, False, fitFile]]
        
            masked_triggers = ["AlCa_", "DST_", "HLT_L1", "HLT_L2", "HLT_Zero"]
            save_fits = True
            max_dt=0.08 ## no deadtime cutuse 2.0
            force_new=True
            print_info=True
            SubSystemOff={'All':False,'Mu':False,'HCal':False,'ECal':False,'Tracker':False,'EndCap':False,'Beam':True}
    

        ###### TO SEE RATE VS PREDICTION ########
        if mode == Modes.secondary:
            trig_name = "HLT"
            num_ls = 1
            physics_active_psi = True
            debug_print = False
            no_versions=False
            min_rate = 1.0
            print_table = False
            data_clean = True
            ##plot_properties = [varX, varY, do_fit, save_root, save_png, fit_file]
            ##plot_properties = [["ls", "rawrate", False, True, False, "Fits/2011/Fit_HLT_10LS_Run176023to180252.pkl"]]
            ##plot_properties = [["ls", "rawrate", False, True, False, "Fits/2011/Fit_HLT_10LS_Run179497to180252.pkl"]]
            plot_properties = [["ls", "rawrate", False, True, False,fitFile]]

            masked_triggers = ["AlCa_", "DST_", "HLT_L1", "HLT_L2", "HLT_Zero"]
            save_fits = False
            max_dt=2.0 ## no deadtime cut=2.0
            force_new=True
            print_info=True
            SubSystemOff={'All':True,'Mu':False,'HCal':False,'ECal':False,'Tracker':False,'EndCap':False,'Beam':True}

    
    
    
    
        ########  END PARAMETERS - CALL FUNCTIONS ##########
        [Rates,LumiPageInfo]= GetDBRates(run_list, trig_name, trig_list, num_ls, max_dt, physics_active_psi, JSON, debug_print, force_new, SubSystemOff)
        ##if not checkLS(Rates,LumiPageInfo,trig_list):
        ##    print "Missing LS!"
    
    
        ##for iterator in range(len(Rates["HLT_IsoMu30_eta2p1"]["rawrate"])):
        ##    print iterator, "ls=",Rates["HLT_IsoMu30_eta2p1"]["ls"][iterator],"rate=",round(Rates["HLT_IsoMu30_eta2p1"]["rawrate"][iterator],2) 
    
        rootFileName = MakePlots(Rates, LumiPageInfo, run_list, trig_name, trig_list, num_ls, min_rate, max_dt, print_table, data_clean, plot_properties, masked_triggers, save_fits, debug_print,SubSystemOff, print_info)
    except KeyboardInterrupt:
        print "Wait... come back..."

def GetDBRates(run_list,trig_name,trig_list_noV, num_ls, max_dt, physics_active_psi,JSON,debug_print, force_new, SubSystemOff):
    
    Rates = {}
    LumiPageInfo={}
    ## Save in RefRuns with name dependent on trig_name, num_ls, JSON, and physics_active_psi
    if JSON:
        #print "Using JSON file"
        if physics_active_psi:
            RefRunNameTemplate = "RefRuns/2011/Rates_%s_%sLS_JPAP.pkl"
        else:
            RefRunNameTemplate = "RefRuns/2011/Rates_%s_%sLS_JSON.pkl"
    else:
        print "Using Physics and Active ==1"
        if physics_active_psi:
            RefRunNameTemplate = "RefRuns/2011/Rates_%s_%sLS_PAP.pkl"
        else:
            RefRunNameTemplate = "RefRuns/2011/Rates_%s_%sLS.pkl"
        
    
    RefRunFile = RefRunNameTemplate % (trig_name,num_ls)
    RefRunFileHLT = RefRunNameTemplate % ("HLT",num_ls)

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
    RefLumiNameTemplate = "RefRuns/2011/Lumis_%s_%sLS.pkl"        
    RefLumiFile= RefLumiNameTemplate % ("HLT",num_ls)
    if not force_new:
        try:
            pkl_lumi_file = open(RefLumiFile, 'rb')
            LumiPageInfo = pickle.load(pkl_lumi_file)
            pkl_lumi_file.close()
            os.remove(RefLumiFile)
            print "using",RefLumiFile
        except:
            print str(RefLumiFile)+" doesn't exist. Make it..."
            
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
                #print RefRunNum, v["Run"]

                if RefRunNum == v["Run"]:
                    LumiExistsAlready=True
                    break
            if ExistsAlready and LumiExistsAlready:
                continue
                    
           
        except:
            print "Getting info for run "+str(RefRunNum)
        
        if RefRunNum < 1:
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


                ## We have specified the trig list without version numbers, we add them specific to this run
                ##print "Processing Triggers: "
                trig_list=[]
                for entry in trig_list_noV:
                    trig_list.append(RefParser.GetTriggerVersion(entry))
                    if trig_list[-1]=="":
                        print ">> WARNING: could not find version for trigger %s, SKIPPING" % (entry,)
                    else:
                        ##print ">> %s " % (trig_list[-1],)
                        pass
                #DeadTimeBeamActive=RefParser.GetDeadTimeBeamActive()
                #print "deadtime ls run 180250=",DeadTimeBeamActive
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
                    #print nls, RefLumiArray[1][nls], RefLumiArray[2][nls]

                    [inst, live, delivered, dead, pscols] = RefParser.GetAvLumiInfo(LSRange[nls])
                    deadtimebeamactive=RefParser.GetDeadTimeBeamActive(LSRange[nls])
                    #print LSRange,deadtimebeamactive
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
                    
                    #print MoreLumiMulti.keys()
#                    print "\n\n\n"

                    

                    if inst < 0 or live < 0 or delivered < 0:
                        print "Run "+str(RefRunNum)+" LS "+str(nls)+" inst lumi = "+str(inst)+" live lumi = "+str(live)+", delivered = "+str(delivered)+", physics = "+str(physics)+", active = "+str(active)


                    
                    LumiPageInfo[nls]=MoreLumiMulti
                    ##print LumiPageInfo[nls]
##                         try:
##                             LumiPageInfo[keys].append(values)
##                         except:
##                             print "Failed",RefRunNum, nls, keys

                    for key in TriggerRates:
                        ##if not key in trig_list:
                        ##    continue
                        
                        ##if not trig_name in key:
                        ##    continue
                        name = StripVersion(key)
                       
                        ##if re.match('.*_v[0-9]+',name): ##Removes _v#
                        ##    name = name[:name.rfind('_')]
                        if not name in trig_list_noV:
                            continue
                        #print "trigger=",name, trig_list
                        
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

                            #for keys, values in MoreLumiMulti.iteritems():
                            #    Rates[name][keys] = []
                        
                            
                        [avps, ps, rate, psrate] = TriggerRates[key]
                        #print "TriggerRates=",TriggerRates[key], "key=",key
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
                        #print iterator, "LS=", nls, "dt=",round(deadtimebeamactive,2), "deliv=",delivered, "live=",live
                        
                        #for keys, values in MoreLumiMulti.iteritems():
                        #    Rates[name][keys].append(values)
                            #print nls, name, keys, values
                #print " "        
            #except: ##If we replace "if True:" with "try:"
                #print "Failed to parse run "+str(RefRunNum)

    RateOutput = open(RefRunFile, 'wb') ##Save new Rates[] to RefRuns
    pickle.dump(Rates, RateOutput, 2)
    RateOutput.close()
    LumiOutput = open(RefLumiFile,'wb')
    pickle.dump(LumiPageInfo,LumiOutput, 2)
    LumiOutput.close()
    
    
    return [Rates,LumiPageInfo]

def MakePlots(Rates, LumiPageInfo, run_list, trig_name, trig_list, num_ls, min_rate, max_dt, print_table, data_clean, plot_properties, masked_triggers, save_fits, debug_print, SubSystemOff, print_info):
    min_run = min(run_list)
    max_run = max(run_list)
    
    InputFit = {}
    OutputFit = {}
    first_trigger=True

    RootNameTemplate = "%s_%sLS_Run%sto%s.root"
    RootFile = RootNameTemplate % (trig_name, num_ls, min_run, max_run)

    [[varX, varY, do_fit, save_root, save_png, fit_file]] = plot_properties
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

    ## check that all the triggers we ask to plot are in the input fit
    if not save_fits:
        goodtrig_list = []
        for trig in trig_list:
            if not InputFit.has_key(trig):
                print "WARNING:  No Fit Prediction for Trigger %s, SKIPPING" % (trig,)
            else:
                goodtrig_list.append(trig)
        trig_list = goodtrig_list

    for print_trigger in Rates:
        ##Limits Rates[] to runs in run_list
        NewTrigger = {}
        if not print_trigger in trig_list:
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
            print str(print_trigger)+" has no good datapoints - setting initial xsec slope estimate to 0"
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
            Chi2 = InputFit[print_trigger][5]
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
                    if FitType == "expo":
                        rate_prediction = X0 + X1*math.exp(X2*delivered_t[-1])
                    else:
                        rate_prediction = X0 + X1*delivered_t[-1] + X2*delivered_t[-1]*delivered_t[-1] + X3*delivered_t[-1]*delivered_t[-1]*delivered_t[-1]
##                     if rate_t[-1] < 0.7 * rate_prediction or rate_t[-1] > 1.4 * rate_prediction:
##                         print str(run_t[-1])+"  "+str(ls_t[-1])+"  "+str(print_trigger)+"  "+str(ps_t[-1])+"  "+str(deadtime_t[-1])+"  "+str(rate_prediction)+"  "+str(rate_t[-1])+"  "+str(rawrate_t[-1])

                    if live_t[-1] == 0:
                        rawrate_fit_t.append(0)
                        rate_fit_t.append(0)
                        rawxsec_fit_t.append(0)
                        xsec_fit_t.append(0)
                        e_rawrate_fit_t.append(0)
                        e_rate_fit_t.append(math.sqrt(Chi2))
                        e_rawxsec_fit_t.append(0)
                        e_xsec_fit_t.append(0)
                        #print "live_t=0", ls_t[-1], rawrate_fit_t[-1]
                    else:
                        if ps_t[-1]>0.0:
                            rawrate_fit_t.append(rate_prediction*(1.0-deadtime_t[-1])/(ps_t[-1]))
                        else:
                            rawrate_fit_t.append(0.0)
                        
                        rate_fit_t.append(rate_prediction)
                        rawxsec_fit_t.append(rawrate_fit_t[-1]/live_t[-1])
                        xsec_fit_t.append(rate_prediction*(1.0-deadtime_t[-1])/live_t[-1])
                        e_rawrate_fit_t.append(math.sqrt(Chi2)*rawrate_fit_t[-1]/rate_fit_t[-1])
                        e_rate_fit_t.append(math.sqrt(Chi2))
                        e_rawxsec_fit_t.append(math.sqrt(Chi2)*rawxsec_fit_t[-1]/rate_fit_t[-1])
                        e_xsec_fit_t.append(math.sqrt(Chi2)*xsec_fit_t[-1]/rate_fit_t[-1])
                        #print "live_t>0", ls_t[-1], rawrate_fit_t[-1]

                ##print iterator, iterator, "ls=",ls_t[-1],"rate=",round(rawrate_t[-1],2), "deadtime=",round(deadtime_t[-1],2),"rawrate_fit=",round(rawrate_fit_t[-1],2),"max it=",len(Rates[print_trigger]["rate"])
                


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

        gr1 = TGraphErrors(len(VX), VX, VY, VXE, VYE)
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
            if "rate" in varY:
                f1a = TF1("f1a","pol2",0,8000)
                f1a.SetLineColor(4)
                f1a.SetLineWidth(2)
                f1a.SetParLimits(0,0,0.2*(sum(VY)/len(VY))+0.8*min(VY))
                f1a.SetParLimits(1,0,2.0*max(VY)/(max(VX)*max(VX)))
                #gr1.Fit("f1a","B","Q")
                gr1.Fit("f1a","Q","rob=0.90")
                
                f1b = 0
                f1c = 0
                if True:
                    f1b = TF1("f1b","pol3",0,8000)
                    f1b.SetLineColor(2)
                    f1b.SetLineWidth(2)
                    f1b.SetParLimits(0,0,0.2*(sum(VY)/len(VY))+0.8*min(VY))
                    f1b.SetParLimits(1,0,f1a.GetParameter(1)+0.0000001)
                    f1b.SetParLimits(2,0,f1a.GetParameter(2)+0.0000000001)
                    f1b.SetParLimits(3,0,2.0*max(VY)/(max(VX)*max(VX)*max(VX)))
                    gr1.Fit("f1b","Q","rob=0.90")
                    #if f1b.GetChisquare()/f1b.GetNDF() < f1a.GetChisquare()/f1a.GetNDF():
                    #print "X0 = "+str(f1a.GetParameter(0))+" X1 = "+str(f1a.GetParameter(1))+" X2 = "+str(f1a.GetParameter(2))
                    #print str(print_trigger)+" f1a Chi2 = "+str(10*f1a.GetChisquare()*math.sqrt(len(VY))/(math.sqrt(sum(VY))*num_ls*f1a.GetNDF()))+", f1b Chi2 = "+str(10*f1b.GetChisquare()*math.sqrt(len(VY))/(math.sqrt(sum(VY))*num_ls*f1b.GetNDF()))
                    #print "X0 = "+str(f1b.GetParameter(0))+" X1 = "+str(f1b.GetParameter(1))+" X2 = "+str(f1b.GetParameter(2))+" X3 = "+str(f1b.GetParameter(3))
                    if (first_trigger):
                        print "len(VX)=",len(VX), "len(VY)=",len(VY)
                        print '%-60s %4s  x0             x1                    x2                    x3                   chi2     ndf chi2/ndf' % ('trigger', 'type')
                        
                        first_trigger=False
                    
                    
                    
                    f1c = TF1("f1c","[0]+[1]*expo(2)",0,8000)
                    f1c.SetLineColor(3)
                    f1c.SetLineWidth(2)
                    f1c.SetParLimits(0,0,0.2*(sum(VY)/len(VY))+0.8*min(VY))
                    f1c.SetParLimits(1,max(VY)/math.exp(10.0),max(VY)/math.exp(2.0))
                    f1c.SetParLimits(2,0.0,0.0000000001)
                    f1c.SetParLimits(3,2.0/max(VX),10.0/max(VX))
                    #print str(max(VY)/math.exp(2.0))+"  "+str(10.0/max(VX))
                    gr1.Fit("f1c","Q","rob=0.90")
                    #if f1c.GetChisquare()/f1c.GetNDF() < f1a.GetChisquare()/f1a.GetNDF():
                    #print str(print_trigger)+" f1a Chi2 = "+str(10*f1a.GetChisquare()*math.sqrt(len(VY))/(math.sqrt(sum(VY))*num_ls*f1a.GetNDF()))+", f1c Chi2 = "+str(10*f1c.GetChisquare()*math.sqrt(len(VY))/(math.sqrt(sum(VY))*num_ls*f1c.GetNDF()))
                    #print "X0 = "+str(f1c.GetParameter(0))+" X1 = "+str(f1c.GetParameter(1))+" X2 = "+str(f1c.GetParameter(2))+" X3 = "+str(f1c.GetParameter(3))
                    
                    
                    
                    

                    if (f1c.GetChisquare()/f1c.GetNDF() < f1b.GetChisquare()/f1b.GetNDF() and f1c.GetChisquare()/f1c.GetNDF() < f1a.GetChisquare()/f1a.GetNDF()):
                        print '%-60s expo % .2f+/-%.2f   % .2e+/-%.1e   % .2e+/-%.1e   % .2e+/-%.1e   %7.2f   %4.0f   %5.3f ' % (print_trigger, f1c.GetParameter(0), f1c.GetParError(0), f1c.GetParameter(1), f1c.GetParError(1), 0                  , 0                 , 0                  , 0                 , f1c.GetChisquare(), f1c.GetNDF(), f1c.GetChisquare()/f1c.GetNDF())
                    elif (f1b.GetChisquare()/f1b.GetNDF() < f1a.GetChisquare()/f1a.GetNDF()):
                        print '%-60s cube % .2f+/-%.2f   % .2e+/-%.1e   % .2e+/-%.1e   % .2e+/-%.1e   %7.2f   %4.0f   %5.3f ' % (print_trigger, f1b.GetParameter(0), f1b.GetParError(0), f1b.GetParameter(1), f1b.GetParError(1), f1b.GetParameter(2), f1b.GetParError(2), f1b.GetParameter(3), f1b.GetParError(3), f1b.GetChisquare(), f1b.GetNDF(), f1b.GetChisquare()/f1b.GetNDF())
                    else:
                        print '%-60s quad % .2f+/-%.2f   % .2e+/-%.1e   % .2e+/-%.1e   % .2e+/-%.1e   %7.2f   %4.0f   %5.3f ' % (print_trigger, f1a.GetParameter(0), f1a.GetParError(0), f1a.GetParameter(1), f1a.GetParError(1), f1a.GetParameter(2), f1a.GetParError(2), 0                  , 0                 , f1a.GetChisquare(), f1a.GetNDF(), f1a.GetChisquare()/f1a.GetNDF())
                        

                    
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

        if save_root or save_png:
            gr1.Draw("APZ")
##                 ##Option to draw stats box
##                 p1 = TPaveStats()                                                                                                                           
##                 p1 = gr1.GetListOfFunctions().FindObject("stats")                                                                                           
##                 print p1                                                                                                                                    
##                 gr1.PaintStats(f1b).Draw("same")                                                                                                               
            if not do_fit:
                gr3.Draw("P3")
            if do_fit:
                f1a.Draw("same")
                try:
                    f1b.Draw("same")
                    f1c.Draw("same")
                except:
                    True
            c1.Update()
            if save_root:
                myfile = TFile( RootFile, 'UPDATE' )
                c1.Write()
                myfile.Close()
            if save_png:
                c1.SaveAs(str(print_trigger)+"_"+str(varY)+"_vs_"+str(varX)+".png")
                

        if print_table or save_fits:
            if not do_fit:
                print "Can't have save_fits = True and do_fit = False"
                continue
            if f1c.GetChisquare()/f1c.GetNDF() < 0.95*f1a.GetChisquare()/f1a.GetNDF() and f1c.GetChisquare()/f1c.GetNDF() < 0.95*f1b.GetChisquare()/f1b.GetNDF():
                OutputFit[print_trigger] = ["expo", f1c.GetParameter(0), f1c.GetParameter(1), f1c.GetParameter(3), 0.0, f1c.GetChisquare()/f1c.GetNDF(), meanrawrate, f1c.GetParError(0), f1c.GetParError(1), f1c.GetParError(2), f1c.GetParError(3)]
            elif f1b.GetChisquare()/f1b.GetNDF() < 0.95*f1a.GetChisquare()/f1a.GetNDF():
                OutputFit[print_trigger] = ["poly", f1b.GetParameter(0), f1b.GetParameter(1), f1b.GetParameter(2), f1b.GetParameter(3), f1b.GetChisquare()/f1b.GetNDF(), meanrawrate,f1b.GetParError(0), f1b.GetParError(1), f1b.GetParError(2), f1b.GetParError(3)]
            else:
                OutputFit[print_trigger] = ["poly", f1a.GetParameter(0), f1a.GetParameter(1), f1a.GetParameter(2), 0.0, f1a.GetChisquare()/f1a.GetNDF(), meanrawrate, f1a.GetParError(0), f1a.GetParError(1), f1a.GetParError(2), 0.0]

    if save_root:
        print "Output root file is "+str(RootFile)

    if save_fits:
        #FitNameTemplate = "Fits/2011/Fit_%s_%sLS_Run%sto%s.pkl"
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
            if not (LumiPageInfo[LS]["rpc"] or LumiPageInfo[LS]["dt0"] or LumiPageInfo[LS]["dtp"] or LumiPageInfo[LS]["dtm"] or LumiPageInfo["cscp"] or LumiPageInfo["cscm"]):
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
            
        #print "LS",LS, Passed, round(Rates[print_trigger]["deadtime"][iterator],2), max_dt
        
    if not data_clean or (
 ##        (
        
##         (
##         realvalue > 0.4*prediction
##         and realvalue < 2.5*prediction
##         )
        
##         or

##         (
##         realvalue > 0.4*meanxsec
##         and realvalue < 2.5*meanxsec
##         )

##         or prediction < 0
##         )
        
        Rates[print_trigger]["physics"][iterator] == 1
        and Rates[print_trigger]["active"][iterator] == 1
        and Rates[print_trigger]["deadtime"][iterator] < max_dt
        #and Rates[print_trigger]["psi"][iterator] > 0
        and Passed
        ):
        #print LS, "True"
        return True
    else:
        
        if (print_info and print_trigger==trig_list[0] and num_ls==1):
            
            print '%10s%10s%10s%10s%10s%10s%10s%15s%20s' % ("Failed", Rates[print_trigger]["run"][iterator], LS, Rates[print_trigger]["physics"][iterator], Rates[print_trigger]["active"][iterator], round(Rates[print_trigger]["deadtime"][iterator],2), max_dt, Passed, subsystemfailed)
        ##elif(print_info and print_trigger==trig_list[0]):
        ##    print '%10s%10s%10s%10s%10s%10s%10s%15s%20s' % ("Failed", Rates[print_trigger]["run"][iterator], LumiPageInfo[Rates[print_trigger]["ls"][iterator]]["LSRange"], Rates[print_trigger]["physics"][iterator], Rates[print_trigger]["active"][iterator], round(Rates[print_trigger]["deadtime"][iterator],2), max_dt, Passed, subsystemfailed)
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
    main()
