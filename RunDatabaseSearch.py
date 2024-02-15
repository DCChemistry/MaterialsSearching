from MaterialSearchCore import MaterialSearch

searchName = "Oxide_test"
listOfFilters = ["GetCondensedStructures"]
criteria = {"nelements": {"$eq": 3}, "elements": {"$in": ["O"]}, "e_above_hull": {"$eq": 0.}}
properties = ['material_id', 'pretty_formula', 'spacegroup.number', 'nsites', "nelements", "structure"]
MaterialSearch(searchName, listOfFilters, database="mp", MPcriteria=criteria, MPproperties=properties)