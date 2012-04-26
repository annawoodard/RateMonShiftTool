//This script will take all the rate comparison plots from a 
//root file and print them into a single pdf for easy viewing
//Usage: root -b -l -q 'dumpToPDF.C("infile.root")'  

void
dumpToPDF(string inName){
  TFile *fin = TFile::Open(inName.c_str(), "read"); assert(fin);

  string outName = inName;
  outName.replace(outName.find(".root"), 5, ".pdf");

  TCanvas c1;
  c1.Print(Form("%s[", outName.c_str()), "pdf"); //Open .pdf

  //get list of keys
  int nplots = fin->GetNkeys(); 
  TList* plots = fin->GetListOfKeys();
  for(int i=0; i<nplots; ++i){
    TKey* key = (TKey*) plots->At(i);
    if(!fin->GetKey(key->GetName())){
      cout<<"Didn't find "<<key<<". Removing."<<endl;
    }
    TCanvas* c = (TCanvas*) fin->Get(key->GetName());
    string bookmarkName = "Title: ";
    bookmarkName += key->GetName();
    c->Print(outName.c_str(), bookmarkName.c_str());
  }

  c1.Print(Form("%s]", outName.c_str()), "pdf"); //Close .pdf

}
