import cx_Oracle
import cPickle as pickle
import os, sys
import time

class DatabaseParser:
    
    def __init__(self):
        cmd='cat ~centraltspro/secure/cms_trg_r.txt'
        line=os.popen(cmd).readlines()
        magic = line[0].rstrip("\n\r")
        connect= 'cms_trg_r/' + magic + '@cms_omds_lb'
        # connect to the DB
        self.orcl = cx_Oracle.connect(connect)
        self.curs = self.orcl.cursor()

        ##-- Defined in ParsePage1 --##
        self.RunNumber = 0

        ##-- Defined in ParseRunPage --##
        self.Date=''
        self.L1_HLT_Key=''
        self.HLT_Key=''
        self.GTRS_Key=''
        self.TSC_Key=''
        self.GT_Key=''
        self.ConfigId=0

        ##-- Defined in ParseHLTSummaryPage --##
        self.TriggerRates = [] ## contains the HLT rates for the current LS range
        self.RateTable = []   ## Rates per LS, useful but maybe enormous!

        self.L1PrescaleTable=[]
        self.AvgL1Prescales=[] ## contains the average L1 prescales for the current LS range range
        self.HLTList=[]
        self.AvgTotalPrescales=[]
        self.HLTPrescaleTable=[] ## can't fill this yet
        self.UnprescaledRates=[]
        self.PrescaledRates=[]
        ##-- Defined in ParseLumiPage --##
        self.LastLSParsed=-1
        self.LSByLS = []
        self.InstLumiByLS = []
        self.DeliveredLumiByLS = []
        self.LiveLumiByLS = []
        self.PSColumnByLS = []
        self.AvInstLumi = 0
        self.AvDeliveredLumi = 0
        self.AvLiveLumi = 0
        self.LumiInfo = []  ##Returns
        self.DeadTime = []
        self.Physics = []


        ##-- Defined in ParseL1Page (not currently used) --##
        self.L1Rates={}  ##Returns

        ##-- Defined in ParsePSColumnPage (not currently used) --##
        self.PSColumnChanges=[]  ##Returns

        ##-- Defined in ParseTriggerModePage --##
        self.L1TriggerMode={}
        self.HLTTriggerMode={}
        self.HLTSeed=[]
        self.HLTSequenceMap=[]
        self.TriggerInfo = []  ##Returns

        ##-- Defined in AssemblePrescaleValues --##
        self.L1Prescale=[]
        self.L1IndexNameMap=[]
        self.HLTPrescale=[]
        self.MissingPrescale=[]
        self.PrescaleValues=[]  ##Returns

        ##-- Defined in ComputeTotalPrescales --##
        self.TotalPSInfo = []  ##Returns

        ##-- Defined in CorrectForPrescaleChange --##
        self.CorrectedPSInfo = []  ##Returns

        ##-- In the current Parser.py philosophy, only RunNumber is set globally
        ##    - LS range is set from the outside for each individual function
        #self.FirstLS = -1
        #self.LastLS = -1

    def GetRunInfo(self):
        ## This query gets the L1_HLT Key (A), the associated HLT Key (B) and the Config number for that key (C)
        KeyQuery = """
        SELECT A.TRIGGERMODE, B.HLT_KEY, B.GT_RS_KEY, B.TSC_KEY, C.CONFIGID, D.GT_KEY FROM
        CMS_WBM.RUNSUMMARY A, CMS_L1_HLT.L1_HLT_CONF B, CMS_HLT.CONFIGURATIONS C, CMS_TRG_L1_CONF.TRIGGERSUP_CONF D WHERE
        B.ID = A.TRIGGERMODE AND C.CONFIGDESCRIPTOR = B.HLT_KEY AND D.TS_Key = B.TSC_Key AND A.RUNNUMBER=%d
        """ % (self.RunNumber,)
        self.curs.execute(KeyQuery)
        self.L1_HLT_Key,self.HLT_Key,self.GTRS_Key,self.TSC_Key,self.ConfigId,self.GT_Key = self.curs.fetchone()        
        
    def UpdateRateTable(self):  # lets not rebuild the rate table every time, rather just append new LSs
        pass

    def GetHLTRates(self,StartLS,EndLS):
        sqlquery = """SELECT SUM(A.L1PASS),SUM(A.PSPASS),SUM(A.PACCEPT)
        ,SUM(A.PEXCEPT),(SELECT L.NAME FROM CMS_HLT.PATHS L WHERE L.PATHID=A.PATHID) PATHNAME 
        FROM CMS_RUNINFO.HLT_SUPERVISOR_TRIGGERPATHS A WHERE RUNNUMBER=%s AND A.LSNUMBER>=%d AND A.LSNUMBER<%d
        GROUP BY A.LSNUMBER,A.PATHID"""

        query = sqlquery % (self.RunNumber,StartLS,EndLS)
        self.curs.execute(query)
        self.TriggerRates=['']*len(self.HLTList)
        for L1Pass,PSPass,HLTPass,HLTExcept,name in self.curs.fetchall():
            rate = HLTPass/23.3
            ps = 0
            if PSPass:
                ps = float(L1Pass)/PSPass
            if not [name] in self.RateTable:
                continue
            nameI = self.GetHLTIndex(name) #self.RateTable.index([name])
            if nameI==-1:
                continue
            self.RateTable[nameI].append([ps,rate])
            self.TriggerRates[nameI]= [rate,L1Pass,PSPass,ps,StartLS,EndLS]
        ##self.RateTable
        return self.TriggerRates

	
    def GetLumiInfo(self): 
        sqlquery="""SELECT RUNNUMBER,LUMISECTION,PRESCALE_INDEX,INSTLUMI,LIVELUMI,DELIVLUMISECTION,DEADTIME
        ,DCSSTATUS,PHYSICS_FLAG
        FROM CMS_RUNTIME_LOGGER.LUMI_SECTIONS A,CMS_GT_MON.LUMI_SECTIONS B WHERE A.RUNNUMBER=%s
        AND B.RUN_NUMBER(+)=A.RUNNUMBER AND B.LUMI_SECTION(+)=A.LUMISECTION AND A.LUMISECTION > %d
        ORDER BY A.RUNNUMBER,A.LUMISECTION"""
        
        ## Get the lumi information for the run, just update the table, don't rebuild it every time
        query = sqlquery % (self.RunNumber,self.LastLSParsed)
        self.curs.execute(query)
        pastLSCol=-1
        for run,ls,psi,inst,live,dlive,dt,dcs,phys in self.curs.fetchall():
            self.LSByLS.append(ls)
            self.PSColumnByLS.append(psi)
            self.InstLumiByLS.append(inst)
            self.LiveLumiByLS.append(inst)
            self.DeliveredLumiByLS.append(inst)
            self.DeadTime.append(dt)
            self.Physics.append(phys)
            if pastLSCol!=-1 and ls!=pastLSCol:
                self.PSColumnChanges.append([ls,psi])
            pastLSCol=ls
            if ls>self.LastLSParsed:
                self.LastLSParsed=ls

    def FillLumiInfo(self,StartLS,EndLS):
        if EndLS <= StartLS:
            print "In ParseLumiPage, EndLS <= StartLS"

        print "In ParseLumiPage, StartLS = "+str(StartLS)+" and EndLS = "+str(EndLS)

        self.AvLiveLumi = 1000*(self.LiveLumiByLS[EndLS] - self.LiveLumiByLS[StartLS])/(23.3*(EndLS-StartLS))
        self.AvDeliveredLumi = 1000*(self.DeliveredLumiByLS[EndLS] - self.DeliveredLumiByLS[StartLS])/(23.3*(EndLS-StartLS))
        value_iterator = 0
        for value in self.LSByLS:
            if value >= StartLS and value <= EndLS:
                self.AvInstLumi+=self.InstLumiByLS[value]
                value_iterator+=1
        self.AvInstLumi = self.AvInstLumi / value_iterator

        self.LumiInfo = [self.LSByLS, self.PSColumnByLS, self.InstLumiByLS, self.DeliveredLumiByLS, self.LiveLumiByLS, self.AvInstLumi, self.AvDeliveredLumi, self.AvLiveLumi]

        return [self.LumiInfo,StartLS,EndLS]
    

    def ParsePSColumnPage(self): ## this is now done automatically when we read the db
        pass

    def GetL1NameIndexAssoc(self):
        ## get the L1 algo names associated with each algo bit
        AlgoNameQuery = """SELECT ALGO_INDEX, ALIAS FROM CMS_GT.L1T_MENU_ALGO_VIEW
        WHERE MENU_IMPLEMENTATION IN (SELECT L1T_MENU_FK FROM CMS_GT.GT_SETUP WHERE ID='%s')
        ORDER BY ALGO_INDEX""" % (self.GT_Key,)
        self.curs.execute(AlgoNameQuery)
        nextIndex=0
        for index,name in self.curs.fetchall():
            while nextIndex<index:
                self.L1IndexNameMap.append('')
                nextIndex+=1 ## skips empty seeds
            self.L1IndexNameMap.append(name)
            nextIndex+=1
            
    def GetL1AlgoPrescales(self):
        L1PrescalesQuery= """
        SELECT
        PRESCALE_FACTOR_ALGO_000,PRESCALE_FACTOR_ALGO_001,PRESCALE_FACTOR_ALGO_002,PRESCALE_FACTOR_ALGO_003,PRESCALE_FACTOR_ALGO_004,PRESCALE_FACTOR_ALGO_005,
        PRESCALE_FACTOR_ALGO_006,PRESCALE_FACTOR_ALGO_007,PRESCALE_FACTOR_ALGO_008,PRESCALE_FACTOR_ALGO_009,PRESCALE_FACTOR_ALGO_010,PRESCALE_FACTOR_ALGO_011,
        PRESCALE_FACTOR_ALGO_012,PRESCALE_FACTOR_ALGO_013,PRESCALE_FACTOR_ALGO_014,PRESCALE_FACTOR_ALGO_015,PRESCALE_FACTOR_ALGO_016,PRESCALE_FACTOR_ALGO_017,
        PRESCALE_FACTOR_ALGO_018,PRESCALE_FACTOR_ALGO_019,PRESCALE_FACTOR_ALGO_020,PRESCALE_FACTOR_ALGO_021,PRESCALE_FACTOR_ALGO_022,PRESCALE_FACTOR_ALGO_023,
        PRESCALE_FACTOR_ALGO_024,PRESCALE_FACTOR_ALGO_025,PRESCALE_FACTOR_ALGO_026,PRESCALE_FACTOR_ALGO_027,PRESCALE_FACTOR_ALGO_028,PRESCALE_FACTOR_ALGO_029,
        PRESCALE_FACTOR_ALGO_030,PRESCALE_FACTOR_ALGO_031,PRESCALE_FACTOR_ALGO_032,PRESCALE_FACTOR_ALGO_033,PRESCALE_FACTOR_ALGO_034,PRESCALE_FACTOR_ALGO_035,
        PRESCALE_FACTOR_ALGO_036,PRESCALE_FACTOR_ALGO_037,PRESCALE_FACTOR_ALGO_038,PRESCALE_FACTOR_ALGO_039,PRESCALE_FACTOR_ALGO_040,PRESCALE_FACTOR_ALGO_041,
        PRESCALE_FACTOR_ALGO_042,PRESCALE_FACTOR_ALGO_043,PRESCALE_FACTOR_ALGO_044,PRESCALE_FACTOR_ALGO_045,PRESCALE_FACTOR_ALGO_046,PRESCALE_FACTOR_ALGO_047,
        PRESCALE_FACTOR_ALGO_048,PRESCALE_FACTOR_ALGO_049,PRESCALE_FACTOR_ALGO_050,PRESCALE_FACTOR_ALGO_051,PRESCALE_FACTOR_ALGO_052,PRESCALE_FACTOR_ALGO_053,
        PRESCALE_FACTOR_ALGO_054,PRESCALE_FACTOR_ALGO_055,PRESCALE_FACTOR_ALGO_056,PRESCALE_FACTOR_ALGO_057,PRESCALE_FACTOR_ALGO_058,PRESCALE_FACTOR_ALGO_059,
        PRESCALE_FACTOR_ALGO_060,PRESCALE_FACTOR_ALGO_061,PRESCALE_FACTOR_ALGO_062,PRESCALE_FACTOR_ALGO_063,PRESCALE_FACTOR_ALGO_064,PRESCALE_FACTOR_ALGO_065,
        PRESCALE_FACTOR_ALGO_066,PRESCALE_FACTOR_ALGO_067,PRESCALE_FACTOR_ALGO_068,PRESCALE_FACTOR_ALGO_069,PRESCALE_FACTOR_ALGO_070,PRESCALE_FACTOR_ALGO_071,
        PRESCALE_FACTOR_ALGO_072,PRESCALE_FACTOR_ALGO_073,PRESCALE_FACTOR_ALGO_074,PRESCALE_FACTOR_ALGO_075,PRESCALE_FACTOR_ALGO_076,PRESCALE_FACTOR_ALGO_077,
        PRESCALE_FACTOR_ALGO_078,PRESCALE_FACTOR_ALGO_079,PRESCALE_FACTOR_ALGO_080,PRESCALE_FACTOR_ALGO_081,PRESCALE_FACTOR_ALGO_082,PRESCALE_FACTOR_ALGO_083,
        PRESCALE_FACTOR_ALGO_084,PRESCALE_FACTOR_ALGO_085,PRESCALE_FACTOR_ALGO_086,PRESCALE_FACTOR_ALGO_087,PRESCALE_FACTOR_ALGO_088,PRESCALE_FACTOR_ALGO_089,
        PRESCALE_FACTOR_ALGO_090,PRESCALE_FACTOR_ALGO_091,PRESCALE_FACTOR_ALGO_092,PRESCALE_FACTOR_ALGO_093,PRESCALE_FACTOR_ALGO_094,PRESCALE_FACTOR_ALGO_095,
        PRESCALE_FACTOR_ALGO_096,PRESCALE_FACTOR_ALGO_097,PRESCALE_FACTOR_ALGO_098,PRESCALE_FACTOR_ALGO_099,PRESCALE_FACTOR_ALGO_100,PRESCALE_FACTOR_ALGO_101,
        PRESCALE_FACTOR_ALGO_102,PRESCALE_FACTOR_ALGO_103,PRESCALE_FACTOR_ALGO_104,PRESCALE_FACTOR_ALGO_105,PRESCALE_FACTOR_ALGO_106,PRESCALE_FACTOR_ALGO_107,
        PRESCALE_FACTOR_ALGO_108,PRESCALE_FACTOR_ALGO_109,PRESCALE_FACTOR_ALGO_110,PRESCALE_FACTOR_ALGO_111,PRESCALE_FACTOR_ALGO_112,PRESCALE_FACTOR_ALGO_113,
        PRESCALE_FACTOR_ALGO_114,PRESCALE_FACTOR_ALGO_115,PRESCALE_FACTOR_ALGO_116,PRESCALE_FACTOR_ALGO_117,PRESCALE_FACTOR_ALGO_118,PRESCALE_FACTOR_ALGO_119,
        PRESCALE_FACTOR_ALGO_120,PRESCALE_FACTOR_ALGO_121,PRESCALE_FACTOR_ALGO_122,PRESCALE_FACTOR_ALGO_123,PRESCALE_FACTOR_ALGO_124,PRESCALE_FACTOR_ALGO_125,
        PRESCALE_FACTOR_ALGO_126,PRESCALE_FACTOR_ALGO_127
        FROM CMS_GT.GT_FDL_PRESCALE_FACTORS_ALGO A, CMS_GT.GT_RUN_SETTINGS_PRESC_VIEW B
        WHERE A.ID=B.PRESCALE_FACTORS_ALGO_FK AND B.ID='%s'
        """ % (self.GTRS_Key,)
        self.curs.execute(L1PrescalesQuery)
        ## This is pretty horrible, but this how you get them!!
        tmp = self.curs.fetchall()
        for ps in tmp[0]: #build the prescale table initially
            self.L1PrescaleTable.append([ps])
        for line in tmp[1:]: # now fill it
            for ps,index in zip(line,range(len(line))):
                self.L1PrescaleTable[index].append(ps)

    def GetHLTIndex(self,name):
        for i,n in enumerate(self.HLTList):
            if n.find(name)!=-1:
                return i
        print name
        return -1

    def GetL1Index(self,name):
        for i,n in enumerate(self.L1IndexNameMap):
            if n==name:
                return i
        print name
        return -1
    
    def GetHLTPrescaleMatrix(self,cursor):
        ##NOT WORKING 1/19/2012
        return
        SequencePathQuery ="""
        SELECT F.SEQUENCENB,J.VALUE TRIGGERNAME
        FROM CMS_HLT.CONFIGURATIONSERVICEASSOC A
        , CMS_HLT.SERVICES B
        , CMS_HLT.SERVICETEMPLATES C
        , CMS_HLT.SUPERIDVECPARAMSETASSOC D
        , CMS_HLT.VECPARAMETERSETS E
        , CMS_HLT.SUPERIDPARAMSETASSOC F
        , CMS_HLT.PARAMETERSETS G
        , CMS_HLT.SUPERIDPARAMETERASSOC H
        , CMS_HLT.PARAMETERS I
        , CMS_HLT.STRINGPARAMVALUES J
        WHERE A.CONFIGID= %d
        AND A.SERVICEID=B.SUPERID
        AND B.TEMPLATEID=C.SUPERID
        AND C.NAME='PrescaleService'
        AND B.SUPERID=D.SUPERID
        AND D.VPSETID=E.SUPERID
        AND E.NAME='prescaleTable'
        AND D.VPSETID=F.SUPERID
        AND F.PSETID=G.SUPERID
        AND G.SUPERID=H.SUPERID
        AND I.PARAMID=H.PARAMID
        AND I.NAME='pathName'
        AND J.PARAMID=H.PARAMID
        ORDER BY F.SEQUENCENB
        """ % (self.ConfigId,)

        cursor.execute(SequencePathQuery)
        self.HLTSequenceMap = [0]*len(self.HLTList)
        for seq,name in cursor.fetchall():
            name = name.lstrip('"').rstrip('"')
            try:
                self.HLTSequenceMap[self.GetHLTIndex(name)]=seq
            except:
                print "couldn't find "+name

        for i,seq in enumerate(self.HLTSequenceMap):
            if seq==0:
                print self.HLTList[i]
            
        SequencePrescaleQuery="""
        SELECT F.SEQUENCENB,J.SEQUENCENB,J.VALUE
        FROM CMS_HLT.CONFIGURATIONSERVICEASSOC A
        , CMS_HLT.SERVICES B
        , CMS_HLT.SERVICETEMPLATES C
        , CMS_HLT.SUPERIDVECPARAMSETASSOC D
        , CMS_HLT.VECPARAMETERSETS E
        , CMS_HLT.SUPERIDPARAMSETASSOC F
        , CMS_HLT.PARAMETERSETS G
        , CMS_HLT.SUPERIDPARAMETERASSOC H
        , CMS_HLT.PARAMETERS I
        , CMS_HLT.VUINT32PARAMVALUES J
        WHERE A.CONFIGID=%d 
        AND A.SERVICEID=B.SUPERID
        AND B.TEMPLATEID=C.SUPERID
        AND C.NAME='PrescaleService'
        AND B.SUPERID=D.SUPERID
        AND D.VPSETID=E.SUPERID
        AND E.NAME='prescaleTable'
        AND D.VPSETID=F.SUPERID
        AND F.PSETID=G.SUPERID
        AND G.SUPERID=H.SUPERID
        AND I.PARAMID=H.PARAMID
        AND I.NAME='prescales'
        AND J.PARAMID=H.PARAMID
        ORDER BY F.SEQUENCENB,J.SEQUENCENB
        """ % (self.ConfigId,)

        print self.HLTSequenceMap
        cursor.execute(SequencePrescaleQuery)
        self.HLTPrescaleTable=[ [] ]*len(self.HLTList)
        lastIndex=-1
        lastSeq=-1
        row = []
        for seq,index,val in cursor.fetchall():
            if lastIndex!=index-1:
                self.HLTPrescaleTable[self.HLTSequenceMap.index(lastSeq)].append(row)
                row=[]
            lastSeq=seq
            lastIndex=index
            row.append(val)
            
    def GetHLTSeeds(self):
        ## This is a rather delicate query, but it works!
        ## Essentially get a list of paths associated with the config, then find the module of type HLTLevel1GTSeed associated with the path
        ## Then find the parameter with field name L1SeedsLogicalExpression and look at the value
        ##
        ## NEED TO BE LOGGED IN AS CMS_HLT_R
        cmd='cat ~hltpro/secure/cms_hlt_r.txt'
        line=os.popen(cmd).readlines()
        magic = line[0].rstrip("\n\r")
        connect= 'cms_hlt_r/' + magic + '@cms_omds_lb'
        # connect to the DB
        tmporcl = cx_Oracle.connect(connect)
        tmpcurs = tmporcl.cursor()
        sqlquery ="""  
        SELECT I.NAME,A.VALUE
        FROM
        CMS_HLT.STRINGPARAMVALUES A,
        CMS_HLT.PARAMETERS B,
        CMS_HLT.SUPERIDPARAMETERASSOC C,
        CMS_HLT.MODULETEMPLATES D,
        CMS_HLT.MODULES E,
        CMS_HLT.PATHMODULEASSOC F,
        CMS_HLT.CONFIGURATIONPATHASSOC G,
        CMS_HLT.CONFIGURATIONS H,
        CMS_HLT.PATHS I
        WHERE
        A.PARAMID = C.PARAMID AND
        B.PARAMID = C.PARAMID AND
        B.NAME = 'L1SeedsLogicalExpression' AND
        C.SUPERID = F.MODULEID AND
        D.NAME = 'HLTLevel1GTSeed' AND
        E.TEMPLATEID = D.SUPERID AND
        F.MODULEID = E.SUPERID AND
        F.PATHID=G.PATHID AND
        I.PATHID=G.PATHID AND
        G.CONFIGID=H.CONFIGID AND
        H.CONFIGDESCRIPTOR='%s' 
        """ % (self.HLT_Key,)
        tmpcurs.execute(sqlquery)
        for HLTPath,L1Seed in tmpcurs.fetchall():
            self.HLTList.append(HLTPath)
            self.HLTSeed.append([HLTPath,L1Seed])
            self.TriggerRates.append([HLTPath])
            self.RateTable.append([HLTPath])
        #self.GetHLTPrescaleMatrix(tmpcurs)

    def ParseRunSetup(self):
        #queries that need to be run only once per run
        self.GetRunInfo()
        self.GetL1NameIndexAssoc()
        self.GetL1AlgoPrescales()
        self.GetHLTSeeds()

    def UpdateRun(self,StartLS,EndLS):
        if EndLS<StartLS:
            print "Invalid Lumi Section Range"
            return
        self.GetLumiInfo()
        if StartLS < 0:
            EndLS = max(self.LSByLS) - 1
            StartLS = EndLS + StartLS
        if StartLS < 2: #The parser does not parse the first LS
            StartLS = 2
        if StartLS == 999999:
            StartLS = min(self.LSByLS)
        if EndLS == 111111:
            EndLS = max(self.LSByLS)
        if EndLS>self.LastLSParsed:
            print "EndLS out of range"
            return
        self.FillLumiInfo(StartLS,EndLS)
        self.GetHLTRates(StartLS,EndLS)
        self.CalculateAvL1Prescales(StartLS,EndLS)
        self.CalculateTotalPrescales()
        self.UnprescaleRates()

    def CalculateAvL1Prescales(self,StartLS,EndLS):
        self.AvgL1Prescales=[0]*len(self.L1IndexNameMap) ## make it an array of 0s of the right length (should be 128, but don't assume)
        for index in range(StartLS,EndLS+1):
            psi = self.PSColumnByLS[index]
            if not psi:
                print "Cannot figure out PSI for LS "+str(index)
                continue
            for algo in range(len(self.L1IndexNameMap)):
                self.AvgL1Prescales[algo]+=self.L1PrescaleTable[algo][psi]                
        for i in range(len(self.AvgL1Prescales)):
            self.AvgL1Prescales[i] = self.AvgL1Prescales[i]/(EndLS-StartLS+1)
        
    def CalculateTotalPrescales(self):
        self.AvgTotalPrescales=[]
        for i,n in enumerate(self.HLTList):
            hltPS=0
            if len(self.TriggerRates[i])>0:
                hltPS = self.TriggerRates[i][3]
            l1Index = self.GetL1Index(self.HLTSeed[i][1].lstrip('"').rstrip('"'))
            l1PS=0
            if l1Index==-1:
                print "Could not find prescale for seed "+self.HLTSeed[i][1]
            else:
                l1PS = self.AvgL1Prescales[l1Index]
            #print hltPS+" "+l1PS
            self.AvgTotalPrescales.append(hltPS*l1PS)


    def UnprescaleRates(self):
        self.PrescaledRates=[]
        self.UnprescaledRates=[]
        for i,n in enumerate(self.HLTList):
            psRate=0
            if len(self.TriggerRates[i])>0:
                psRate = self.TriggerRates[i][0]
            totalPS = self.AvgTotalPrescales[i]
            unpsRate = psRate
            if totalPS:
                unpsRate = psRate*totalPS
            self.PrescaledRates.append(psRate)
            self.UnprescaledRates.append(unpsRate)
        
    def AssemblePrescaleValues(self): ##Depends on output from ParseLumiPage and ParseTriggerModePage
        return ## WHAT DOES THIS FUNCTION DO???
        MissingName = "Nemo"
        for key in self.L1TriggerMode:
            self.L1Prescale[key] = {}
            for n in range(min(self.LSByLS),max(self.LSByLS)+1): #"range()" excludes the last element
                try:
                    self.L1Prescale[key][n] = self.L1TriggerMode[key][self.PSColumnByLS[n]]
                except:
                    if not key == MissingName:
                        self.MissingPrescale.append(key)
                        MissingName = key
                    if not n < 2:
                        print "LS "+str(n)+" of key "+str(key)+" is missing from the LumiSections page"

        for key in self.HLTTriggerMode:
            self.HLTPrescale[key] = {}
            for n in range(min(self.LSByLS),max(self.LSByLS)+1): #"range" excludes the last element
                try:
                    self.HLTPrescale[key][n] = self.HLTTriggerMode[key][self.PSColumnByLS[n]]
                except:
                    if not key == MissingName:
                        self.MissingPrescale.append(key)
                        MissingName = key
                    if not n < 2:
                        print "LS "+str(n)+" of key "+str(key)+" is missing from the LumiSections page"

        self.PrescaleValues = [self.L1Prescale,self.HLTPrescale,self.MissingPrescale]
        return self.PrescaleValues

    def ComputeTotalPrescales(self,StartLS,EndLS):
        return ## WHAT DOES THIS FUNCTION DO??
        IdealHLTPrescale = {}
        IdealPrescale = {}
        L1_zero = {}
        HLT_zero = {}
        n1 = {}
        n2 = {}
        L1 = {}
        L2 = {}
        H1 = {}
        H2 = {}
        InitialColumnIndex = self.PSColumnByLS[int(StartLS)]

        for key in self.HLTTriggerMode:
            try:
                DoesThisPathHaveAValidL1SeedWithPrescale = self.L1Prescale[self.HLTSeed[key]][StartLS]
            except:
                L1_zero[key] = True
                HLT_zero[key] = False
                continue

            IdealHLTPrescale[key] = 0.0
            IdealPrescale[key] = 0.0
            n1[key] = 0
            L1_zero[key] = False
            HLT_zero[key] = False

            for LSIterator in range(StartLS,EndLS+1): #"range" excludes the last element
                if self.L1Prescale[self.HLTSeed[key]][LSIterator] > 0 and self.HLTPrescale[key][LSIterator] > 0:
                    IdealPrescale[key]+=1.0/(self.L1Prescale[self.HLTSeed[key]][LSIterator]*self.HLTPrescale[key][LSIterator])
                else:
                    IdealPrescale[key]+=1.0 ##To prevent a divide by 0 error later
                    if self.L1Prescale[self.HLTSeed[key]][LSIterator] < 0.1:
                        L1_zero[key] = True
                    if self.HLTPrescale[key][LSIterator] < 0.1:
                        HLT_zero[key] = True
                if self.PSColumnByLS[LSIterator] == InitialColumnIndex:
                    n1[key]+=1

            if L1_zero[key] == True or HLT_zero[key] == True:
                continue

            IdealPrescale[key] = (EndLS + 1 - StartLS)/IdealPrescale[key]

            n2[key] = float(EndLS + 1 - StartLS - n1[key])
            L1[key] = float(self.L1Prescale[self.HLTSeed[key]][StartLS])
            L2[key] = float(self.L1Prescale[self.HLTSeed[key]][EndLS])
            H1[key] = float(self.HLTPrescale[key][StartLS])
            H2[key] = float(self.HLTPrescale[key][EndLS])

            IdealHLTPrescale[key] = ((n1[key]/L1[key])+(n2[key]/L2[key]))/((n1[key]/(L1[key]*H1[key]))+(n2[key]/(L2[key]*H2[key])))

        self.TotalPSInfo = [L1_zero,HLT_zero,IdealPrescale,IdealHLTPrescale,n1,n2,L1,L2,H1,H2]

        return self.TotalPSInfo

        
    def CorrectForPrescaleChange(self,StartLS,EndLS):
        [L1_zero,HLT_zero,IdealPrescale,IdealHLTPrescale,n1,n2,L1,L2,H1,H2] = self.TotalPSInfo
        xLS = {}
        RealPrescale = {}

        for key in self.HLTTriggerMode:
            if L1_zero[key] == True or HLT_zero[key] == True:
                continue
            [TriggerRate,L1Pass,PSPass,PS,Seed,StartLS,EndLS] = self.TriggerRates[key]
            if PS > 0.95 * IdealHLTPrescale[key] and PS < 1.05 * IdealHLTPrescale[key]:
                RealPrescale[key] = IdealPrescale[key]
                continue
                
            if H1[key] == H2[key] and L1[key] == L2[key] and not EndLS > max(self.LSByLS) - 1: ##Look for prescale change into the next LS
                H2[key] = float(self.HLTPrescale[key][EndLS+1])
                L2[key] = float(self.L1Prescale[self.HLTSeed[key]][EndLS+1])
            if H1[key] == H2[key] and L1[key] == L2[key] and not StartLS < 3:
                H1[key] = float(self.HLTPrescale[key][StartLS-1])
                L1[key] = float(self.L1Prescale[self.HLTSeed[key]][StartLS-1])
            if H1[key] == H2[key]:
                xLS[key] = 0
            else:
                xLS[key] = ((-(PS/IdealHLTPrescale[key])*(L2[key]*n1[key]+L1[key]*n2[key])*(H2[key]*L2[key]*n1[key]+H1[key]*L1[key]*n2[key]))+((H2[key]*L2[key]*n1[key]+H1[key]*L1[key]*n2[key])*(L2[key]*n1[key]+L1[key]*n2[key])))/(((PS/IdealHLTPrescale[key])*(L2[key]*n1[key]+L1[key]*n2[key])*(H1[key]*L1[key]-H2[key]*L2[key]))+((H2[key]*L2[key]*n1[key]+H1[key]*L1[key]*n2[key])*(L2[key]-L1[key])))

            if xLS[key] > 1:
                xLS[key] = 1
            if xLS[key] < -1:
                xLS[key] = -1
            RealPrescale[key] = (n1[key] + n2[key])/(((n1[key] - xLS[key])/(H1[key]*L1[key]))+(n2[key]+xLS[key])/(H2[key]*L2[key]))

        self.CorrectedPSInfo = [RealPrescale,xLS,L1,L2,H1,H2]

        return self.CorrectedPSInfo
        
    def Save(self, fileName):
        dir = os.path.dirname(fileName)    
        if not os.path.exists(dir):
            os.makedirs(dir)
        pickle.dump( self, open( fileName, 'w' ) )

    def Load(self, fileName):
        self = pickle.load( open( fileName ) )
