import numpy as np
import os
import pandas as pd
from Filters import Analysis
from Util import get_NElems, TurnElementsIntoList, APIkeyChecker, SaveDictAsJSON
from pymatgen.ext.matproj import MPRester

import Batching
Batching.setup()

def MaterialSearch_GNOME(searchName, orderOfFilters, homeDir, database):
    if(not os.path.isdir(searchName)):
        print(f"Creating search directory {searchName} and reading in GNOME database.")
        if(os.path.isfile("gnome_data_stable_materials_summary.csv")): #new version of the database has a different name than before, so I'm just renaming it to what it used to be lol
            os.rename("gnome_data_stable_materials_summary.csv", "stable_materials_summary.csv")

        results = pd.read_csv(os.path.join(homeDir, "stable_materials_summary.csv")) #loading database information
        os.mkdir(searchName)
        os.chdir(searchName)

        initialFilterName = "Database"
        initialSearchFilename = f"0_{initialFilterName}"
        if(not os.path.isfile(f"{initialSearchFilename}.json")):
            results['Elements'] = results['Elements'].apply(TurnElementsIntoList)
            NElements = results['Elements'].apply(get_NElems)
            results.insert(loc = 5,
                            column = 'NElements',
                            value = NElements)
            results = results.replace([np.inf, -np.inf, np.nan], None) #replace infinite values and NaN with "None"
            
            ###converting property headings in GNoME database for MP property names (in cases where there's a direct translation)
            results_headings = results.columns.to_list()
            GNoME_to_MP_propertyNames={
                            "Composition": "full_formula",
                            "Reduced Formula": "pretty_formula",
                            "Elements": "elements",
                            "NElements": "nelements",
                            "NSites": "nsites",
                            "Volume": "volume",
                            "Density": "density",
                            "Space Group": "spacegroup.symbol",
                            "Space Group Number": "spacegroup.number",
                            "Crystal System": "spacegroup.crystal_system"
            }
            newHeadings = [GNoME_to_MP_propertyNames[prop] if prop in list(GNoME_to_MP_propertyNames.keys()) else prop for prop in results_headings]
            results=results.set_axis(newHeadings, axis=1)
            ###

            results.to_json(f"{initialSearchFilename}.json", orient="records", indent=4)

            #logging
            with open("SearchLog.txt", mode="w") as f:
                f.write(f"{initialFilterName}: {len(results.index)}\n")
            print("Gnome database has been prepped for further analysis.")
    else:
        print(f"Search directory {searchName} already exists.")
        os.chdir(searchName)


    Analysis(searchName, orderOfFilters, homeDir, database)
    os.chdir(homeDir)


def MaterialSearch_MP(searchName, APIkey, criteria, properties, orderOfFilters, homeDir, database):

    if(not os.path.isdir(searchName)):
        print(f"Creating search directory {searchName}.")
        os.mkdir(searchName)
        os.chdir(searchName)

        initialFilterName = "MPquery"
        initialSearchFilename = f"0_{initialFilterName}"
        if(not os.path.isfile(f"{initialSearchFilename}.json")):
            print("Performing Materials Project query.")
            with MPRester(APIkey) as mpr:
                results = mpr.query(criteria, properties, chunk_size=10000)
            print("Query complete.\n")

            #logging
            with open("SearchLog.txt", mode="w") as f:
                f.write(f"{initialFilterName}: {len(results)}\n")

            #New code
            #############
            if("structure" in list(results[0].keys())):
                results = Analysis._storeStructures(results)
            #############
            SaveDictAsJSON(initialSearchFilename, results)
            print("Initial search completed.")
    else:
        print(f"Search directory {searchName} already exists.")
        os.chdir(searchName)


    Analysis(searchName, orderOfFilters, homeDir, database)
    os.chdir(homeDir)
    print("\n"*4)

def MaterialSearch(searchName:str, orderOfFilters:list[str], database:str, MPcriteria={}, MPproperties=['material_id', 'pretty_formula', 'spacegroup.number', 'nsites', "nelements"]):
    """
    The core function used to interact with this codebase.
    This is the function that user interacts with in order to perform a search of either the GNoME or MP databases.

    Args:
    
    searchName - the name of the search you want to perform.
    orderOfFilters - a list of filter names (analysis tags) that you want to apply to your search in the order provided.
    database - either "mp" or "gnome"; this determines which database will be searched (Materials Project or GNoME).
    MPcriteria - a dictionary of criteria required when performing a Materials Project query. Only required when database="mp".
    MPproperties - a list of properties asked for in a Materials Project query. Only required when database="mp".
    """
    homeDir=os.getcwd()

    database = database.lower()
    databaseDirName_dict = {"mp": "MP", "gnome": "GNoME"}

    if(database == "mp"):
        APIkey = APIkeyChecker()
        databaseDirName = databaseDirName_dict[database]
        if(not os.path.isdir(databaseDirName)):
            os.mkdir(databaseDirName)
            os.chdir(databaseDirName)
        else:
            os.chdir(databaseDirName)
        MaterialSearch_MP(searchName, APIkey, MPcriteria, MPproperties, orderOfFilters, homeDir, database)
    elif(database == "gnome"):
        databaseDirName = databaseDirName_dict[database]
        if(not os.path.isdir(databaseDirName)):
            os.mkdir(databaseDirName)
            os.chdir(databaseDirName)
        else:
            os.chdir(databaseDirName)
        MaterialSearch_GNOME(searchName, orderOfFilters, homeDir, database)
    else:
        print("Database is not recognised. Only database options are 'mp' (Materials Project) and 'gnome' (Google's GNoME database).\nTry again with either of these options, please.")
