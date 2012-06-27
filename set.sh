#!/bin/bash
export SCRAM_ARCH=slc5_amd64_gcc462
pushd /nfshome0/cmssw2
source cmsset_default.sh
cd /nfshome0/cmssw2/slc5_amd64_gcc462/cms/cmssw/CMSSW_5_2_4/src
##cd slc5_ia32_gcc434/cms/cmssw/CMSSW_3_8_2/
#cd slc5_amd64_gcc434/cms/cmssw/CMSSW_4_4_2/
##cd slc5_amd64_gcc461/cms/cmssw/CMSSW_5_0_1/
cmsenv
popd
#source /nfshome0/abrinke1/UserCode/Andrew/setupCVS.sh
