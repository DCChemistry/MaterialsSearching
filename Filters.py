import shutil
from pymatgen.core.composition import Composition
from datetime import datetime
import os
import re
from pymatgen.core.structure import Structure
from pymatgen.analysis.dimensionality import get_structure_components
from pymatgen.analysis.local_env import MinimumDistanceNN
from pymatgen.core.periodic_table import Element
from robocrys import StructureCondenser
from Util import SaveDictAsJSON, ReadJSONFile, ListOfTheElements, ConvertJSONresultsToExcel, BlockPrint, EnablePrint
import smact
import numpy as np
import itertools
from smact.screening import pauling_test

from Batching import batch_map

class Analysis:

    def __init__(self, searchName:str, orderOfFilters:list):
        #orderOfFilters is the order of the keys from 'filters' dictionary
        self.searchName = searchName


        #########################################################################################################################################################
        #PUT IN NEW FILTERS IN THIS DICTIONARY. Format is "Name": Analysis.functionName  (leave the ones that start with 'self' in the dictionary below as is - they're fine as they are)
        filters = {
                    "Inorganic": Analysis.InorganicFilter,                     #Removes materials that contain both C and H, leaving only inorganic materials
                    "Dimensionality": Analysis.DimensionalityFilter,           #Saves materials that have a specified dimensionality (2 by default). This is a VERY slow filter - try to use this as late as possible in your search.
                    "Cu_or_Ni": Analysis.Ni_or_CuFilter,                       #Saves materials that contain Ni or Cu
                    "BinaryComp": Analysis.BinaryCompoundFilter,               #Saves binary compounds
                    "ContainsMetal": Analysis.ContainsMetalFilter,             #Saves materials that contain metals
                    "ContainsHalogen": Analysis.ContainsHalogenFilter,         #Saves materials that contain halogens
                    "ContainsFBlock": Analysis.ContainsFBlockFilter,           #Saves materials that contain a f-block element
                    "AntiFBlock": Analysis.AntiFBlockFilter,
                    "ContainsTM": Analysis.ContainsTransitionMetalFilter,      #Saves materials that contain a transition metal
                    "ContainsCorN": Analysis.ContainsCorNFilter,               #Saves materials that contain C or N
                    "MXeneRatio": Analysis.CheckMXeneRatioFilter,              #Saves materials that have an MXene ratio (use only after ContainsTM and ContainsCorN) - M(transition metal):X(C or N) - 2:1, 3:2, 4:3, 5:4
                    "ContainsOxygen": Analysis.ContainsOxygenFilter,
                    "7to1Ratio": Analysis.LargeToSmallAmountRatioFilter7to1,
                    "PutStructuresIntoDB": Analysis.InputStructuresIntoData,
                    "GetCondensedStructures": Analysis.GetCondensedStructures,
                    "RemoveIntermetallics": Analysis.RemoveIntermetallicsFilter,
                    "ContainsTMorF": Analysis.ContainsTMorF_Filter,
                    "Contains3orLessElem": Analysis.TernaryOrLessCompoundFilter,
                    "AntiActinide": Analysis.AntiActinideFilter,
                    "ChargeBalance": Analysis.ChargeBalanceFilter,
                    "GetStructures": self.GetStructures                        #Acquires the structures for the results for the previous filter
        }
        #########################################################################################################################################################

        for counter, filter in enumerate(orderOfFilters):
            self.previousFilter = orderOfFilters[counter-1]
            self.previousFilterCounter = counter
            if(counter==0):
                self.ReadAnalyseWrite(filters[filter], "Database", filter, counter)
            else:
                self.ReadAnalyseWrite(filters[filter], orderOfFilters[counter-1], filter, counter)


    def ReadAnalyseWrite(self, analysisType, prevAnalysisTag, newAnalysisTag, numberInQueue): #numberInQueue is to show the order each filter was applied in
        """AnalysisType is the name of the method used to analyse the data, e.g. NonPolar.
           prevAnalysisTag is the text appeneded to the end of the analysis file you want to load.
           newAnalysisTag that will be appended to the end of the analysis file you want to create."""
        
        if(not os.path.isfile(f"{numberInQueue+1}_{newAnalysisTag}.json")):
            print(f"\nStarting {newAnalysisTag} analysis:")
            results = ReadJSONFile(f"{numberInQueue}_{prevAnalysisTag}")
            analysisResults = analysisType(results)
            SaveDictAsJSON(f"{numberInQueue+1}_{newAnalysisTag}", analysisResults)
            ConvertJSONresultsToExcel(f"{numberInQueue+1}_{newAnalysisTag}")
            print(f"{newAnalysisTag} analysis complete.")
            # ^ numberInQueue+1 starts from 1, hence numberInQueue without the +1 is the previous numberInQueue
            if(type(results) == dict):
                numOfMatInPrevAnal = len(list(results.keys()))
                numOfMatInCurrentAnal = len(list(analysisResults.keys()))
            elif(type(results) == list):
                numOfMatInPrevAnal = len(results)
                numOfMatInCurrentAnal = len(analysisResults)
            print(f"{numOfMatInCurrentAnal} materials identified.")
            print(f"{numOfMatInPrevAnal-numOfMatInCurrentAnal} materials removed from previous analysis ({prevAnalysisTag}).")
            #logging
            with open("SearchLog.txt", mode="a") as f:
                f.write(f"{newAnalysisTag}: {numOfMatInCurrentAnal}\n")
        else:
            print(f"{newAnalysisTag} analysis has already been done for search {self.searchName}.")


#########################################################################################################################################################
#This where you'll define your filters. So that the code functions, you need to write your filters in a specific way:
#   1) Indented by 1 (this is so that the function is inside the Analysis class)
#   2) With "@staticmethod" written above the function (see below). Only deviate from this if you know what you're doing and are familiar with Python classes.
#   3) All filters have only one positional argument - results. See InorganicFilter and DimensionalityFilter.

    @staticmethod
    def _containsHalogen(formula):
        """
        Returns True if a material contains a halogen, returns False otherwise.

        This is the core function of ContainsHalogenFilter.
        """
        elemsInFormula = list(Composition(formula).as_dict().keys())
        halogens = ["F", "Cl", "Br", "I", "At"]
        if(set(elemsInFormula) & set(halogens)):
            return True
        else:
            return False
    
    @staticmethod
    def ContainsHalogenFilter(results):
        """
        Halogen filter.

        This function only saves materials that contain a halogen.

        This function is dependant on the _containsHalogen function.
        """
        filteredResults = []
        for result in results:
            formula = result["Reduced Formula"]
            if(Analysis._containsHalogen(formula)):
                filteredResults.append(result)
        return filteredResults
    
    @staticmethod
    def _containsOxygen(formula):
        """
        Returns True if a material contains oxygen, returns False otherwise.

        This is the core function of ContainsOxygenFilter.
        """
        elemsInFormula = list(Composition(formula).as_dict().keys())
        oxygen = ["O"]
        if(set(elemsInFormula) & set(oxygen)):
            return True
        else:
            return False
    
    @staticmethod
    def ContainsOxygenFilter(results):
        """
        Oxygen filter.

        This function only saves materials that contain oxygen.

        This function is dependant on the _containsOxygen function.
        """
        filteredResults = []
        for result in results:
            formula = result["Reduced Formula"]
            if(Analysis._containsOxygen(formula)):
                filteredResults.append(result)
        return filteredResults

    @staticmethod
    def _getStructure(result):
        """
        Used to obtain the structure of a material given its ID.
        
        Input:
        A line from a .json produced by this code. So, in a filter when you write "for result in results" (see InorganicFilter function below), you'll be passing 'result' in.

        Output:
        A pymatgen Structure object that you can analyse with Pymatgen.
        """
        id = result["MaterialId"]
        cwd = os.getcwd()
        dirAbove = cwd.replace(os.getcwd().split("/")[-1], "")[:-1]
        struct = Structure.from_file(os.path.join(dirAbove, "by_id", f"{id}.CIF"))
        return struct

    @staticmethod
    def _checkInorganic(formula):
        """
        The core of the InorganicFilter filter.
        
        This function returns False if C and H are both present in the formula of a material, and True otherwise.
        """
        elems = list(Composition(formula).as_dict().keys())
        if("C" in elems and "H" in elems):
            status=False
        else:
            status=True
        return status

    @staticmethod
    def InorganicFilter(results):
        """
        Inorganic filter.

        This function only saves materials that do not contain both C and H based on their formula.

        This function is dependant on the _checkInorganic function.
        """
        filteredResults = []
        for result in results:
            formula = result["Reduced Formula"]
            if(Analysis._checkInorganic(formula)): #returns True if not organic (if C and H aren't both in the formula)
                filteredResults.append(result)
        return filteredResults

    @staticmethod
    def _get_dimensionality(structure):
        """
        The core of the DimensionalityFilter filter.
        
        Input: Pymatgen structure object.
        Output: Overall dimensionality for the structure.
        """
        mdd = MinimumDistanceNN()
        structure_copy = structure.copy()
        bonded_structure = mdd.get_bonded_structure(structure_copy) #make StructureGraph
        return max(x["dimensionality"] for x in get_structure_components(bonded_structure))
        #^ Alex says that he takes the “max” of the dimensionalities at the end because that is just to be consistent with the robocrys
        #condense function (e.g., what do you do when there are more than one bonded component in the structure with different
        #dimensionalities, safest is just to take the max dimensionality).

    @staticmethod
    def DimensionalityFilter(results, requiredDim=2):
        """
        Dimensionality filter.

        This function only saves materials that have an overall dimensionality equal to the requiredDim named argument (by default set to 2 as an example).

        This function is dependant on the _get_dimensionality function.
        """

        # Adding a counter because I'd like to know if this filter is still working or if the program died. This is a VERY slow filter.
        counter = 0
        numOfResults = len(results)

        # Filter code as normal (with try/except blocks since this filter has been known to ocassionally fail)
        filteredResults=[]
        problemChildren = [] #I've done a search before where the search just keeled over on a certain material (a problem child) - this is why we need a problem children bin.
        for result in results:
            struct = Analysis._getStructure(result)
            try:
                dim = Analysis._get_dimensionality(struct)
                if(dim==requiredDim):
                    result["dim"] = dim
                    filteredResults.append(result)
            except:
                result["FailedOnFilter"] = "Dim"
                problemChildren.append(result)

            # Incrementing the counter
            counter += 1
            if(counter%100==0): #print info on progress every 100 entries
                now = datetime.now()
                current_time = now.strftime("%H:%M:%S")
                print(f"[{current_time}]: {counter}/{numOfResults}")

        if(len(problemChildren)!=0):
            SaveDictAsJSON("ProblemChildren_Dim", problemChildren)
        return filteredResults
    
    @staticmethod
    def _containsCu_or_Ni(formula):
        """
        Returns True if a material contains Cu or Ni, returns False otherwise.

        This is the core function of Ni_or_CuFilter.
        """
        elems = list(Composition(formula).as_dict().keys())
        if("Cu" in elems or "Ni" in elems):
            return True
        else:
            return False
    
    @staticmethod
    def Ni_or_CuFilter(results):
        """
        Ni or Cu filter.

        This function only saves materials that contain Ni or Cu.

        This function is dependant on the _containsCu_or_Ni function.
        """
        filteredResults = []
        for result in results:
            formula = result["Reduced Formula"]
            if(Analysis._containsCu_or_Ni(formula)):
                filteredResults.append(result)
        return filteredResults

    @staticmethod
    def _containsMetal(formula):
        """
        Returns True if a material contains a metal, returns False otherwise.

        This is the core function of ContainsMetalFilter.
        """
        elemsInFormula = list(Composition(formula).as_dict().keys())
        allElems = ListOfTheElements()
        metals = [elem for elem in allElems if Element(elem).is_metal]
        if(set(elemsInFormula) & set(metals)): #if formula contains a metal
            return True
        else:
            return False
    
    @staticmethod
    def ContainsMetalFilter(results):
        """
        Metal filter.

        This function only saves materials that contain a metal.

        This function is dependant on the _containsMetal function.
        """
        filteredResults = []
        for result in results:
            formula = result["Reduced Formula"]
            if(Analysis._containsMetal(formula)):
                filteredResults.append(result)
        return filteredResults
    

    
    @staticmethod
    def BinaryCompoundFilter(results):
        """
        Binary compound filter.

        This function only saves materials that have exactly 2 elements.
        """
        filteredResults = []
        for result in results:
            NElements = result["NElements"]
            if(NElements==2):
                filteredResults.append(result)
        return filteredResults

    @staticmethod
    def TernaryOrLessCompoundFilter(results):
        """
        Ternary or less compound filter.

        This function only saves materials that have 3 or less elements.
        """
        filteredResults = []
        for result in results:
            NElements = result["NElements"]
            if(NElements<=3):
                filteredResults.append(result)
        return filteredResults

    @staticmethod
    def _containsFBlock(formula):
        """
        Returns True if a material contains an f-block element, returns False otherwise.

        This is the core function of ContainsFBlockFilter.
        """
        elemsInFormula = list(Composition(formula).as_dict().keys())
        allElems = ListOfTheElements()
        lanthanides = [elem for elem in allElems if Element(elem).is_lanthanoid]
        actinides = [elem for elem in allElems if Element(elem).is_actinoid]
        fBlockElems = lanthanides + actinides
        if(set(elemsInFormula) & set(fBlockElems)):
            return True
        else:
            return False
    
    @staticmethod
    def ContainsFBlockFilter(results):
        """
        f-block filter.

        This function only saves materials that contain an f-block element.

        This function is dependant on the _containsFBlock function.
        """
        # Adding a counter because I'd like to know if this filter is still working or if the program died. This is a slow filter.
        counter = 0

        numOfResults = len(results)
        filteredResults = []
        for result in results:
            formula = result["Reduced Formula"]
            if(Analysis._containsFBlock(formula)):
                filteredResults.append(result)

            # Incrementing the counter
            counter += 1
            if(counter%2000==0): #print info on progress every 100 entries
                now = datetime.now()
                current_time = now.strftime("%H:%M:%S")
                print(f"[{current_time}]: {counter}/{numOfResults}")

        return filteredResults
    
    @staticmethod
    def AntiFBlockFilter(results):
        """
        f-block filter.

        This function only saves materials that DO NOT contain an f-block element.

        This function is dependant on the _containsFBlock function.
        """
        # Adding a counter because I'd like to know if this filter is still working or if the program died. This is a slow filter.
        counter = 0

        numOfResults = len(results)
        filteredResults = []
        for result in results:
            formula = result["Reduced Formula"]
            if(not Analysis._containsFBlock(formula)): #flipping the functionality of the _containsFBlock function to get this 'anti' filter
                filteredResults.append(result)

            # Incrementing the counter
            counter += 1
            if(counter%2000==0): #print info on progress every 100 entries
                now = datetime.now()
                current_time = now.strftime("%H:%M:%S")
                print(f"[{current_time}]: {counter}/{numOfResults}")

        return filteredResults

    @staticmethod
    def _containsActinide(formula):
        """
        Returns True if a material contains an f-block element, returns False otherwise.

        This is the core function of AntiActinideFilter.
        """
        elemsInFormula = list(Composition(formula).as_dict().keys())
        allElems = ListOfTheElements()
        actinides = [elem for elem in allElems if Element(elem).is_actinoid]
        if(set(elemsInFormula) & set(actinides)):
            return True
        else:
            return False

    @staticmethod
    def AntiActinideFilter(results):
        """
        Anti-actinide filter.

        This function only saves materials that DO NOT contain an actinide.

        This function is dependant on the _containsActinide function.
        """
        # Adding a counter because I'd like to know if this filter is still working or if the program died. This is a slow filter.
        counter = 0

        numOfResults = len(results)
        filteredResults = []
        for result in results:
            formula = result["Reduced Formula"]
            if(not Analysis._containsActinide(formula)): #flipping the functionality of the _containsActinide function to get this 'anti' filter
                filteredResults.append(result)

            # Incrementing the counter
            counter += 1
            if(counter%2000==0): #print info on progress every 100 entries
                now = datetime.now()
                current_time = now.strftime("%H:%M:%S")
                print(f"[{current_time}]: {counter}/{numOfResults}")

        return filteredResults

    @staticmethod
    def ContainsTransitionMetalFilter(results):
        """
        Transition metal filter.

        This function only saves materials that contain a transition metal.

        This function is dependant on the contains_element_type function from the Pymatgen Composition class.
        """
        filteredResults = []
        for result in results:
            formula = result["Reduced Formula"]
            if(Composition(formula).contains_element_type("transition_metal")):
                filteredResults.append(result)
        return filteredResults

    @staticmethod
    def ContainsTMorF_Filter(results):
        filteredResults = []
        for result in results:
            formula = result["Reduced Formula"]
            if(Composition(formula).contains_element_type("transition_metal") or Analysis._containsFBlock):
                filteredResults.append(result)
        return filteredResults

    @staticmethod
    def _noIntermetallics(formula):
        elements = [elem for elem in Composition(formula).elements]
        metalStatus = [elem.is_metal for elem in elements]
        if(all(metalStatus)):
            return False
        else:
            return True
    
    @staticmethod
    def RemoveIntermetallicsFilter(results):
        """
        No intermetallics filter.

        This function removes materials that contain only metal elements.

        This function is dependant on the _noIntermetallics function.
        """
        filteredResults = []
        for result in results:
            formula = result["Reduced Formula"]
            if(Analysis._noIntermetallics(formula)):
                filteredResults.append(result)
        return filteredResults

    @staticmethod
    def _containsCorN(formula):
        """
        Returns True if a material contains C or N, returns False otherwise.

        This is the core function of ContainsCorNFilter.
        """
        elemsInFormula = list(Composition(formula).as_dict().keys())
        CorN = ["C", "N"]
        if(set(elemsInFormula) & set(CorN)):
            return True
        else:
            return False

    @staticmethod
    def ContainsCorNFilter(results):
        """
        C or N filter.

        This function only saves materials that contain C or N.

        This function is dependant on the _containsCorN function.
        """
        filteredResults = []
        for result in results:
            formula = result["Reduced Formula"]
            if(Analysis._containsCorN(formula)):
                filteredResults.append(result)
        return filteredResults
    
    @staticmethod
    def _checkMXeneRatios(formula): #this method should only be used after ContainsCorNFilter and ContainsTransitionMetalFilter have been applied.
        """
        Returns True if a material of the form MX, where M=transition metal and X=C/N, has an M:X ratio of 2:1, 3:2, 4:3 or 5:4. Function returns False otherwise.

        This is the core function of CheckMXeneRatioFilter.
        """
        elemsInFormula = list(Composition(formula).as_dict().keys())
        M = [elem for elem in elemsInFormula if Element(elem).is_transition_metal].pop()
        CorN = [elem for elem in elemsInFormula if elem=="C" or elem=="N"].pop()
        elemsAndAmounts = Composition(formula).get_el_amt_dict()
        if((elemsAndAmounts[M]==2 and elemsAndAmounts[CorN]==1) or (elemsAndAmounts[M]==3 and elemsAndAmounts[CorN]==2) or (elemsAndAmounts[M]==4 and elemsAndAmounts[CorN]==3) or (elemsAndAmounts[M]==5 and elemsAndAmounts[CorN]==4)):
            return True
        else:
            return False
        
    @staticmethod
    def CheckMXeneRatioFilter(results):
        filteredResults = []
        for result in results:
            formula = result["Reduced Formula"]
            if(Analysis._checkMXeneRatios(formula)):
                filteredResults.append(result)
        return filteredResults
    
    @staticmethod
    def _7to1RatioRemover(formula):
        amounts = list(Composition(formula).get_el_amt_dict().values())
        smallestAmount = min(amounts)
        largestAmount = max(amounts)
        largestToSmallestRatio = largestAmount/smallestAmount
        if(largestToSmallestRatio > 7):
            return False
        else:
            return True #only keep a material if the ratio between the largest to smallest elem amount ratio is greater than 7:1
    
    @staticmethod
    def LargeToSmallAmountRatioFilter7to1(results):
        filteredResults = []
        for result in results:
            formula = result["Reduced Formula"]
            if(Analysis._7to1RatioRemover(formula)):
                filteredResults.append(result)
        return filteredResults


    @staticmethod
    def _get_elements_stoichs(comp:str) -> list:
        """Returns list of elements and a list of stoichs from a formula string"""
        comp_dict = Composition(comp).add_charges_from_oxi_state_guesses()
        elem_symbols = [elem.symbol for elem in comp_dict.keys()]
        count = comp_dict.values()
        return tuple(elem_symbols), tuple(count)

    @staticmethod
    def _smact_validity(formula, use_pauling_test=True, include_alloys=True):
        """Check if a formula is valid by SMACT"""
        elem_symbols, count = Analysis._get_elements_stoichs(formula)
        count = [int(c) for c in count]
        #space = smact.element_dictionary(elem_symbols)
        #smact_elems = [e[1] for e in space.items()]
        smact_elems = [smact.Element(e) for e in elem_symbols]
        electronegs = [e.pauling_eneg for e in smact_elems]
        ox_combos = [e.oxidation_states for e in smact_elems]
        if len(set(elem_symbols)) == 1:
            return True
        if include_alloys:
            is_metal_list = [elem_s in smact.metals for elem_s in elem_symbols]
            if all(is_metal_list):
                return True

        threshold = np.max(count)
        compositions = []
        for ox_states in itertools.product(*ox_combos):
            stoichs = [(c,) for c in count]
            # Test for charge balance
            cn_e, cn_r = smact.neutral_ratios(
                ox_states, stoichs=stoichs, threshold=threshold)
            # Electronegativity test
            if cn_e:
                if use_pauling_test:
                    try:
                        electroneg_OK = pauling_test(ox_states, electronegs)
                    except TypeError:
                        # if no electronegativity data, assume it is okay
                        electroneg_OK = True
                else:
                    electroneg_OK = True
                if electroneg_OK:
                    for ratio in cn_r:
                        compositions.append(
                            tuple([elem_symbols, ox_states, ratio]))
        compositions = [(i[0], i[2]) for i in compositions]
        compositions = list(set(compositions))
        if len(compositions) > 0:
            return True
        else:
            return False

    @staticmethod
    def ChargeBalanceFilter(results): #known issue - this does not work for cases where there's only one atom of an element that can undergo charge disproportionation, e.g. BiO2
        filteredResults = []
        for result in results:
            formula = result["Reduced Formula"]
            if(Analysis._smact_validity(formula)):
                filteredResults.append(result)
        return filteredResults



    @staticmethod
    def _condense(struct):
        BlockPrint()
        condenser = StructureCondenser()
        condensedStruct = condenser.condense_structure(struct)
        EnablePrint()
        return condensedStruct

    @staticmethod
    def GetCondensedStructures(results):
        counter = [0]
        numOfResults = len(results)
        results = Analysis._loadStructures(results)

        def with_task(result):
            counter[0] += 1
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")
            print(f"[{current_time}]: {counter}/{numOfResults}")

        def filter(result):
            struct = result["structure"]
            condensedStruct = Analysis._condense(struct)
            result["condensed_struct"] = condensedStruct
            return result

        batch_map(filter, results, 200, callback=with_task)
        results = Analysis._storeStructures(results)
        return results

    def GetStructures(self, results): #this is a non-static method, hence the lack of the @staticmethod decorator - this relies on an instance of the Analysis class.
        """
        Not a filter, but can be called like one in the usual way.

        This function returns a directory with the structures from the results identified in the previous filter.

        So, if you apply these filters: ["BinaryComp", "ContainsMetal", "ContainsHalogen"] to get all metal halides, you can add GetStructures like so:
        ["BinaryComp", "ContainsMetal", "ContainsHalogen", "GetStructures"], and a directory containing the materials identified in the ContainsHalogen
        filter will be created.
        """
        structureDirName = f"{self.previousFilterCounter}_{self.previousFilter}_structures"
        print(structureDirName)
        if(not os.path.isdir(structureDirName)):
            os.mkdir(structureDirName)
            for result in results:
                id = result["MaterialId"]
                cwd = os.getcwd()
                dirAbove = cwd.replace(os.getcwd().split("/")[-1], "")[:-1]
                shutil.copy(os.path.join(dirAbove, "by_id", f"{id}.CIF"), structureDirName)

        return results

    @staticmethod
    def InputStructuresIntoData(results):
        counter = 0
        numOfResults = len(results)
        print("Acquiring structures and saving them in the database.")
        for result in results:
            struct = Analysis._getStructure(result)
            result["structure"] = struct
                        # Incrementing the counter
            counter += 1
            if(counter%500==0): #print info on progress every 100 entries
                now = datetime.now()
                current_time = now.strftime("%H:%M:%S")
                print(f"[{current_time}]: {counter}/{numOfResults}")
        results = Analysis._storeStructures(results)
        return results

    @staticmethod
    def _loadStructures(results):
        print("Loading structures.")
        counter = 0
        numOfResults = len(results)
        loadedResults = []
        for result in results:
            item = {k:(Structure.from_dict(v) if k=="structure" else v) for (k,v) in result.items()}
            loadedResults.append(item)
            counter += 1
            if(counter%500==0): #print info on progress every 100 entries
                now = datetime.now()
                current_time = now.strftime("%H:%M:%S")
                print(f"[{current_time}]: {counter}/{numOfResults}")
        return loadedResults
    

    @staticmethod
    def _storeStructures(results):
        print("Storing structures.")
        counter = 0
        numOfResults = len(results)
        storedResults = []
        for result in results:
            item = {k:(v.as_dict() if k=="structure" else v) for (k,v) in result.items()}
            storedResults.append(item)
            counter += 1
            if(counter%500==0): #print info on progress every 100 entries
                now = datetime.now()
                current_time = now.strftime("%H:%M:%S")
                print(f"[{current_time}]: {counter}/{numOfResults}")
        return storedResults

    @staticmethod
    def _getChargesPerElement(formula):
        """
        Note: this function is not in use by default (but I thought it could be handy if someone wanted to use it).

        This function takes a formula and returns a dictionary in the form {element_symbol: charge}
        """
        chemical = Composition(formula) #converting formula to pymatgen Composition object
        oxStates = list(chemical.add_charges_from_oxi_state_guesses(max_sites=-1)) #max_sites=-1 fully reduces the formula for oxidation calc
        oxStates = [str(element) for element in oxStates]
        alphabetRegex = re.compile('[a-zA-Z]+')
        elements = [alphabetRegex.findall(element)[0] for element in oxStates]
        chargesInStruct = [oxState.replace(elem,"") for (oxState,elem) in zip(oxStates,elements)]
        chargesInStruct=[oxState[::-1] for oxState in chargesInStruct]
        chargesInStruct = [1 if charge == "+" else -1 if charge == "-" else charge for charge in chargesInStruct]
        chargesInStruct = [int(charge) for charge in chargesInStruct]
        #Checking for charge disproportionation
        CDcharges = [] #will only be filled if a CD atom is found
        for i in range(len(elements)):
            elemInstances = elements.count(elements[i])
            if(elemInstances > 1):
                CDatom = elements[i]
                CDcharges.append(chargesInStruct[i])

        elemAndChargeDict = dict(zip(elements,chargesInStruct))
        try: #this will only work if CDatom exists, i.e. if charge disproportionation is taking place in this system
            elemAndChargeDict[CDatom] = CDcharges
        except:
            pass
        return elemAndChargeDict
