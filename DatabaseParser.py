import cx_Oracle
import cPickle as pickle
import os, sys
import time
import re
from sets import Set


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
        self.HLTRatesByLS = {}
        self.HLTPSByLS = {}

        self.nAlgoBits=0
        self.L1PrescaleTable=[]
        self.AvgL1Prescales=[] ## contains the average L1 prescales for the current LS range range
        self.HLTList=[]
        self.AvgTotalPrescales={}
        self.HLTPrescaleTable=[] ## can't fill this yet
        self.UnprescaledRates={}
        self.PrescaledRates={}
        ##-- Defined in ParseLumiPage --##
        self.LastLSParsed=-1
        self.InstLumiByLS = {}
        self.DeliveredLumiByLS = {}
        self.LiveLumiByLS = {}
        self.PSColumnByLS = {}
        self.AvInstLumi = 0
        self.AvDeliveredLumi = 0
        self.AvLiveLumi = 0
        self.AvDeadTime = 0
        self.LumiInfo = {}  ##Returns
        self.DeadTime = {}
        self.Physics = {}
        self.Active = {}
        
        ##-- Defined in ParsePSColumnPage (not currently used) --##
        self.PSColumnChanges=[]  ##Returns

        ##-- Defined in ParseTriggerModePage --##
        self.L1TriggerMode={}  ## 
        self.HLTTriggerMode={} ## 
        self.HLTSeed={}
        self.HLTSequenceMap=[]
        self.TriggerInfo = []  ##Returns

        ##-- Defined in AssemblePrescaleValues --##
        self.L1Prescale={}
        self.L1IndexNameMap={}
        self.HLTPrescale=[]
        self.MissingPrescale=[]
        self.PrescaleValues=[]  ##Returns

        ##-- Defined in ComputeTotalPrescales --##
        self.TotalPSInfo = []  ##Returns # #collection 

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

    def GetHLTRates(self,LSRange):
        sqlquery = """SELECT SUM(A.L1PASS),SUM(A.PSPASS),SUM(A.PACCEPT)
        ,SUM(A.PEXCEPT),(SELECT L.NAME FROM CMS_HLT.PATHS L WHERE L.PATHID=A.PATHID) PATHNAME 
        FROM CMS_RUNINFO.HLT_SUPERVISOR_TRIGGERPATHS A WHERE RUNNUMBER=%s AND A.LSNUMBER>=%d AND A.LSNUMBER<%d
        GROUP BY A.LSNUMBER,A.PATHID"""

        #print "Getting HLT Rates for LS from %d to %d" % (LSRange[0],LSRange[-1],)
        query = sqlquery % (self.RunNumber,LSRange[0],LSRange[-1],)
        self.curs.execute(query)

        TriggerRates = {}
        for L1Pass,PSPass,HLTPass,HLTExcept,name in self.curs.fetchall():
            rate = HLTPass/23.3
            ps = 0
            if PSPass:
                ps = float(L1Pass)/PSPass
            TriggerRates[name]= [ps,rate,L1Pass,PSPass]
            
        return TriggerRates

    def GetTriggerRatesByLS(self,triggerName):
        sqlquery = """SELECT A.LSNUMBER, A.PACCEPT
        FROM CMS_RUNINFO.HLT_SUPERVISOR_TRIGGERPATHS A, CMS_HLT.PATHS B
        WHERE RUNNUMBER=%s AND B.NAME = \'%s\' AND A.PATHID = B.PATHID
        GROUP BY A.LSNUMBER,A.PATHID""" % (self.RunNumber,triggerName,)

        self.curs.execute(sqlquery)
        r={}
        for ls,accept in  self.curs.fetchall():
            r[ls] = accept/23.3
        return r
    
    def GetAllTriggerRatesByLS(self):
        for hltName in self.HLTSeed:
            self.HLTRatesByLS[hltName] = self.GetTriggerRatesByLS(hltName)

    def GetLumiInfo(self): 
        sqlquery="""SELECT RUNNUMBER,LUMISECTION,PRESCALE_INDEX,INSTLUMI,LIVELUMI,DELIVLUMI,DEADTIME
        ,DCSSTATUS,PHYSICS_FLAG,CMS_ACTIVE
        FROM CMS_RUNTIME_LOGGER.LUMI_SECTIONS A,CMS_GT_MON.LUMI_SECTIONS B WHERE A.RUNNUMBER=%s
        AND B.RUN_NUMBER(+)=A.RUNNUMBER AND B.LUMI_SECTION(+)=A.LUMISECTION AND A.LUMISECTION > %d
        ORDER BY A.RUNNUMBER,A.LUMISECTION"""
        
        ## Get the lumi information for the run, just update the table, don't rebuild it every time
        query = sqlquery % (self.RunNumber,self.LastLSParsed)
        self.curs.execute(query)
        pastLSCol=-1
        for run,ls,psi,inst,live,dlive,dt,dcs,phys,active in self.curs.fetchall():
            self.PSColumnByLS[ls]=psi
            self.InstLumiByLS[ls]=inst
            self.LiveLumiByLS[ls]=live
            self.DeliveredLumiByLS[ls]=dlive
            self.DeadTime[ls]=dt
            self.Physics[ls]=phys
            self.Active[ls]=active
            if pastLSCol!=-1 and ls!=pastLSCol:
                self.PSColumnChanges.append([ls,psi])
            pastLSCol=ls
            if ls>self.LastLSParsed:
                self.LastLSParsed=ls
        self.LumiInfo = [self.PSColumnByLS, self.InstLumiByLS, self.DeliveredLumiByLS, self.LiveLumiByLS, self.DeadTime]

    def GetAvLumiInfo(self,LSRange):
        nLS=0;
        AvInstLumi=0
        StartLS = LSRange[0]
        EndLS   = LSRange[-1]
        AvLiveLumi=self.LiveLumiByLS[EndLS]-self.LiveLumiByLS[StartLS]
        AvDeliveredLumi=self.DeliveredLumiByLS[EndLS]-self.DeliveredLumiByLS[StartLS]
        AvDeadTime=AvDeliveredLumi/AvLiveLumi * 100
        PSCols=Set()
        for ls in LSRange:
            try:
                AvInstLumi+=self.InstLumiByLS[ls]
                PSCols.add(self.PSColumnByLS[ls])
                nLS+=1
            except:
                print "ERROR: Lumi section "+str(ls)+" not in bounds"
                return
        return [AvInstLumi/nLS,AvLiveLumi/nLS, AvDeliveredLumi/nLS, AvDeadTime/nLS,PSCols]
    
    def ParsePSColumnPage(self): ## this is now done automatically when we read the db
        pass

    def GetL1NameIndexAssoc(self):
        ## get the L1 algo names associated with each algo bit
        AlgoNameQuery = """SELECT ALGO_INDEX, ALIAS FROM CMS_GT.L1T_MENU_ALGO_VIEW
        WHERE MENU_IMPLEMENTATION IN (SELECT L1T_MENU_FK FROM CMS_GT.GT_SETUP WHERE ID='%s')
        ORDER BY ALGO_INDEX""" % (self.GT_Key,)
        self.curs.execute(AlgoNameQuery)
        for index,name in self.curs.fetchall():
            self.L1IndexNameMap[name] = index
            
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
        self.nAlgoBits=128

    def GetHLTIndex(self,name):
        for i,n in enumerate(self.HLTList):
            if n.find(name)!=-1:
                return i
        #print name
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

        #print self.HLTSequenceMap
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
        ORDER BY A.VALUE
        """ % (self.HLT_Key,)
        tmpcurs.execute(sqlquery)
        for HLTPath,L1Seed in tmpcurs.fetchall():
            if not self.HLTSeed.has_key(HLTPath): ## this should protect us from L1_SingleMuOpen
                self.HLTSeed[HLTPath] = L1Seed.lstrip('"').rstrip('"') 
        #self.GetHLTPrescaleMatrix(tmpcurs)

    def ParseRunSetup(self):
        #queries that need to be run only once per run
        self.GetRunInfo()
        self.GetL1NameIndexAssoc()
        self.GetL1AlgoPrescales()
        self.GetHLTSeeds()
        self.GetLumiInfo()

    def UpdateRun(self,LSRange):
        self.GetLumiInfo()
        TriggerRates     = self.GetHLTRates(LSRange)
        L1Prescales      = self.CalculateAvL1Prescales(LSRange)
        TotalPrescales   = self.CalculateTotalPrescales(TriggerRates,L1Prescales)
        UnprescaledRates = self.UnprescaleRates(TriggerRates,TotalPrescales)

        return [UnprescaledRates, TotalPrescales, L1Prescales, TriggerRates]

    def GetLSRange(self,StartLS, NLS):
        """
        returns an array of valid LumiSections
        if NLS < 0, count backwards from StartLS
        """
        self.GetLumiInfo()
        LS=[]
        curLS=StartLS
        step = NLS/abs(NLS)
        NLS=abs(NLS)
        while len(LS)<NLS:
            if (curLS<0 and step<0) or (curLS>=self.LastLSParsed and step>0):
                break
            if curLS>=0 and curLS<self.LastLSParsed:
                if not self.Physics.has_key(curLS) or not self.Active.has_key(curLS):
                    break
                if self.Physics[curLS] and self.Active[curLS]:
                    if step>0:
                        LS.append(curLS)
                    else:
                        LS.insert(0,curLS)
            curLS += step
        return LS

    def CalculateAvL1Prescales(self,LSRange):
        AvgL1Prescales = [0]*self.nAlgoBits
        for index in LSRange:
            psi = self.PSColumnByLS[index]
            if not psi:
                print "Cannot figure out PSI for LS "+str(index)+"  setting to 0"
                psi = 0
            for algo in range(self.nAlgoBits):
                AvgL1Prescales[algo]+=self.L1PrescaleTable[algo][psi]
        for i in range(len(AvgL1Prescales)):
            AvgL1Prescales[i] = AvgL1Prescales[i]/len(LSRange)
        return AvgL1Prescales
    
    def CalculateTotalPrescales(self,TriggerRates, L1Prescales):
        AvgTotalPrescales={}
        for hltName,v in TriggerRates.iteritems():
            if not self.HLTSeed.has_key(hltName):
                continue 
            hltPS=0
            if len(v)>0:
                hltPS = v[0]
            l1Index=-1
            if self.L1IndexNameMap.has_key(self.HLTSeed[hltName]):
                l1Index = self.L1IndexNameMap[self.HLTSeed[hltName]]

            l1PS=0
            if l1Index==-1:
                l1PS = self.UnwindORSeed(self.HLTSeed[hltName],L1Prescales)
            else:
                l1PS = L1Prescales[l1Index]
            AvgTotalPrescales[hltName]=l1PS*hltPS
        return AvgTotalPrescales

    def UnwindORSeed(self,expression,L1Prescales):
        """
        Figures out the effective prescale for the OR of several seeds
        we take this to be the *LOWEST* prescale of the included seeds
        """
        if expression.find(" OR ") == -1:
            return -1  # Not an OR of seeds
        seedList = expression.split(" OR ")
        if len(seedList)==1:
            return -1 # Not an OR of seeds, really shouldn't get here...
        minPS = 99999999999
        for seed in seedList:
            if not self.L1IndexNameMap.has_key(seed):
                continue
            ps = L1Prescales[self.L1IndexNameMap[seed]]
            if ps:
                minPS = min(ps,minPS)
        if minPS==99999999999:
            return 0
        else:
            return minPS
    
    def UnprescaleRates(self,TriggerRates,TotalPrescales):
        UnprescaledRates = {}
        for hltName,v in TriggerRates.iteritems():
            if TotalPrescales.has_key(hltName):
                ps = TotalPrescales[hltName]
                if ps:                    
                    UnprescaledRates[hltName] = v[1]*ps
                else:
                    UnprescaledRates[hltName] = v[1]
            else:
                UnprescaledRates[hltName] = v[1]
        return UnprescaledRates
    
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
        
    def GetAvLumiPerRange(self, NMergeLumis=10):
        """
        This function returns a per-LS table of the average lumi of the previous NMergeLumis LS
        """
        AvLumiRange = []
        AvLumiTable = {}
        for ls,lumi in self.InstLumiByLS.iteritems():
            try:
                AvLumiRange.append(int(lumi))
            except:
                continue
            if len(AvLumiRange) == NMergeLumis:
                AvLumiRange = AvLumiRange[1:]
                AvLumiTable[ls] = sum(AvLumiRange)/NMergeLumis
        return AvLumiTable
        
    def Save(self, fileName):
        dir = os.path.dirname(fileName)    
        if not os.path.exists(dir):
            os.makedirs(dir)
        pickle.dump( self, open( fileName, 'w' ) )

    def Load(self, fileName):
        self = pickle.load( open( fileName ) )



def GetLatestRunNumber():
    cmd='cat ~centraltspro/secure/cms_trg_r.txt'
    line=os.popen(cmd).readlines()
    magic = line[0].rstrip("\n\r")
    connect= 'cms_trg_r/' + magic + '@cms_omds_lb'
    # connect to the DB
    orcl = cx_Oracle.connect(connect)
    curs = orcl.cursor()
    RunNoQuery="""
    SELECT MAX(A.RUNNUMBER) FROM CMS_RUNINFO.RUNNUMBERTBL A, CMS_WBM.RUNSUMMARY B WHERE A.RUNNUMBER=B.RUNNUMBER AND B.TRIGGERS>0
    """
    curs.execute(RunNoQuery)
    r, = curs.fetchone()
    TrigModeQuery = """
    SELECT TRIGGERMODE FROM CMS_WBM.RUNSUMMARY WHERE RUNNUMBER = %d
    """ % r
    curs.execute(TrigModeQuery)
    trigm, = curs.fetchone()
    isCol=0
    if trigm.find('l1_hlt_collisions')!=-1:
        isCol=1
    return (r,isCol,)

def ClosestIndex(value,table):
    diff = 999999999;
    index = 0
    for i,thisVal in table.iteritems():
        if abs(thisVal-value)<diff:
            diff = abs(thisVal-value)
            index =i
    return index


def StripVersion(name):
    if re.match('.*_v[0-9]+',name):
        name = name[:name.rfind('_')]
    return name
