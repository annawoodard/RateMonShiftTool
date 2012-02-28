from DatabaseParser import *
import sys
import os
from numpy import *
import pickle

from ROOT import gROOT, TCanvas, TF1, TGraph, TGraphErrors, TPaveStats, gPad, gStyle
from ROOT import TFile, TPaveText
from ROOT import gBenchmark
import array
import math

def main():

    ######## TO CREATE FITS #########
##     run_list = [179497,179547,179558,179563,179889,179959,179977,180072,180076,180093,180241,180250,180252]
##     trig_name = "HLT"
##     num_ls = 20
##     debug_print = False

##     min_rate = 1.0
##     print_table = False
##     data_clean = True
##     ##plot_properties = [varX, varY, do_fit, save_root, save_png, overlay_fit, fit_file]
##     plot_properties = [["live", "rate", True, True, False, False, ""]]
##     masked_triggers = ["AlCa_", "DST_", "HLT_L1", "HLT_L2", "HLT_Zero"]
##     save_fits = True
    

    ######## TO SEE RATE VS PREDICTION ########
    run_list = [180241]

    trig_name = "Mu"
    num_ls = 1
    debug_print = False

    min_rate = 3.0
    print_table = False
    data_clean = False
    ##plot_properties = [varX, varY, do_fit, save_root, save_png, overlay_fit, fit_file]
    plot_properties = [["ls", "rawrate", False, True, False, True,"Fits/2011/Fit_HLT_20LS_Run179497to180252.pkl"]]
    masked_triggers = ["AlCa_", "DST_", "HLT_L1", "HLT_L2", "HLT_Zero"]
    save_fits = False
    
    
    ########  END PARAMETERS ##########
    
    Rates = GetDBRates(run_list, trig_name, num_ls, debug_print)
    MakePlots(Rates, run_list, trig_name, num_ls, min_rate, print_table, data_clean, plot_properties, masked_triggers, save_fits, debug_print)
    

def GetDBRates(run_list,trig_name,num_ls, debug_print):
    
    Rates = {}
    RefRunNameTemplate = "RefRuns/2011/Rates_%s_%sLS.pkl"
    RefRunFile = RefRunNameTemplate % (trig_name,num_ls)
    try:
        pkl_file = open(RefRunFile, 'rb')
        Rates = pickle.load(pkl_file)
        pkl_file.close()
        os.remove(RefRunFile)
    except:
        print str(RefRunFile)+" does not exist. Creating ..."

    for RefRunNum in run_list: #Will change to a "count back runs" scheme, or something like that

        try:
            ExistsAlready = False
            for key in Rates:
                if RefRunNum in Rates[key]["run"]:
                    ExistsAlready = True
                    break
            if ExistsAlready:
                continue
        except:
            print "Getting info for run "+str(RefRunNum)
        
        if RefRunNum < 1:
            continue

        if True:
            if True: #May replace with "try" - for now it's good to know when problems happen
                RefParser = DatabaseParser()
                RefParser.RunNumber = RefRunNum
                RefParser.ParseRunSetup()
                RefLumiRangePhysicsActive = RefParser.GetLSRange(1,9999)
                RefLumiArray = RefParser.GetLumiInfo()
                RefLumiRange = []
                for iterator in RefLumiArray[0]:
                    RefLumiRange.append(iterator)

                nls = RefLumiRange[0]
                LSRange = {}
                if nls >= RefLumiRange[-1]-num_ls:
                    print "Run "+str(RefRunNum)+" is too short: from "+str(nls)+" to "+str(RefLumiRange[-1])+", while num_ls = "+str(num_ls)
                    continue
                while nls < RefLumiRange[-1]-num_ls:
                    if num_ls > 1:
                        #LSRange[nls] = RefParser.GetLSRange(nls,num_ls)
                        LSRange[nls] = []
                        for iterator in RefLumiRange:
                            if iterator >= nls and iterator < nls+num_ls:
                                LSRange[nls].append(iterator)
                    else:
                        LSRange[nls] = [nls]
                    nls = LSRange[nls][-1]+1
                print "Run "+str(RefRunNum)+" contains LS from "+str(min(LSRange))+" to "+str(max(LSRange))
                for nls in LSRange:
                    TriggerRates = RefParser.GetHLTRates(LSRange[nls])
                
                    [inst, live, delivered, dead, pscols] = RefParser.GetAvLumiInfo(LSRange[nls])
                    physics = 1
                    active = 1
                    for iterator in LSRange[nls]:
                        if RefLumiArray[5][iterator] == 0:
                            physics = 0
                        if RefLumiArray[6][iterator] == 0:
                            active = 0

                    if live < 0:
                        print "Run "+str(RefRunNum)+" LS "+str(nls)+" live lumi = "+str(live)+", delivered = "+str(delivered)+", physics = "+str(physics)+", active = "+str(active)

                    for key in TriggerRates:
                        if not trig_name in key:
                            continue
                        name = key
                        if re.match('.*_v[0-9]+',name):
                            name = name[:name.rfind('_')]

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
                        [avps, ps, rate, psrate] = TriggerRates[key]
                        Rates[name]["run"].append(RefRunNum)
                        Rates[name]["ls"].append(nls)
                        Rates[name]["ps"].append(ps)
                        Rates[name]["inst_lumi"].append(inst)
                        Rates[name]["live_lumi"].append(live)
                        Rates[name]["delivered_lumi"].append(delivered)
                        Rates[name]["deadtime"].append(dead)
                        Rates[name]["rawrate"].append(rate)
                        Rates[name]["rate"].append(psrate/(1.0-dead))
                        if live == 0:
                            Rates[name]["rawxsec"].append(0.0)
                            Rates[name]["xsec"].append(0.0)
                        else:
                            Rates[name]["rawxsec"].append(rate/live)
                            Rates[name]["xsec"].append(psrate/live)
                        Rates[name]["physics"].append(physics)
                        Rates[name]["active"].append(active)
            #except:
                #print "Failed to parse run "+str(RefRunNum)

    RateOutput = open(RefRunFile, 'wb')
    pickle.dump(Rates, RateOutput, 2)
    RateOutput.close()
    #print Rates
    return Rates

def MakePlots(Rates, run_list, trig_name, num_ls, min_rate, print_table, data_clean, plot_properties, masked_triggers, save_fits, debug_print):
    min_run = min(run_list)
    max_run = max(run_list)

    Input = {}
    Output = {}

    RootNameTemplate = "%s_%sLS_Run%sto%s.root"
    RootFile = RootNameTemplate % (trig_name, num_ls, min_run, max_run)

    for varX, varY, do_fit, save_root, save_png, overlay_fit, fit_file in plot_properties:
        if overlay_fit:
            pkl_file = open(fit_file, 'rb')
            Input = pickle.load(pkl_file)
            pkl_file.close()
        if save_root:
            try:
                os.remove(RootFile)
            except:
                break

    for print_trigger in Rates:
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
                
        Output[print_trigger] = {}

        lowlumi = 0
        numzeroes = 0
        for live_lumi in Rates[print_trigger]["live_lumi"]:
            if live_lumi < 1:
                numzeroes+=1
        meanlumi_init = sum(Rates[print_trigger]["live_lumi"])/(len(Rates[print_trigger]["live_lumi"])-numzeroes)
        meanlumi = 0
        highlumi = 0
        lowxsec = 0
        meanxsec = 0
        highxsec = 0
        nlow = 0
        nhigh = 0
        for iterator in range(len(Rates[print_trigger]["rate"])):
            if not Rates[print_trigger]["run"][iterator] in run_list:
                continue
            if Rates[print_trigger]["live_lumi"][iterator] <= meanlumi_init:
                if not data_clean or ( Rates[print_trigger]["rawrate"][iterator] > 0.04 and Rates[print_trigger]["physics"][iterator] == 1 and Rates[print_trigger]["active"][iterator] == 1):
                    meanxsec+=Rates[print_trigger]["xsec"][iterator]
                    lowxsec+=Rates[print_trigger]["xsec"][iterator]
                    meanlumi+=Rates[print_trigger]["live_lumi"][iterator]
                    lowlumi+=Rates[print_trigger]["live_lumi"][iterator]
                    nlow+=1
            if Rates[print_trigger]["live_lumi"][iterator] > meanlumi_init:
                if not data_clean or ( Rates[print_trigger]["rawrate"][iterator] > 0.04 and Rates[print_trigger]["physics"][iterator] == 1 and Rates[print_trigger]["active"][iterator] == 1):
                    meanxsec+=Rates[print_trigger]["xsec"][iterator]
                    highxsec+=Rates[print_trigger]["xsec"][iterator]
                    meanlumi+=Rates[print_trigger]["live_lumi"][iterator]
                    highlumi+=Rates[print_trigger]["live_lumi"][iterator]
                    nhigh+=1
        meanxsec = meanxsec/(nlow+nhigh)
        meanlumi = meanlumi/(nlow+nhigh)
        slopexsec = ( (highxsec/nhigh) - (lowxsec/nlow) ) / ( (highlumi/nhigh) - (lowlumi/nlow) )

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

        rawrate_fit_t = array.array('f')
        rate_fit_t = array.array('f')
        rawxsec_fit_t = array.array('f')
        xsec_fit_t = array.array('f')
        e_rawrate_fit_t = array.array('f')
        e_rate_fit_t = array.array('f')
        e_rawxsec_fit_t = array.array('f')
        e_xsec_fit_t = array.array('f')

        if overlay_fit:
            X0 = Input[print_trigger][0]
            X1 = Input[print_trigger][1]
            X2 = Input[print_trigger][2]
            Chi2 = Input[print_trigger][3]
            
        for iterator in range(len(Rates[print_trigger]["rate"])):
            if not Rates[print_trigger]["run"][iterator] in run_list:
                continue
            prediction = meanxsec + slopexsec * (Rates[print_trigger]["live_lumi"][iterator] - meanlumi)
            realvalue = Rates[print_trigger]["xsec"][iterator]
            if not data_clean or ( ((realvalue > 0.4*prediction and realvalue < 2.5*prediction) or (realvalue > 0.4*meanxsec and realvalue < 2.5*meanxsec) or prediction < 0 ) and Rates[print_trigger]["physics"][iterator] == 1 and Rates[print_trigger]["active"][iterator] == 1 ):
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

                e_run_t.append(0.0)
                e_ls_t.append(0.0)
                e_ps_t.append(0.0)
                e_inst_t.append(14.14)
                e_live_t.append(14.14)
                e_delivered_t.append(14.14)
                e_deadtime_t.append(0.01)
                e_rawrate_t.append(math.sqrt(Rates[print_trigger]["rawrate"][iterator]/(num_ls*23.3)))
                e_rate_t.append(Rates[print_trigger]["ps"][iterator]*math.sqrt(Rates[print_trigger]["rawrate"][iterator]/(num_ls*23.3)))
                if live_t[-1] == 0:
                    e_rawxsec_t.append(0)
                    e_xsec_t.append(0)
                else:
                    e_rawxsec_t.append(math.sqrt(Rates[print_trigger]["rawrate"][iterator]/(num_ls*23.3))/Rates[print_trigger]["live_lumi"][iterator])
                    e_xsec_t.append(Rates[print_trigger]["ps"][iterator]*math.sqrt(Rates[print_trigger]["rawrate"][iterator]/(num_ls*23.3))/Rates[print_trigger]["live_lumi"][iterator])

                if overlay_fit:
                    rate_prediction = X0 + X1*delivered_t[-1] + X2*delivered_t[-1]*delivered_t[-1]
                    if rate_t[-1] < 0.7 * rate_prediction or rate_t[-1] > 1.4 * rate_prediction:
                        print str(run_t[-1])+"  "+str(ls_t[-1])+"  "+str(print_trigger)+"  "+str(ps_t[-1])+"  "+str(deadtime_t[-1])+"  "+str(rate_prediction)+"  "+str(rate_t[-1])+"  "+str(rawrate_t[-1])
                    rawrate_fit_t.append(rate_prediction*(1.0-deadtime_t[-1])/(ps_t[-1]))
                    rate_fit_t.append(rate_prediction)
                    if live_t[-1] == 0:
                        rawxsec_fit_t.append(0)
                        xsec_fit_t.append(0)
                    else:
                        rawxsec_fit_t.append(rate_prediction/(ps_t[-1]*live_t[-1]))
                        xsec_fit_t.append(rate_prediction/live_t[-1])
                    e_rawrate_fit_t.append(e_rawrate_t[-1]*sqrt(Chi2))
                    e_rate_fit_t.append(e_rate_t[-1]*sqrt(Chi2))
                    e_rawxsec_fit_t.append(e_rawxsec_t[-1]*sqrt(Chi2))
                    e_xsec_fit_t.append(e_xsec_t[-1]*sqrt(Chi2))
 
            else:
                if debug_print:
                    print str(print_trigger)+" has xsec "+str(round(Rates[print_trigger]["xsec"][iterator],6))+" at lumi "+str(round(Rates[print_trigger]["live_lumi"][iterator],2))+" where the expected value is "+str(prediction)

        for varX, varY, do_fit, save_root, save_png, overlay_fit, fit_file in plot_properties:
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
                print deadtime_t
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
                if overlay_fit:
                    VF = rawrate_fit_t
                    VFE = e_rawrate_fit_t
            elif varY == "rate":
                VY = rate_t
                VYE = e_rate_t
                if overlay_fit:
                    VF = rate_fit_t
                    VFE = e_rate_fit_t
            elif varY == "rawxsec":
                VY = rawxsec_t
                VYE = e_rawxsec_t
                if overlay_fit:
                    VF = rawxsec_fit_t
                    VFE = e_rawxsec_fit_t
            elif varY == "xsec":
                VY = xsec_t
                VYE = e_xsec_t
                if overlay_fit:
                    VF = xsec_fit_t
                    VFE = e_xsec_fit_t
            else:
                print "No valid variable entered for Y"
                continue


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
            gr1.GetXaxis().SetLimits(min(VX)-0.2*max(VX),1.2*max(VX))
            gr1.SetMarkerStyle(8)
            if overlay_fit:
                gr1.SetMarkerSize(0.8)
            else:
                gr1.SetMarkerSize(0.5)
            gr1.SetMarkerColor(2)

##             gr2 = TGraphErrors(len(VX), live_t, xsec_t, e_live_t, e_xsec_t)

            if overlay_fit:
                gr3 = TGraphErrors(len(VX), VX, VF, VXE, VFE)
                gr3.SetMarkerStyle(8)
                gr3.SetMarkerSize(0.4)
                gr3.SetMarkerColor(4)
                gr3.SetFillColor(4)
                gr3.SetFillStyle(3003)
            
            if do_fit:
                if "rate" in varY:
##                     f2a = TF1("f2a","pol1",0,8000)
##                     f2a.SetParLimits(0,0,meanxsec*1.5)
##                     if slopexsec > 0:
##                         f2a.SetParLimits(1,0,max(xsec_t)/max(live_t))
##                     else:
##                         f2a.SetParLimits(1,2*slopexsec,-2*slopexsec)
##                     gr2.Fit("f2a","Q","rob=0.80")
                    
                    f1a = TF1("f1a","pol2",0,8000)
                    f1a.SetLineColor(4)
                    f1a.SetLineWidth(2)
                    f1a.SetParLimits(0,0,1000)
                    f1a.SetParLimits(1,0,1000)
                    #gr1.Fit("f1a","B","Q")
                    gr1.Fit("f1a","Q","rob=0.80")

                    if f1a.GetChisquare()/f1a.GetNDF() > 20:
                        f1b = TF1("f1b","pol3",0,8000)
                        f1b.SetLineColor(4)
                        f1b.SetLineWidth(2)
                        f1b.SetParLimits(0,0,1000)
                        f1b.SetParLimits(1,0,1000)
                        f1b.SetParLimits(2,0,1000)
                        gr1.Fit("f1b","Q","rob=0.80")
                        if f1b.GetChisquare()/f1b.GetNDF() < f1a.GetChisquare()/f1a.GetNDF():
                            print str(print_trigger)+" f1a Chi2 = "+str(f1a.GetChisquare()/f1a.GetNDF())+", f1b Chi2 = "+str(f1b.GetChisquare()/f1b.GetNDF())
                        

##                     f1b = TF1("f1b","pol2",0,8000)
##                     f1b.SetParameters(0.0,f2a.GetParameter(0),f2a.GetParameter(1))
##                     f1b.SetLineColor(3)
##                     f1b.SetLineWidth(2)
                    
                else:
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
                        f1a.SetParLimits(0,0,1000)
                    gr1.Fit("f1a","Q","rob=0.80")

            if save_root or save_png:
                gr1.Draw("APZ")
                if overlay_fit:
                    gr3.Draw("P3")
                if do_fit:
                    #if f1b and f1b.GetChisquare()/f1b.GetNDF() < f1a.GetChisquare()/f1a.GetNDF():
                        #f1b.Draw("same")
                    #else:
                    f1a.Draw("same")
##                     if "rate" in varY:
##                         f1b.Draw("same")
                c1.Update()
                if save_root:
                    myfile = TFile( RootFile, 'UPDATE' )
                    c1.Write()
                    myfile.Close()
                if save_png:
                    c1.SaveAs(str(print_trigger)+"_"+str(varY)+"_vs_"+str(varX)+".png")
                
        
        ##p1 = TPaveStats()                                                                                                                              
        ##p1 = gr1.GetListOfFunctions().FindObject("stats")                                                                                              
        ##print p1                                                                                                                                       
        ##gr1.PaintStats(f1b).Draw("same")                                                                                                               

        if print_table or save_fits:
            Output[print_trigger] = [f1a.GetParameter(0), f1a.GetParameter(1), f1a.GetParameter(2), f1a.GetChisquare()/f1a.GetNDF(), f1a.GetParameter(0)+5000*(f1a.GetParameter(1)+f1a.GetParameter(2)*5000), meanrawrate]

    if save_root:
        print "Output root file is "+str(RootFile)

    if save_fits:
        FitNameTemplate = "Fits/2011/Fit_%s_%sLS_Run%sto%s.pkl"
        FitFile = FitNameTemplate % (trig_name, num_ls, min_run, max_run)
        if os.path.exists(FitFile):
            os.remove(FitFile)
        FitOutput = open(FitFile, 'wb')
        pickle.dump(Output, FitOutput, 2)
        FitOutput.close()

    if print_table:
        print '%60s%10s%10s%10s%10s%10s%10s' % ("Trig", "p0", "p1", "p2", "Chi2", "5e33 pred", "Av raw")
        for print_trigger in Output:
            _trigger = (print_trigger[:56] + '...') if len(print_trigger) > 59 else print_trigger
            try:
                print '%60s%10s%10s%10s%10s%10s%10s' % (_trigger, round(Output[print_trigger][0],3), round(Output[print_trigger][1],6)*1000, round(Output[print_trigger][2],9)*1000000, round(Output[print_trigger][3],2), round(Output[print_trigger][4],2) , round(Output[print_trigger][5],3))
            except:
                print str(print_trigger)+" is somehow broken"

if __name__=='__main__':
    main()
