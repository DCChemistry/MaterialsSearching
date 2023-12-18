from json_tricks import dumps, loads #the json module doesn't support non-standard types (such as the output from MAPI),
                                     #but json_tricks does
import sys, os
import pandas as pd
from pymatgen.core.periodic_table import Element
import numpy as np
from pymatgen.ext.matproj import MPRester

#Functions used by MaterialSearchCore.py to prep GNOME data.
########################################
def get_NElems(elements):
    return len(list(elements))

def TurnElementsIntoList(elements):
    elements = elements.replace("[", "")
    elements = elements.replace("]", "")
    elements = elements.replace(",", "")
    elements = elements.replace("'", "")
    elements = elements.strip()
    elements = elements.split()
    return list(elements)
#########################################

def APIkeyChecker():
    APIkey = None #done so that APIkey is not lost in the scope of the with block
    if(not os.path.isfile("APIkey.txt")): #if APIkey.txt doesn't exist, ask for key and create txt file
        print("\nIt seems you do not have an API key saved.")
        while(True):
            APIkey = input("\nPlease input your API key: ")
            print(f"Testing your given API key: {APIkey}")
            with MPRester(APIkey) as mpr:
                try:
                    mpr.get_structure_by_material_id("mp-149")
                    print("API key is valid. Saving API key to file: APIkey.txt")
                    with open('APIkey.txt', 'w') as f:
                        f.write(APIkey)
                        return APIkey
                except:
                    print(f"API key {APIkey} was invalid.")

    else:
        with open("APIkey.txt", "r") as f:
            APIkey= f.read()
            return APIkey

def ConvertJSONresultsToExcel(JSONfileName): #do not need to give the .json extension - that's assumed
    results = ReadJSONFile(JSONfileName)
    df = pd.DataFrame.from_dict(results)
    if("structure" in df.columns.to_list()):
        df = df.drop("structure", axis=1)
    if("condensed_struct" in df.columns.to_list()):
        df = df.drop("condensed_struct", axis=1)
    df.to_excel(f"{JSONfileName}.xlsx")

# Disable printing
def BlockPrint():
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')

# Restore printing
def EnablePrint():
    sys.stdout = sys.__stdout__

def SaveDictAsJSON(fileName, dictionary, indent=4):
    with open(fileName+".json", "w") as f:
        f.write(dumps(dictionary, indent=indent)) #don't need to read this since it's just a 'checkpoint'

def ReadJSONFile(fileName):
    with open(fileName+".json", "r") as f:
        return loads(f.read()) #loads() returns the string from f.read() as dict

def ListOfTheElements(elementsExcluded=None):
    noOfElements = 118 #as of 2021
    atomicNos = np.arange(1, noOfElements+1) #the function stops just before the given value (default step = 1)
    
    if(elementsExcluded != None):
        atomicNos = [z for z in atomicNos if z not in elementsExcluded]
    
    symbolsTypeElement = [Element.from_Z(z) for z in atomicNos]
    symbols = [str(symbol) for symbol in symbolsTypeElement]
    
    return symbols