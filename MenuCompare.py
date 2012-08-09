#!/usr/bin/env python
import sys
import os
import subprocess
import getopt
import pickle
import re
import csv

#########################################################################################
#### This file needs: DatabaseRatePredictor_dev.py
####                  DatabaseRateMonitor.py
####                  
####  Charlie Mueller 8/8/2012
#########################################################################################
def usage():
    print "This tool compares old menu rates to new menu rates in addition to googledoc and TMD predicions"
    print "EXAMPLE: python MenuCompare.py --TriggerList=monitorlist_all_v4.list --json=Cert_190456-199429_8TeV_PromptReco_Collisions12_JSON.txt --oldMenu=199318-199429 --LS1=2 --nLS1=23 --newMenu=199751-199754 --LS2=54 --nLS2=20 --googleDoc=googledoc_7e33_v3.csv --TMDpred=TMDpred_7e33_v4.csv "
    print "the only optional argument is '--json='"

def main():
    try:
        try:
            opt,args = getopt.getopt(sys.argv[1:],"",["TriggerList=","json=","oldMenu=","LS1=","nLS1=","newMenu=","LS2=","nLS2=","scaleFac=","googleDoc=","TMDpred="])
        except getopt.GetoptError, err:
            print "Error"
            usage()
            sys.exit(2)
            
        #init inputs
        triggerlist = ""
        json = ""
        LS1 = ""
        LS2 = ""
        nLS1 = ""
        nLS2 = ""
        gDoc = ""
        TMDpred = ""
        for o,a in opt:
            if o == "--TriggerList":
                triggerlist = a
            elif o =="--json":
                json = a
            elif o =="--oldMenu":
                oldMenu = a
            elif o =="--LS1":
                LS1 = a
            elif o =="--nLS1":
                nLS1 = a
            elif o =="--newMenu":
                newMenu = a
            elif o =="--LS2":
                LS2 = a
            elif o =="--nLS2":
                nLS2 = a
            elif o =="--googleDoc":
                gDoc = a
            elif o =="--TMDpred":
                TMDpred = a
            elif o =="--scaleFac":
                scaleFac = float(a)

        if oldMenu.find('-') != -1:#oldMenu is a run range
            rrangeOld = oldMenu.split('-')
        if newMenu.find('-') != -1:#newMenu is a run range
            rrangeNew = newMenu.split('-')
            
        run1 = rrangeOld[0]
        run2 = rrangeOld[1]
        run3 = rrangeNew[0]
        run4 = rrangeNew[1]

        save_string = "MenuComparison_"+run2+"-"+run4+".csv"
        trigger_string = "--TriggerList="+triggerlist

        if json == "":
            json_string = json
        else:
            json_string = "--json="+json
        
        print " "
        cmd1 = "env DISPLAY= python DatabaseRatePredictor.py --makeFits "+trigger_string+" --NoVersion "+json_string+" --maxdt=0.10 "+oldMenu
        cmd2 = "sed -i '/TriggerToMonitorList=/ c\TriggerToMonitorList="+triggerlist+"' defaults.cfg"
        cmd3 = "sed -i '/FitFileName=/ c\FitFileName=Fits/2012/Fit_HLT_NoV_10LS_Run"+run1+"to"+run2+".pkl' defaults.cfg"
        cmd4 = "sed -i '/prettyCSVwriter(/     c\    prettyCSVwriter(\"rateMon_oldmenu.csv\",[80,10,10,10,10,20,20],Header,SortedData,Warn)' DatabaseRateMonitor.py"
        cmd5 = "python DatabaseRateMonitor.py --CompareRun="+run2+" --FirstLS="+LS1+" --NumberLS="+nLS1
        cmd6 = "env DISPLAY= python DatabaseRatePredictor.py --makeFits "+trigger_string+" --NoVersion --maxdt=0.10 "+newMenu
        cmd7 = "sed -i '/FitFileName=/ c\FitFileName=Fits/2012/Fit_HLT_NoV_10LS_Run"+run3+"to"+run4+".pkl' defaults.cfg"
        cmd8 = "sed -i '/prettyCSVwriter(/ c\    prettyCSVwriter(\"rateMon_newmenu.csv\",[80,10,10,10,10,20,20],Header,SortedData,Warn)' DatabaseRateMonitor.py"
        cmd9 = "python DatabaseRateMonitor.py --CompareRun="+run4+" --FirstLS="+LS2+" --NumberLS="+nLS2
        cmds = [cmd1,cmd2,cmd3,cmd4,cmd5,cmd6,cmd7,cmd8,cmd9]
        for cmd in cmds:
            try:
                subprocess.call(cmd, shell=True)
            except:
                print "Command Error:",cmd
                sys.exit(2)
                
        compareFiles("rateMon_newmenu.csv","rateMon_oldmenu.csv",TMDpred,gDoc,scaleFac,save_string)
        
    except KeyboardInterrupt:
        print "Exiting..."
        

def StripVersion(name):
    if re.match('.*_v[0-9]+',name):
        name = name[:name.rfind('_')]
    return name

def StripPm(name1):
    if re.match('.*[+-]',name1):
        name1 = name1[:name1.rfind('+-')]
    return name1

def compareFiles(new,old,tmd,gdoct,scaler,save_file):
    f1 = open(new,"rU")#new menu, the order is important!
    f2 = open(old,"rU")#old menu
    f3 = open(tmd,"rU")#TMD
    f4 = open(gdoct,"rU")#gDoc
    saveF = open(save_file,"wb")
    r1 = csv.reader(f1)
    r2 = csv.reader(f2)
    r3 = csv.reader(f3)
    r4 = csv.reader(f4)
    w1 = csv.writer(saveF)
  
    w1.writerow(["Trigger","Old Menu Rate (Actual)"," Old Menu Rate (Expected)","Old Menu PS","New Menu Rate (Actual)","New Menu Rate (Expected)","New Menu PS","Google Doc Rate","TMD Pred Rate","contact"])

    list2 = [iter2 for iter2 in r2]
    list3 = [iter3 for iter3 in r3]
    list4 = [iter4 for iter4 in r4]

    #row1 = newmenu
    #row2 = oldmenu
    #row3 = TMD
    #row4 = googledoc

    for row1 in r1:
        for row2 in list2:
            if StripVersion(str(row1[0])) == StripVersion(str(row2[0])):
                for row3 in list3:
                    if StripVersion(str(row3[0])) == StripVersion(str(row2[0])):
                        row_write = False
                        for row4 in list4:
                            if StripVersion(str(row4[0])) == StripVersion(str(row3[0])):
                                w1.writerow([str(row1[0]),str(float(row2[1])*scaler),str(float(row2[2])*scaler),str(row2[5]),str(float(row1[1])*scaler),str(float(row1[2])*scaler),str(row1[5]),str(row4[3]),str(row3[4]),str(row4[32])])
                                row_write = True
                                break

                        if row_write == False: #if no gDoc match
                            w1.writerow([str(row1[0]),str(float(row2[1])*scaler),str(float(row2[2])*scaler),str(row2[5]),str(float(row1[1])*scaler),str(float(row1[2])*scaler),str(row1[5]),"none",str(row3[4]),"none"])


    f1.close()
    f2.close()
    f3.close()
    f4.close()
    print "output comparison file is ",save_file
    saveF.close()    


if __name__=='__main__':
    main()
