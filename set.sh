#!/bin/bash
export SCRAM_ARCH=slc5_amd64_gcc461
pushd /nfshome0/cmssw
source cmsset_default.sh
##cd slc5_ia32_gcc434/cms/cmssw/CMSSW_3_8_2/
##cd slc5_amd64_gcc434/cms/cmssw/CMSSW_4_4_2/
cd slc5_amd64_gcc461/cms/cmssw/CMSSW_5_0_1/
cmsenv
popd
#source /nfshome0/abrinke1/UserCode/Andrew/setupCVS.sh
