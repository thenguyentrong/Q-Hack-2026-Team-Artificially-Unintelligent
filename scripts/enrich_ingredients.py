"""
Enriches all_data.csv with:
- RM_ingredient: cleaned ingredient name from RM_SKU
- aliases: list of alternate names / synonyms
- product_category: list of categories this ingredient belongs to
- region: 'eu', 'us', or 'global' based on supplier geography
"""

import re

import pandas as pd

# ---------------------------------------------------------------------------
# Supplier region classification
# ---------------------------------------------------------------------------
GLOBAL_SUPPLIERS = {
    "ADM",
    "Cargill",
    "Ingredion",
    "IFF",
    "Univar Solutions",
    "Ashland",
    "Colorcon",
    "Sensient",
    "Cambrex",
    "TCI America",  # Japanese parent, global ops
    "Darling Ingredients / Rousselot",  # Dutch parent, global ops
}
EU_SUPPLIERS = {
    "Icelandirect",  # Iceland / EEA
}
# Everything else is treated as US


def classify_supplier_region(supplier_name: str) -> str:
    if supplier_name in GLOBAL_SUPPLIERS:
        return "global"
    if supplier_name in EU_SUPPLIERS:
        return "eu"
    return "us"


def aggregate_region(regions) -> str:
    unique = set(regions)
    if "global" in unique:
        return "global"
    if "eu" in unique and "us" in unique:
        return "global"
    if "eu" in unique:
        return "eu"
    return "us"


# ---------------------------------------------------------------------------
# Ingredient metadata: aliases + product_category
# Keys are normalised ingredient names (lowercase, spaces)
# ---------------------------------------------------------------------------
INGREDIENT_META: dict[str, dict] = {
    # --- Vitamins ---
    "ascorbic acid": {
        "aliases": ["Vitamin C", "L-Ascorbic Acid", "E300"],
        "product_category": ["Vitamins", "Antioxidants"],
    },
    "ascorbic acid vitamin c": {
        "aliases": ["Vitamin C", "L-Ascorbic Acid", "E300"],
        "product_category": ["Vitamins", "Antioxidants"],
    },
    "vitamin c": {
        "aliases": ["Ascorbic Acid", "L-Ascorbic Acid", "E300"],
        "product_category": ["Vitamins", "Antioxidants"],
    },
    "vitamin c ascorbic acid": {
        "aliases": ["Ascorbic Acid", "L-Ascorbic Acid"],
        "product_category": ["Vitamins", "Antioxidants"],
    },
    "vitamin c calcium ascorbate": {
        "aliases": ["Calcium Ascorbate", "Ester-C"],
        "product_category": ["Vitamins", "Minerals"],
    },
    "vitamin c l ascorbic acid": {
        "aliases": ["L-Ascorbic Acid", "E300"],
        "product_category": ["Vitamins", "Antioxidants"],
    },
    "sodium ascorbate": {
        "aliases": ["Sodium Vitamin C", "E301"],
        "product_category": ["Vitamins", "Minerals"],
    },
    "calcium ascorbate": {
        "aliases": ["Ester-C", "Calcium Vitamin C"],
        "product_category": ["Vitamins", "Minerals"],
    },
    "ascorbyl palmitate": {
        "aliases": ["Vitamin C Palmitate", "E304", "Ascorbyl Hexadecanoate"],
        "product_category": ["Vitamins", "Antioxidants", "Excipients"],
    },
    "biotin": {
        "aliases": ["Vitamin B7", "Vitamin H", "Coenzyme R"],
        "product_category": ["Vitamins"],
    },
    "cholecalciferol": {
        "aliases": ["Vitamin D3", "Colecalciferol"],
        "product_category": ["Vitamins"],
    },
    "cholecalciferol vitamin d3": {
        "aliases": ["Vitamin D3", "Colecalciferol"],
        "product_category": ["Vitamins"],
    },
    "vitamin d": {
        "aliases": ["Cholecalciferol", "Ergocalciferol", "Calciferol"],
        "product_category": ["Vitamins"],
    },
    "vitamin d3": {
        "aliases": ["Cholecalciferol", "Colecalciferol"],
        "product_category": ["Vitamins"],
    },
    "vitamin d3 cholecalciferol": {
        "aliases": ["Cholecalciferol"],
        "product_category": ["Vitamins"],
    },
    "cyanocobalamin": {
        "aliases": ["Vitamin B12", "Cyanocobalamin B12"],
        "product_category": ["Vitamins"],
    },
    "cyanocobalamin vitamin b12": {
        "aliases": ["Vitamin B12", "Cobalamin"],
        "product_category": ["Vitamins"],
    },
    "vitamin b12": {
        "aliases": ["Cyanocobalamin", "Methylcobalamin", "Cobalamin"],
        "product_category": ["Vitamins"],
    },
    "vitamin b12 cyanocobalamin": {
        "aliases": ["Cyanocobalamin", "Cobalamin"],
        "product_category": ["Vitamins"],
    },
    "vitamin b12 methylcobalamin": {
        "aliases": ["Methylcobalamin", "MeCbl"],
        "product_category": ["Vitamins"],
    },
    "folate": {
        "aliases": ["Folic Acid", "Vitamin B9", "Pteroylglutamic Acid"],
        "product_category": ["Vitamins"],
    },
    "folic acid": {
        "aliases": ["Folate", "Vitamin B9", "Pteroylglutamic Acid"],
        "product_category": ["Vitamins"],
    },
    "niacin": {
        "aliases": ["Vitamin B3", "Nicotinic Acid", "Niacinamide"],
        "product_category": ["Vitamins"],
    },
    "niacinamide": {
        "aliases": ["Nicotinamide", "Vitamin B3", "Niacin Amide"],
        "product_category": ["Vitamins"],
    },
    "niacinamide vitamin b3": {
        "aliases": ["Nicotinamide", "Vitamin B3"],
        "product_category": ["Vitamins"],
    },
    "nicotinamide": {
        "aliases": ["Niacinamide", "Vitamin B3", "Nicotinic Acid Amide"],
        "product_category": ["Vitamins"],
    },
    "pantothenic acid": {
        "aliases": ["Vitamin B5", "D-Pantothenic Acid"],
        "product_category": ["Vitamins"],
    },
    "d calcium pantothenate": {
        "aliases": ["Calcium Pantothenate", "Vitamin B5", "Pantothenic Acid"],
        "product_category": ["Vitamins", "Minerals"],
    },
    "calcium pantothenate vitamin b5": {
        "aliases": ["D-Calcium Pantothenate", "Vitamin B5"],
        "product_category": ["Vitamins", "Minerals"],
    },
    "calcium d pantothenate": {
        "aliases": ["D-Calcium Pantothenate", "Vitamin B5"],
        "product_category": ["Vitamins", "Minerals"],
    },
    "vitamin b5 d calcium pantothenate": {
        "aliases": ["D-Calcium Pantothenate", "Pantothenic Acid"],
        "product_category": ["Vitamins"],
    },
    "pyridoxine hcl": {
        "aliases": ["Pyridoxine Hydrochloride", "Vitamin B6", "Pyridoxine HCl"],
        "product_category": ["Vitamins"],
    },
    "pyridoxine hydrochloride": {
        "aliases": ["Pyridoxine HCl", "Vitamin B6"],
        "product_category": ["Vitamins"],
    },
    "pyridoxine hydrochloride vitamin b6": {
        "aliases": ["Pyridoxine HCl", "Vitamin B6"],
        "product_category": ["Vitamins"],
    },
    "vitamin b6": {
        "aliases": ["Pyridoxine", "Pyridoxal", "Pyridoxamine"],
        "product_category": ["Vitamins"],
    },
    "vitamin b6 pyridoxal 5 phosphate": {
        "aliases": ["P-5-P", "Pyridoxal-5-Phosphate", "PLP"],
        "product_category": ["Vitamins"],
    },
    "vitamin b6 pyridoxine hydrochloride": {
        "aliases": ["Pyridoxine HCl", "Vitamin B6"],
        "product_category": ["Vitamins"],
    },
    "retinyl acetate": {
        "aliases": ["Vitamin A Acetate", "Retinol Acetate"],
        "product_category": ["Vitamins"],
    },
    "retinyl palmitate vitamin a": {
        "aliases": ["Vitamin A Palmitate", "Retinol Palmitate"],
        "product_category": ["Vitamins"],
    },
    "vitamin a": {
        "aliases": ["Retinol", "Retinyl Palmitate", "Beta-Carotene"],
        "product_category": ["Vitamins"],
    },
    "vitamin a acetate": {
        "aliases": ["Retinyl Acetate", "Retinol Acetate"],
        "product_category": ["Vitamins"],
    },
    "vitamin a palmitate": {
        "aliases": ["Retinyl Palmitate", "Vitamin A Ester"],
        "product_category": ["Vitamins"],
    },
    "vitamin a retinyl palmitate": {
        "aliases": ["Retinyl Palmitate", "Retinol Palmitate"],
        "product_category": ["Vitamins"],
    },
    "riboflavin": {
        "aliases": ["Vitamin B2", "Riboflavine", "E101"],
        "product_category": ["Vitamins"],
    },
    "vitamin b2": {
        "aliases": ["Riboflavin", "Riboflavine"],
        "product_category": ["Vitamins"],
    },
    "thiamin": {
        "aliases": ["Thiamine", "Vitamin B1", "Aneurin"],
        "product_category": ["Vitamins"],
    },
    "thiamine": {
        "aliases": ["Thiamin", "Vitamin B1", "Aneurin"],
        "product_category": ["Vitamins"],
    },
    "thiamine hcl": {
        "aliases": ["Thiamine Hydrochloride", "Vitamin B1 HCl"],
        "product_category": ["Vitamins"],
    },
    "thiamine mononitrate": {
        "aliases": ["Vitamin B1 Mononitrate", "Thiamin Mononitrate"],
        "product_category": ["Vitamins"],
    },
    "vitamin b1": {
        "aliases": ["Thiamine", "Thiamin", "Aneurin"],
        "product_category": ["Vitamins"],
    },
    "vitamin b3 niacinamide": {
        "aliases": ["Nicotinamide", "Niacinamide"],
        "product_category": ["Vitamins"],
    },
    "vitamin e": {
        "aliases": ["Tocopherol", "Alpha-Tocopherol", "d-Alpha Tocopherol"],
        "product_category": ["Vitamins", "Antioxidants"],
    },
    "vitamin e alpha tocopherol": {
        "aliases": ["d-Alpha Tocopherol", "Alpha-Tocopherol"],
        "product_category": ["Vitamins", "Antioxidants"],
    },
    "vitamin e d alpha tocopheryl": {
        "aliases": ["d-Alpha Tocopheryl", "Natural Vitamin E"],
        "product_category": ["Vitamins", "Antioxidants"],
    },
    "d alpha tocopheryl acetate vitamin e": {
        "aliases": ["d-Alpha Tocopheryl Acetate", "Natural Vitamin E Acetate"],
        "product_category": ["Vitamins", "Antioxidants"],
    },
    "d alpha tocopheryl succinate": {
        "aliases": ["d-Alpha Tocopheryl Succinate", "Vitamin E Succinate"],
        "product_category": ["Vitamins", "Antioxidants"],
    },
    "dl alpha tocopherol": {
        "aliases": ["dl-Alpha-Tocopherol", "Synthetic Vitamin E"],
        "product_category": ["Vitamins", "Antioxidants"],
    },
    "dl alpha tocopheryl acetate": {
        "aliases": ["dl-Alpha-Tocopheryl Acetate", "Synthetic Vitamin E"],
        "product_category": ["Vitamins", "Antioxidants"],
    },
    "tocopherols": {
        "aliases": ["Mixed Tocopherols", "Vitamin E Complex", "E306"],
        "product_category": ["Vitamins", "Antioxidants", "Excipients"],
    },
    "vitamin k": {
        "aliases": ["Phylloquinone", "Menaquinone", "Phytonadione"],
        "product_category": ["Vitamins"],
    },
    "vitamin k1": {
        "aliases": ["Phylloquinone", "Phytonadione", "K1"],
        "product_category": ["Vitamins"],
    },
    "vitamin k2": {
        "aliases": ["Menaquinone", "MK-7", "MK-4"],
        "product_category": ["Vitamins"],
    },
    "vitamin k2 menaquinone 7": {
        "aliases": ["MK-7", "Menaquinone-7", "Natto-K2"],
        "product_category": ["Vitamins"],
    },
    "phytonadione": {
        "aliases": ["Vitamin K1", "Phylloquinone", "K1"],
        "product_category": ["Vitamins"],
    },
    "b vitamins": {
        "aliases": ["B Complex", "B-Complex Vitamins", "Vitamin B Complex"],
        "product_category": ["Vitamins"],
    },
    "inositol": {
        "aliases": ["Myo-Inositol", "Cyclohexanehexol", "Vitamin B8"],
        "product_category": ["Vitamins", "Nutraceuticals"],
    },
    "choline bitartrate": {
        "aliases": ["Choline", "Choline Hydrogen Tartrate"],
        "product_category": ["Vitamins", "Nootropics"],
    },
    "para amino benzoic acid": {
        "aliases": ["PABA", "4-Aminobenzoic Acid", "Vitamin Bx"],
        "product_category": ["Vitamins", "Antioxidants"],
    },
    # --- Minerals ---
    "calcium": {
        "aliases": ["Ca", "Calcium Ion"],
        "product_category": ["Minerals"],
    },
    "calcium carbonate": {
        "aliases": ["Chalk", "Limestone", "CaCO3", "E170"],
        "product_category": ["Minerals", "Excipients"],
    },
    "calcium citrate": {
        "aliases": ["Tricalcium Dicitrate", "Calcium Citrate Tetrahydrate"],
        "product_category": ["Minerals"],
    },
    "calcium lactate gluconate": {
        "aliases": ["CLG", "Calcium Salt of Lactic and Gluconic Acid"],
        "product_category": ["Minerals"],
    },
    "dibasic calcium phosphate dihydrate": {
        "aliases": ["DCP", "Dicalcium Phosphate Dihydrate", "DCPD"],
        "product_category": ["Minerals", "Excipients"],
    },
    "dicalcium phosphate": {
        "aliases": ["DCP", "Dibasic Calcium Phosphate", "E341"],
        "product_category": ["Minerals", "Excipients"],
    },
    "tricalcium phosphate": {
        "aliases": ["TCP", "Tribasic Calcium Phosphate", "E341(iii)"],
        "product_category": ["Minerals", "Excipients"],
    },
    "boron": {
        "aliases": ["B", "Elemental Boron"],
        "product_category": ["Minerals", "Trace Elements"],
    },
    "boron amino acid chelate": {
        "aliases": ["Chelated Boron"],
        "product_category": ["Minerals", "Trace Elements"],
    },
    "boron calcium fructoborate": {
        "aliases": ["FruiteX-B", "Calcium Fructoborate"],
        "product_category": ["Minerals", "Trace Elements"],
    },
    "chloride": {
        "aliases": ["Cl-", "Chloride Ion"],
        "product_category": ["Minerals", "Electrolytes"],
    },
    "chromium": {
        "aliases": ["Cr", "Chromium Ion"],
        "product_category": ["Minerals", "Trace Elements"],
    },
    "chromium chloride": {
        "aliases": ["Chromic Chloride", "CrCl3"],
        "product_category": ["Minerals", "Trace Elements"],
    },
    "chromium nicotinate": {
        "aliases": ["Chromium Niacinate", "Chromium Polynicotinate"],
        "product_category": ["Minerals", "Trace Elements"],
    },
    "chromium picolinate": {
        "aliases": ["Chromium Picolinate", "Cr Picolinate"],
        "product_category": ["Minerals", "Trace Elements"],
    },
    "copper": {
        "aliases": ["Cu", "Cupric Ion"],
        "product_category": ["Minerals", "Trace Elements"],
    },
    "copper sulfate": {
        "aliases": ["Cupric Sulfate", "CuSO4", "Blue Vitriol"],
        "product_category": ["Minerals", "Trace Elements"],
    },
    "cupric oxide": {
        "aliases": ["Copper(II) Oxide", "CuO"],
        "product_category": ["Minerals", "Trace Elements"],
    },
    "cupric sulfate": {
        "aliases": ["Copper Sulfate", "CuSO4"],
        "product_category": ["Minerals", "Trace Elements"],
    },
    "iodine": {
        "aliases": ["I", "I2", "Elemental Iodine"],
        "product_category": ["Minerals", "Trace Elements"],
    },
    "potassium iodide": {
        "aliases": ["KI", "Iodide Salt"],
        "product_category": ["Minerals", "Trace Elements"],
    },
    "kelp extract": {
        "aliases": ["Seaweed Extract", "Brown Algae Extract", "Iodine Source"],
        "product_category": ["Botanical Extracts", "Minerals"],
    },
    "iron": {
        "aliases": ["Fe", "Ferrous Ion"],
        "product_category": ["Minerals"],
    },
    "ferrous fumarate": {
        "aliases": ["Iron Fumarate", "Ferrous(II) Fumarate"],
        "product_category": ["Minerals"],
    },
    "iron glycinate": {
        "aliases": ["Ferrous Bisglycinate", "Iron Bis-Glycinate Chelate"],
        "product_category": ["Minerals"],
    },
    "magnesium": {
        "aliases": ["Mg", "Magnesium Ion"],
        "product_category": ["Minerals"],
    },
    "magnesium amino acid chelate": {
        "aliases": ["Chelated Magnesium", "Albion Magnesium"],
        "product_category": ["Minerals"],
    },
    "magnesium aspartate": {
        "aliases": ["Magnesium L-Aspartate"],
        "product_category": ["Minerals"],
    },
    "magnesium bisglycinate": {
        "aliases": [
            "Magnesium Glycinate",
            "Magnesium Bis-Glycinate",
            "Chelated Magnesium",
        ],
        "product_category": ["Minerals"],
    },
    "magnesium carbonate": {
        "aliases": ["MgCO3", "Basic Magnesium Carbonate", "E504"],
        "product_category": ["Minerals", "Excipients"],
    },
    "magnesium citrate": {
        "aliases": ["Trimagnesium Dicitrate", "Magnesium Citrate Salt"],
        "product_category": ["Minerals"],
    },
    "magnesium dimagnesium malate": {
        "aliases": ["Dimagnesium Malate", "Magnesium Malate"],
        "product_category": ["Minerals"],
    },
    "magnesium glycinate": {
        "aliases": [
            "Magnesium Bisglycinate",
            "Chelated Magnesium",
            "Magnesium Diglycinate",
        ],
        "product_category": ["Minerals"],
    },
    "magnesium l threonate magtein": {
        "aliases": ["Magtein", "Magnesium L-Threonate", "MgT"],
        "product_category": ["Minerals", "Nootropics"],
    },
    "magnesium malate": {
        "aliases": ["Magnesium Dihydrogen Malate", "Magnesium Apple Malate"],
        "product_category": ["Minerals"],
    },
    "magnesium oxide": {
        "aliases": ["MgO", "Magnesia", "Periclase"],
        "product_category": ["Minerals", "Excipients"],
    },
    "magnesium silicate": {
        "aliases": ["Talc", "Magnesium Trisilicate", "E553"],
        "product_category": ["Excipients", "Minerals"],
    },
    "magnesium stearate": {
        "aliases": ["Magnesium Salt of Stearic Acid", "E572"],
        "product_category": ["Excipients", "Lubricants"],
    },
    "magnesium taurate": {
        "aliases": ["Magnesium Ditaurate"],
        "product_category": ["Minerals"],
    },
    "magnesium taurinate": {
        "aliases": ["Magnesium Taurate", "Taurine-Magnesium Complex"],
        "product_category": ["Minerals"],
    },
    "manganese": {
        "aliases": ["Mn", "Manganese Ion"],
        "product_category": ["Minerals", "Trace Elements"],
    },
    "manganese chelate": {
        "aliases": ["Chelated Manganese", "Manganese Amino Acid Chelate"],
        "product_category": ["Minerals", "Trace Elements"],
    },
    "manganese citrate": {
        "aliases": ["Manganese(II) Citrate"],
        "product_category": ["Minerals", "Trace Elements"],
    },
    "manganese sulfate": {
        "aliases": ["MnSO4", "Manganese(II) Sulfate"],
        "product_category": ["Minerals", "Trace Elements"],
    },
    "molybdenum": {
        "aliases": ["Mo", "Molybdenum Ion"],
        "product_category": ["Minerals", "Trace Elements"],
    },
    "sodium molybdate": {
        "aliases": ["Disodium Molybdate", "Na2MoO4"],
        "product_category": ["Minerals", "Trace Elements"],
    },
    "potassium": {
        "aliases": ["K", "Potassium Ion"],
        "product_category": ["Minerals", "Electrolytes"],
    },
    "potassium alginate": {
        "aliases": ["Algin", "E402"],
        "product_category": ["Minerals", "Gums", "Excipients"],
    },
    "potassium aspartate": {
        "aliases": ["Potassium L-Aspartate"],
        "product_category": ["Minerals", "Electrolytes"],
    },
    "potassium chloride": {
        "aliases": ["KCl", "Muriate of Potash", "E508"],
        "product_category": ["Minerals", "Electrolytes"],
    },
    "potassium citrate": {
        "aliases": ["Tripotassium Citrate", "E332"],
        "product_category": ["Minerals", "Electrolytes", "Excipients"],
    },
    "potassium gluconate": {
        "aliases": ["Potassium D-Gluconate"],
        "product_category": ["Minerals", "Electrolytes"],
    },
    "potassium phosphate": {
        "aliases": ["Dipotassium Phosphate", "DKP", "E340"],
        "product_category": ["Minerals", "Excipients"],
    },
    "dipotassium phosphate": {
        "aliases": ["DKP", "Potassium Phosphate Dibasic", "E340(ii)"],
        "product_category": ["Minerals", "Excipients"],
    },
    "selenium": {
        "aliases": ["Se", "Selenium Ion"],
        "product_category": ["Minerals", "Trace Elements", "Antioxidants"],
    },
    "sodium selenite": {
        "aliases": ["Disodium Selenite", "Na2SeO3"],
        "product_category": ["Minerals", "Trace Elements"],
    },
    "sodium": {
        "aliases": ["Na", "Sodium Ion"],
        "product_category": ["Minerals", "Electrolytes"],
    },
    "sodium chloride": {
        "aliases": ["Table Salt", "NaCl", "E508"],
        "product_category": ["Minerals", "Electrolytes"],
    },
    "sodium citrate": {
        "aliases": ["Trisodium Citrate", "E331"],
        "product_category": ["Minerals", "Excipients", "Food Additives"],
    },
    "sodium alginate": {
        "aliases": ["Algin", "E401", "Sodium Salt of Alginic Acid"],
        "product_category": ["Gums", "Excipients"],
    },
    "vanadium as vanadyl sulfate": {
        "aliases": ["Vanadyl Sulfate", "VOSO4", "Vanadium Sulfate"],
        "product_category": ["Minerals", "Trace Elements"],
    },
    "zinc": {
        "aliases": ["Zn", "Zinc Ion"],
        "product_category": ["Minerals"],
    },
    "zinc chelate": {
        "aliases": ["Chelated Zinc", "Zinc Amino Acid Chelate"],
        "product_category": ["Minerals"],
    },
    "zinc citrate": {
        "aliases": ["Zinc(II) Citrate"],
        "product_category": ["Minerals"],
    },
    "zinc oxide": {
        "aliases": ["ZnO", "Zinc White"],
        "product_category": ["Minerals", "Excipients"],
    },
    "zinc sulfate": {
        "aliases": ["ZnSO4", "Zinc Vitriol"],
        "product_category": ["Minerals"],
    },
    "zinc zinc bisglycinate": {
        "aliases": ["Zinc Bisglycinate", "Zinc Glycinate Chelate"],
        "product_category": ["Minerals"],
    },
    "boron": {
        "aliases": ["B", "Elemental Boron"],
        "product_category": ["Minerals", "Trace Elements"],
    },
    "sulfate": {
        "aliases": ["Sulphate", "SO4"],
        "product_category": ["Minerals"],
    },
    "concentrace trace minerals": {
        "aliases": ["Trace Mineral Concentrate", "ConcenTrace"],
        "product_category": ["Minerals", "Trace Elements"],
    },
    "trace mineral concentrate": {
        "aliases": ["ConcenTrace", "Trace Minerals Concentrate"],
        "product_category": ["Minerals", "Trace Elements"],
    },
    "kalahari desert salt": {
        "aliases": ["Desert Salt", "African Salt"],
        "product_category": ["Minerals", "Electrolytes", "Food Additives"],
    },
    "pink himalayan salt": {
        "aliases": ["Himalayan Pink Salt", "Himalayan Rock Salt"],
        "product_category": ["Minerals", "Electrolytes", "Food Additives"],
    },
    "salt": {
        "aliases": ["Sodium Chloride", "NaCl", "Table Salt"],
        "product_category": ["Minerals", "Electrolytes", "Food Additives"],
    },
    "salt sodium chloride": {
        "aliases": ["NaCl", "Table Salt", "Sea Salt"],
        "product_category": ["Minerals", "Electrolytes", "Food Additives"],
    },
    "sea salt": {
        "aliases": ["Marine Salt", "Sea Mineral Salt"],
        "product_category": ["Minerals", "Electrolytes", "Food Additives"],
    },
    # --- Proteins ---
    "collagen peptides": {
        "aliases": [
            "Hydrolyzed Collagen",
            "Collagen Hydrolysate",
            "Gelatin Hydrolysate",
        ],
        "product_category": ["Proteins", "Nutraceuticals"],
    },
    "brown rice protein": {
        "aliases": ["Rice Protein Concentrate", "Brown Rice Protein Isolate"],
        "product_category": ["Proteins", "Plant Proteins", "Sports Nutrition"],
    },
    "grass fed whey protein concentrate": {
        "aliases": ["Grass-Fed WPC", "Whey Protein Concentrate", "WPC80"],
        "product_category": ["Proteins", "Sports Nutrition"],
    },
    "hemp seed protein": {
        "aliases": ["Hemp Protein", "Cannabis Sativa Protein"],
        "product_category": ["Proteins", "Plant Proteins"],
    },
    "hydrolyzed whey protein": {
        "aliases": ["WPH", "Whey Protein Hydrolysate", "Pre-Digested Whey"],
        "product_category": ["Proteins", "Sports Nutrition"],
    },
    "milk protein": {
        "aliases": ["Milk Protein Concentrate", "MPC", "Casein/Whey Blend"],
        "product_category": ["Proteins", "Dairy"],
    },
    "organic dairy whey protein concentrate": {
        "aliases": ["Organic WPC", "Organic Whey Protein"],
        "product_category": ["Proteins", "Sports Nutrition"],
    },
    "organic whey protein": {
        "aliases": ["Organic Whey", "Organic WPC"],
        "product_category": ["Proteins", "Sports Nutrition"],
    },
    "pea protein": {
        "aliases": ["Pea Protein Isolate", "PPI", "Yellow Pea Protein"],
        "product_category": ["Proteins", "Plant Proteins", "Sports Nutrition"],
    },
    "pumpkin seed protein": {
        "aliases": ["Pumpkin Protein", "Cucurbita Protein"],
        "product_category": ["Proteins", "Plant Proteins"],
    },
    "rice protein": {
        "aliases": ["Rice Protein Concentrate", "Brown Rice Protein"],
        "product_category": ["Proteins", "Plant Proteins"],
    },
    "whey protein concentrate": {
        "aliases": ["WPC", "WPC80", "Whey Concentrate"],
        "product_category": ["Proteins", "Sports Nutrition"],
    },
    "whey protein isolate": {
        "aliases": ["WPI", "Whey Isolate", "WPI90"],
        "product_category": ["Proteins", "Sports Nutrition"],
    },
    # --- Amino Acids ---
    "l isoleucine": {
        "aliases": ["Isoleucine", "L-Ile", "BCAA"],
        "product_category": ["Amino Acids", "Sports Nutrition"],
    },
    "l leucine": {
        "aliases": ["Leucine", "L-Leu", "BCAA"],
        "product_category": ["Amino Acids", "Sports Nutrition"],
    },
    "l valine": {
        "aliases": ["Valine", "L-Val", "BCAA"],
        "product_category": ["Amino Acids", "Sports Nutrition"],
    },
    "leucine": {
        "aliases": ["L-Leucine", "L-Leu", "BCAA"],
        "product_category": ["Amino Acids", "Sports Nutrition"],
    },
    "taurine": {
        "aliases": ["2-Aminoethanesulfonic Acid", "Taurine Amino Acid"],
        "product_category": ["Amino Acids", "Nutraceuticals"],
    },
    "bcaas": {
        "aliases": ["Branched Chain Amino Acids", "BCAA", "Leucine Isoleucine Valine"],
        "product_category": ["Amino Acids", "Sports Nutrition"],
    },
    # --- Oils / Lipids ---
    "coconut mct oil": {
        "aliases": ["MCT Oil", "Medium Chain Triglycerides", "C8/C10 Oil"],
        "product_category": ["Oils", "Lipids", "Sports Nutrition"],
    },
    "corn oil": {
        "aliases": ["Maize Oil", "Zea Mays Oil"],
        "product_category": ["Oils", "Lipids"],
    },
    "medium chain triglycerides": {
        "aliases": ["MCT Oil", "MCTs", "C8/C10 Triglycerides"],
        "product_category": ["Oils", "Lipids", "Sports Nutrition"],
    },
    "medium chain triglycerides mct from coconut oil": {
        "aliases": ["Coconut MCT", "MCT Oil", "C8/C10 Oil"],
        "product_category": ["Oils", "Lipids", "Sports Nutrition"],
    },
    "olive oil": {
        "aliases": ["Olea Europaea Oil", "Extra Virgin Olive Oil"],
        "product_category": ["Oils", "Lipids"],
    },
    "palm oil": {
        "aliases": ["Elaeis Guineensis Oil", "Red Palm Oil"],
        "product_category": ["Oils", "Lipids"],
    },
    "safflower oil": {
        "aliases": ["Carthamus Tinctorius Oil", "High-Oleic Safflower Oil"],
        "product_category": ["Oils", "Lipids"],
    },
    "soybean oil": {
        "aliases": ["Soya Oil", "Soy Oil"],
        "product_category": ["Oils", "Lipids"],
    },
    "sunflower oil": {
        "aliases": ["Helianthus Annuus Seed Oil", "High-Oleic Sunflower Oil"],
        "product_category": ["Oils", "Lipids"],
    },
    "omega 3 dha": {
        "aliases": ["DHA", "Docosahexaenoic Acid", "Omega-3"],
        "product_category": ["Oils", "Lipids", "Nutraceuticals"],
    },
    "oil fill": {
        "aliases": ["Carrier Oil", "Oil Matrix"],
        "product_category": ["Oils", "Excipients"],
    },
    "blend of oils coconut and or palm with beeswax and or carnauba w": {
        "aliases": ["Oil/Wax Blend", "Coating Blend"],
        "product_category": ["Oils", "Excipients"],
    },
    # --- Sweeteners ---
    "acesulfame potassium": {
        "aliases": ["Acesulfame K", "Ace-K", "E950"],
        "product_category": ["Sweeteners", "Artificial Sweeteners", "Food Additives"],
    },
    "anhydrous dextrose": {
        "aliases": ["Dextrose Anhydrous", "D-Glucose Anhydrous", "Corn Sugar"],
        "product_category": ["Sweeteners", "Carbohydrates"],
    },
    "cane sugar": {
        "aliases": ["Sucrose", "Refined Sugar", "White Sugar"],
        "product_category": ["Sweeteners", "Carbohydrates"],
    },
    "coconut sugar": {
        "aliases": ["Coconut Palm Sugar", "Coco Sugar"],
        "product_category": ["Sweeteners", "Natural Sweeteners", "Carbohydrates"],
    },
    "coconut water from concentrate": {
        "aliases": ["Coconut Water Concentrate", "Coconut Juice Concentrate"],
        "product_category": ["Sweeteners", "Natural Flavors", "Nutraceuticals"],
    },
    "coconut water powder": {
        "aliases": ["Spray-Dried Coconut Water", "Coconut Water Extract"],
        "product_category": ["Sweeteners", "Electrolytes", "Nutraceuticals"],
    },
    "dextrose": {
        "aliases": ["D-Glucose", "Corn Sugar", "Glucose Monohydrate"],
        "product_category": ["Sweeteners", "Carbohydrates"],
    },
    "glucose": {
        "aliases": ["Dextrose", "Blood Sugar", "D-Glucose"],
        "product_category": ["Sweeteners", "Carbohydrates"],
    },
    "monk fruit extract": {
        "aliases": ["Luo Han Guo Extract", "Mogroside V", "SGF Extract"],
        "product_category": ["Sweeteners", "Natural Sweeteners"],
    },
    "organic cane sugar": {
        "aliases": ["Organic Sucrose", "Organic Cane Juice"],
        "product_category": ["Sweeteners", "Carbohydrates"],
    },
    "organic erythritol": {
        "aliases": ["Erythritol", "E968", "Sugar Alcohol"],
        "product_category": ["Sweeteners", "Natural Sweeteners"],
    },
    "organic stevia": {
        "aliases": ["Stevia Leaf Extract", "Rebaudioside A", "Steviol Glycoside"],
        "product_category": ["Sweeteners", "Natural Sweeteners"],
    },
    "organic stevia extract": {
        "aliases": ["Rebaudioside A", "Steviol Glycoside", "Reb A"],
        "product_category": ["Sweeteners", "Natural Sweeteners"],
    },
    "organic stevia extract leaf": {
        "aliases": ["Reb A", "Rebaudioside A"],
        "product_category": ["Sweeteners", "Natural Sweeteners"],
    },
    "organic stevia leaf extract rebaudioside a": {
        "aliases": ["Reb A", "Steviol Glycoside"],
        "product_category": ["Sweeteners", "Natural Sweeteners"],
    },
    "pure cane sugar": {
        "aliases": ["Sucrose", "Refined Cane Sugar"],
        "product_category": ["Sweeteners", "Carbohydrates"],
    },
    "rebaudioside a": {
        "aliases": ["Reb A", "Stevia Extract", "E960"],
        "product_category": ["Sweeteners", "Natural Sweeteners"],
    },
    "sorbitol": {
        "aliases": ["Glucitol", "E420", "Sorbitol Powder"],
        "product_category": ["Sweeteners", "Sugar Alcohols", "Excipients"],
    },
    "stevia": {
        "aliases": ["Stevia Leaf Extract", "Rebaudioside A", "Steviol Glycoside"],
        "product_category": ["Sweeteners", "Natural Sweeteners"],
    },
    "stevia leaf extract": {
        "aliases": ["Reb A", "Rebaudioside A", "E960"],
        "product_category": ["Sweeteners", "Natural Sweeteners"],
    },
    "stevia leaf extract rebaudioside a": {
        "aliases": ["Reb A", "Steviol Glycoside"],
        "product_category": ["Sweeteners", "Natural Sweeteners"],
    },
    "stevia or sucralose sweetener": {
        "aliases": ["Sweetener Blend", "Low-Calorie Sweetener"],
        "product_category": ["Sweeteners"],
    },
    "sucralose": {
        "aliases": ["Splenda", "E955", "Trichlorogalactosucrose"],
        "product_category": ["Sweeteners", "Artificial Sweeteners"],
    },
    "sucrose": {
        "aliases": ["Sugar", "Table Sugar", "Beet Sugar"],
        "product_category": ["Sweeteners", "Carbohydrates"],
    },
    "sugar": {
        "aliases": ["Sucrose", "Granulated Sugar", "Table Sugar"],
        "product_category": ["Sweeteners", "Carbohydrates"],
    },
    "tapioca syrup": {
        "aliases": ["Cassava Syrup", "Tapioca Glucose Syrup"],
        "product_category": ["Sweeteners", "Carbohydrates"],
    },
    # --- Excipients / Tableting / Encapsulation ---
    "bone gelatin bovine": {
        "aliases": ["Bovine Gelatin", "Beef Gelatin", "Type B Gelatin"],
        "product_category": ["Excipients", "Encapsulation"],
    },
    "carboxymethylcellulose sodium": {
        "aliases": ["Sodium CMC", "CMC", "E466"],
        "product_category": ["Excipients", "Gums"],
    },
    "carnauba wax": {
        "aliases": ["Brazil Wax", "Carnuba Wax", "E903"],
        "product_category": ["Excipients", "Coatings"],
    },
    "cellulose": {
        "aliases": ["Microcrystalline Cellulose", "MCC", "Plant Cellulose"],
        "product_category": ["Excipients"],
    },
    "cellulose gel": {
        "aliases": ["Microcrystalline Cellulose Gel", "Avicel Gel"],
        "product_category": ["Excipients"],
    },
    "cellulose gum": {
        "aliases": ["CMC", "Carboxymethyl Cellulose", "E466"],
        "product_category": ["Excipients", "Gums"],
    },
    "croscarmellose sodium": {
        "aliases": ["Ac-Di-Sol", "Cross-linked Carboxymethyl Cellulose Sodium", "E468"],
        "product_category": ["Excipients", "Disintegrants"],
    },
    "gelatin": {
        "aliases": ["Gelatine", "Collagen Protein", "E441"],
        "product_category": ["Excipients", "Encapsulation"],
    },
    "gelatin capsule": {
        "aliases": ["Hard Gelatin Capsule", "HGC"],
        "product_category": ["Excipients", "Encapsulation"],
    },
    "gelatin capsule bovine": {
        "aliases": ["Bovine Hard Gelatin Capsule", "Beef Gelatin Capsule"],
        "product_category": ["Excipients", "Encapsulation"],
    },
    "soft gel capsule bovine gelatin": {
        "aliases": ["Bovine Softgel", "Soft Gelatin Capsule"],
        "product_category": ["Excipients", "Encapsulation"],
    },
    "softgel bovine gelatin": {
        "aliases": ["Bovine Softgel", "Soft Gelatin Capsule"],
        "product_category": ["Excipients", "Encapsulation"],
    },
    "softgel capsule bovine gelatin": {
        "aliases": ["Bovine Softgel", "Soft Gel Capsule"],
        "product_category": ["Excipients", "Encapsulation"],
    },
    "hypromellose": {
        "aliases": ["HPMC", "Hydroxypropyl Methylcellulose", "E464"],
        "product_category": ["Excipients", "Encapsulation"],
    },
    "hydroxypropyl methyl cellulose": {
        "aliases": ["HPMC", "Hypromellose", "E464"],
        "product_category": ["Excipients", "Encapsulation"],
    },
    "hydroxypropyl methylcellulose": {
        "aliases": ["HPMC", "Hypromellose", "E464"],
        "product_category": ["Excipients", "Encapsulation"],
    },
    "hydroxypropylmethylcellulose": {
        "aliases": ["HPMC", "Hypromellose", "E464"],
        "product_category": ["Excipients", "Encapsulation"],
    },
    "hypromellose capsule": {
        "aliases": ["HPMC Capsule", "Vegetarian Capsule", "Vegan Capsule"],
        "product_category": ["Excipients", "Encapsulation"],
    },
    "lac resin": {
        "aliases": ["Shellac", "Pharmaceutical Glaze", "E904"],
        "product_category": ["Excipients", "Coatings"],
    },
    "pharmaceutical glaze": {
        "aliases": ["Shellac Glaze", "Lac Resin", "E904"],
        "product_category": ["Excipients", "Coatings"],
    },
    "microcrystalline cellulose": {
        "aliases": ["MCC", "Avicel", "E460(i)"],
        "product_category": ["Excipients"],
    },
    "modified cellulose": {
        "aliases": ["Cellulose Derivative", "Modified Cellulose Gum"],
        "product_category": ["Excipients"],
    },
    "modified food starch": {
        "aliases": ["Modified Starch", "E1400-E1450"],
        "product_category": ["Excipients", "Starches"],
    },
    "pea starch": {
        "aliases": ["Pisum Sativum Starch", "Pea Flour Starch"],
        "product_category": ["Excipients", "Starches"],
    },
    "rice bran": {
        "aliases": ["Rice Bran Extract", "Oryzanol Source"],
        "product_category": ["Excipients", "Nutraceuticals"],
    },
    "rice flour": {
        "aliases": ["Rice Powder", "Oryza Sativa Flour"],
        "product_category": ["Excipients", "Starches"],
    },
    "rice powder": {
        "aliases": ["Rice Flour", "Oryza Sativa Powder"],
        "product_category": ["Excipients", "Starches"],
    },
    "silicon dioxide": {
        "aliases": ["Silica", "SiO2", "E551"],
        "product_category": ["Excipients", "Anti-caking Agents"],
    },
    "silica": {
        "aliases": ["Silicon Dioxide", "SiO2", "E551"],
        "product_category": ["Excipients", "Anti-caking Agents"],
    },
    "sodium aluminum silicate": {
        "aliases": ["Sodium Aluminosilicate", "E554"],
        "product_category": ["Excipients", "Anti-caking Agents"],
    },
    "sodium starch glycolate": {
        "aliases": ["SSG", "Primojel", "Explotab"],
        "product_category": ["Excipients", "Disintegrants"],
    },
    "starch": {
        "aliases": ["Food Starch", "Maize Starch", "Corn Starch"],
        "product_category": ["Excipients", "Starches"],
    },
    "stearic acid": {
        "aliases": ["Octadecanoic Acid", "E570"],
        "product_category": ["Excipients", "Lubricants", "Lipids"],
    },
    "talc": {
        "aliases": ["Magnesium Silicate", "Soapstone", "E553b"],
        "product_category": ["Excipients", "Anti-caking Agents"],
    },
    "titanium dioxide": {
        "aliases": ["TiO2", "E171", "Pigment White 6"],
        "product_category": ["Excipients", "Colorants"],
    },
    "vegetable cellulose": {
        "aliases": ["Plant Cellulose", "HPMC", "Vegetable-Based Cellulose"],
        "product_category": ["Excipients", "Encapsulation"],
    },
    "vegetable glycerin": {
        "aliases": ["Vegetable Glycerol", "Plant-Based Glycerin"],
        "product_category": ["Excipients", "Humectants"],
    },
    "vegetable magnesium stearate": {
        "aliases": ["Veg Mag Stearate", "Plant-Based Magnesium Stearate"],
        "product_category": ["Excipients", "Lubricants"],
    },
    "vegetable stearic acid": {
        "aliases": ["Plant-Based Stearic Acid", "Veg Stearic Acid"],
        "product_category": ["Excipients", "Lubricants"],
    },
    "vegan capsule": {
        "aliases": ["HPMC Capsule", "Vegetarian Capsule", "Plant-Based Capsule"],
        "product_category": ["Excipients", "Encapsulation"],
    },
    "vegan capsule hypromellose": {
        "aliases": ["HPMC Vegan Capsule", "Plant-Based Capsule"],
        "product_category": ["Excipients", "Encapsulation"],
    },
    "vegetarian capsule": {
        "aliases": ["HPMC Capsule", "Vegan Capsule", "Plant-Based Capsule"],
        "product_category": ["Excipients", "Encapsulation"],
    },
    "plantgel capsule": {
        "aliases": ["Plant-Based Gel Capsule", "Seaweed Capsule"],
        "product_category": ["Excipients", "Encapsulation"],
    },
    "polyethylene glycol": {
        "aliases": ["PEG", "Macrogol", "E1521"],
        "product_category": ["Excipients", "Plasticizers"],
    },
    "polyvinyl alcohol": {
        "aliases": ["PVA", "E1203"],
        "product_category": ["Excipients", "Film Coatings"],
    },
    "polyvinylpolypyrrolidone": {
        "aliases": ["PVPP", "Crospovidone", "E1202"],
        "product_category": ["Excipients", "Disintegrants"],
    },
    "polysorbate 80": {
        "aliases": ["Tween 80", "E433", "Polyoxyethylene Sorbitan Monooleate"],
        "product_category": ["Excipients", "Emulsifiers"],
    },
    "polydextrose": {
        "aliases": ["Litesse", "E1200", "Poly-D-Glucose"],
        "product_category": ["Excipients", "Dietary Fiber", "Prebiotics"],
    },
    "sorbic acid": {
        "aliases": ["E200", "2,4-Hexadienoic Acid"],
        "product_category": ["Excipients", "Preservatives"],
    },
    "sodium benzoate": {
        "aliases": ["E211", "Sodium Salt of Benzoic Acid"],
        "product_category": ["Excipients", "Preservatives"],
    },
    "vegetable acetoglycerides": {
        "aliases": ["Acetylated Monoglycerides", "DATEM"],
        "product_category": ["Excipients", "Emulsifiers"],
    },
    "aqueous coating": {
        "aliases": ["Water-Based Coating", "Film Coat"],
        "product_category": ["Excipients", "Coatings"],
    },
    "organic coating": {
        "aliases": ["Organic Film Coat", "Natural Coating"],
        "product_category": ["Excipients", "Coatings"],
    },
    "gummy base": {
        "aliases": ["Gelatin Base", "Pectin Base", "Gummy Matrix"],
        "product_category": ["Excipients", "Encapsulation"],
    },
    "effervescent base": {
        "aliases": ["Citric Acid/Bicarbonate Blend", "Fizzy Base"],
        "product_category": ["Excipients", "Food Additives"],
    },
    "non gmo corn zein": {
        "aliases": ["Corn Zein", "Zein Protein", "Corn Prolamin"],
        "product_category": ["Excipients", "Coatings"],
    },
    # --- Gums / Hydrocolloids ---
    "acacia gum": {
        "aliases": ["Gum Arabic", "E414", "Acacia Senegal Gum"],
        "product_category": ["Gums", "Prebiotics", "Excipients"],
    },
    "carrageenan": {
        "aliases": ["Irish Moss Extract", "E407", "Carrageen"],
        "product_category": ["Gums", "Excipients"],
    },
    "gellan gum": {
        "aliases": ["E418", "Gellan", "Kelcogel"],
        "product_category": ["Gums", "Excipients"],
    },
    "gum acacia": {
        "aliases": ["Gum Arabic", "Acacia Gum", "E414"],
        "product_category": ["Gums", "Prebiotics", "Excipients"],
    },
    "gum arabic": {
        "aliases": ["Acacia Gum", "E414", "Acacia Senegal"],
        "product_category": ["Gums", "Prebiotics", "Excipients"],
    },
    "organic acacia": {
        "aliases": ["Organic Gum Arabic", "Organic Acacia Gum"],
        "product_category": ["Gums", "Prebiotics", "Excipients"],
    },
    "organic gum acacia": {
        "aliases": ["Organic Gum Arabic", "Organic Acacia"],
        "product_category": ["Gums", "Prebiotics", "Excipients"],
    },
    "xanthan gum": {
        "aliases": ["E415", "Xanthomonas Campestris Gum"],
        "product_category": ["Gums", "Excipients"],
    },
    # --- Dietary Fiber / Prebiotics ---
    "blue agave inulin": {
        "aliases": ["Agave Inulin", "Blue Agave Fiber"],
        "product_category": ["Prebiotics", "Dietary Fiber"],
    },
    "fructooligosaccharides": {
        "aliases": [
            "FOS",
            "Oligofructose",
            "E420 (incorrectly sometimes)",
            "Short-Chain FOS",
        ],
        "product_category": ["Prebiotics", "Dietary Fiber"],
    },
    "inulin": {
        "aliases": ["Chicory Inulin", "Oligofructose", "FOS"],
        "product_category": ["Prebiotics", "Dietary Fiber"],
    },
    "organic agave inulin powder": {
        "aliases": ["Agave Inulin", "Organic Agave Fiber"],
        "product_category": ["Prebiotics", "Dietary Fiber"],
    },
    "organic inulin": {
        "aliases": ["Organic Chicory Inulin", "Organic FOS"],
        "product_category": ["Prebiotics", "Dietary Fiber"],
    },
    "organic tapioca fiber imo": {
        "aliases": ["Isomalto-Oligosaccharides", "IMO", "Tapioca IMO"],
        "product_category": ["Prebiotics", "Dietary Fiber"],
    },
    "prebiotic fiber": {
        "aliases": ["Soluble Fiber", "Prebiotic", "Fermentable Fiber"],
        "product_category": ["Prebiotics", "Dietary Fiber"],
    },
    # --- Probiotics ---
    "bifidobacterium lactis bl 04": {
        "aliases": ["B. lactis BL-04", "Bifidobacterium animalis BL-04"],
        "product_category": ["Probiotics"],
    },
    "probiotic cultures": {
        "aliases": ["Live Active Cultures", "Beneficial Bacteria", "Lactobacillus"],
        "product_category": ["Probiotics"],
    },
    "cultured nutrients": {
        "aliases": ["Fermented Nutrients", "Probiotic Nutrients", "Postbiotics"],
        "product_category": ["Probiotics", "Nutraceuticals"],
    },
    "epicor postbiotic": {
        "aliases": ["EpiCor", "Saccharomyces Cerevisiae Fermentate", "Postbiotic"],
        "product_category": ["Probiotics", "Immune Support"],
    },
    # --- Botanical Extracts / Phytonutrients ---
    "alfalfa leaf": {
        "aliases": ["Medicago Sativa", "Lucerne Leaf", "Alfalfa Herb"],
        "product_category": ["Botanical Extracts", "Greens"],
    },
    "astaxanthin": {
        "aliases": ["Haematococcus Pluvialis Extract", "Keto-Carotenoid"],
        "product_category": ["Botanical Extracts", "Antioxidants", "Carotenoids"],
    },
    "beta carotene": {
        "aliases": ["Pro-Vitamin A", "Beta-Carotene", "E160a"],
        "product_category": ["Botanical Extracts", "Vitamins", "Carotenoids"],
    },
    "black pepper concentrate": {
        "aliases": ["Piperine", "BioPerine", "Piper Nigrum Extract"],
        "product_category": ["Botanical Extracts", "Bioavailability Enhancers"],
    },
    "citrus bioflavonoids": {
        "aliases": ["Citrus Flavonoids", "Hesperidin Complex", "Bioflavonoid Complex"],
        "product_category": ["Botanical Extracts", "Antioxidants"],
    },
    "coenzyme q10": {
        "aliases": ["CoQ10", "Ubiquinone", "Ubidecarenone"],
        "product_category": ["Nutraceuticals", "Antioxidants"],
    },
    "coq10": {
        "aliases": ["CoQ-10", "Ubiquinone", "Ubidecarenone"],
        "product_category": ["Nutraceuticals", "Antioxidants"],
    },
    "grape seed extract": {
        "aliases": ["GSE", "OPC", "Oligomeric Proanthocyanidins"],
        "product_category": ["Botanical Extracts", "Antioxidants"],
    },
    "green tea extract": {
        "aliases": ["EGCG", "Camellia Sinensis Extract", "Catechins"],
        "product_category": ["Botanical Extracts", "Antioxidants"],
    },
    "hesperidin complex": {
        "aliases": ["Hesperidin", "Citrus Bioflavonoid Complex"],
        "product_category": ["Botanical Extracts", "Antioxidants"],
    },
    "lemon bioflavonoid complex": {
        "aliases": ["Lemon Flavonoids", "Citrus Bioflavonoids"],
        "product_category": ["Botanical Extracts", "Antioxidants"],
    },
    "lutein": {
        "aliases": ["Marigold Extract", "Xanthophyll", "Tagetes Erecta Extract"],
        "product_category": ["Botanical Extracts", "Carotenoids", "Eye Health"],
    },
    "lycopene": {
        "aliases": ["Tomato Extract", "Red Carotenoid"],
        "product_category": ["Botanical Extracts", "Carotenoids", "Antioxidants"],
    },
    "pomegranate extract": {
        "aliases": ["Punica Granatum Extract", "Ellagic Acid Source"],
        "product_category": ["Botanical Extracts", "Antioxidants"],
    },
    "resveratrol": {
        "aliases": ["Trans-Resveratrol", "Polygonum Cuspidatum Extract"],
        "product_category": ["Botanical Extracts", "Antioxidants"],
    },
    "rhodiola rosea extract root": {
        "aliases": ["Rhodiola", "Golden Root", "Rosavin"],
        "product_category": ["Botanical Extracts", "Adaptogens"],
    },
    "rutin": {
        "aliases": ["Quercetin-3-Rutinoside", "Rutoside", "Bioflavonoid"],
        "product_category": ["Botanical Extracts", "Antioxidants"],
    },
    "zeaxanthin": {
        "aliases": ["Marigold Extract", "Carotenoid", "Zeaxanthine"],
        "product_category": ["Botanical Extracts", "Carotenoids", "Eye Health"],
    },
    "cinnamon": {
        "aliases": ["Cinnamomum Verum", "Ceylon Cinnamon", "Cassia"],
        "product_category": ["Botanical Extracts", "Food Additives"],
    },
    "organic ginger": {
        "aliases": ["Zingiber Officinale", "Ginger Root Extract"],
        "product_category": ["Botanical Extracts", "Food Additives"],
    },
    "organic turmeric": {
        "aliases": ["Curcuma Longa", "Curcumin Source"],
        "product_category": ["Botanical Extracts", "Anti-inflammatories"],
    },
    "organic pomegranate juice powder": {
        "aliases": ["Pomegranate Powder", "Punica Granatum Juice"],
        "product_category": ["Botanical Extracts", "Antioxidants"],
    },
    "organic rosemary extract": {
        "aliases": ["Rosmarinus Officinalis Extract", "Rosemary Antioxidant"],
        "product_category": ["Botanical Extracts", "Antioxidants", "Excipients"],
    },
    "aquamin mg soluble": {
        "aliases": ["Aquamin Magnesium", "Marine Magnesium"],
        "product_category": ["Minerals", "Botanical Extracts"],
    },
    # --- Flavors ---
    "artificial flavor": {
        "aliases": ["Artificial Flavoring", "Synthetic Flavor"],
        "product_category": ["Flavors", "Food Additives"],
    },
    "artificial flavors": {
        "aliases": ["Artificial Flavoring", "Synthetic Flavors"],
        "product_category": ["Flavors", "Food Additives"],
    },
    "natural and artificial flavors": {
        "aliases": ["N&A Flavors", "Natural and Artificial Flavoring"],
        "product_category": ["Flavors", "Food Additives"],
    },
    "natural cherry flavor": {
        "aliases": ["Cherry Flavoring", "Natural Cherry Flavoring"],
        "product_category": ["Flavors", "Natural Flavors"],
    },
    "natural flavor": {
        "aliases": ["Natural Flavoring", "FTNF"],
        "product_category": ["Flavors", "Natural Flavors"],
    },
    "natural flavors": {
        "aliases": ["Natural Flavoring", "WONF", "FTNF"],
        "product_category": ["Flavors", "Natural Flavors"],
    },
    "natural french vanilla flavor": {
        "aliases": ["Vanilla Flavor", "French Vanilla Flavoring"],
        "product_category": ["Flavors", "Natural Flavors"],
    },
    "natural lemon lime flavor": {
        "aliases": ["Lemon Lime Flavor", "Citrus Flavor"],
        "product_category": ["Flavors", "Natural Flavors"],
    },
    "natural passionfruit flavor": {
        "aliases": ["Passion Fruit Flavor", "Tropical Flavor"],
        "product_category": ["Flavors", "Natural Flavors"],
    },
    "natural peach flavor": {
        "aliases": ["Peach Flavoring", "Stone Fruit Flavor"],
        "product_category": ["Flavors", "Natural Flavors"],
    },
    "natural strawberry flavor": {
        "aliases": ["Strawberry Flavoring", "Berry Flavor"],
        "product_category": ["Flavors", "Natural Flavors"],
    },
    "natural tangerine flavor": {
        "aliases": ["Tangerine Flavoring", "Citrus Flavor"],
        "product_category": ["Flavors", "Natural Flavors"],
    },
    "natural vanilla": {
        "aliases": ["Vanilla Bean Extract", "Vanilla Flavoring", "Vanillin"],
        "product_category": ["Flavors", "Natural Flavors"],
    },
    "natural vanilla flavor": {
        "aliases": ["Vanilla Extract", "Vanilla Flavoring"],
        "product_category": ["Flavors", "Natural Flavors"],
    },
    "orange flavor": {
        "aliases": ["Orange Flavoring", "Citrus Flavor"],
        "product_category": ["Flavors", "Natural Flavors"],
    },
    "other natural flavors": {
        "aliases": ["Natural Flavorings", "WONF"],
        "product_category": ["Flavors", "Natural Flavors"],
    },
    "organic flavor": {
        "aliases": ["Organic Natural Flavor", "Certified Organic Flavoring"],
        "product_category": ["Flavors", "Natural Flavors"],
    },
    "organic vanilla flavors": {
        "aliases": ["Organic Vanilla Extract", "Organic Vanilla Flavoring"],
        "product_category": ["Flavors", "Natural Flavors"],
    },
    "ground vanilla beans": {
        "aliases": ["Vanilla Bean Powder", "Vanilla Bean Pieces"],
        "product_category": ["Flavors", "Natural Flavors", "Botanical Extracts"],
    },
    "lemon juice powder": {
        "aliases": ["Lemon Juice Concentrate Powder", "Citrus Juice Powder"],
        "product_category": ["Flavors", "Food Additives", "Vitamins"],
    },
    # --- Colorants ---
    "bht": {
        "aliases": [
            "Butylated Hydroxytoluene",
            "E321",
            "2,6-Di-tert-butyl-4-methylphenol",
        ],
        "product_category": ["Antioxidants", "Preservatives", "Excipients"],
    },
    "beet extract": {
        "aliases": ["Beetroot Extract", "Beta Vulgaris Extract", "E162"],
        "product_category": ["Colorants", "Botanical Extracts"],
    },
    "beet juice powder": {
        "aliases": ["Beetroot Juice Powder", "E162"],
        "product_category": ["Colorants", "Botanical Extracts"],
    },
    "beet powder": {
        "aliases": ["Beetroot Powder", "Beet Root Powder"],
        "product_category": ["Colorants", "Botanical Extracts"],
    },
    "blue 2 lake": {
        "aliases": ["Indigo Carmine Lake", "FD&C Blue No. 2 Lake", "E132"],
        "product_category": ["Colorants", "Synthetic Dyes"],
    },
    "coloring concentrates": {
        "aliases": ["Color Blend", "Colorant Mixture"],
        "product_category": ["Colorants"],
    },
    "fd and c blue no 2 lake": {
        "aliases": ["Blue 2 Lake", "Indigo Carmine Lake", "E132"],
        "product_category": ["Colorants", "Synthetic Dyes"],
    },
    "fd and c red no 40 lake": {
        "aliases": ["Red 40 Lake", "Allura Red Lake", "E129"],
        "product_category": ["Colorants", "Synthetic Dyes"],
    },
    "fd and c yellow no 6 lake": {
        "aliases": ["Yellow 6 Lake", "Sunset Yellow Lake", "E110"],
        "product_category": ["Colorants", "Synthetic Dyes"],
    },
    "red 40 lake": {
        "aliases": ["Allura Red Lake", "FD&C Red 40 Lake", "E129"],
        "product_category": ["Colorants", "Synthetic Dyes"],
    },
    "yellow 6 lake": {
        "aliases": ["Sunset Yellow Lake", "FD&C Yellow 6 Lake", "E110"],
        "product_category": ["Colorants", "Synthetic Dyes"],
    },
    # --- Acids / Acidulants ---
    "citric acid": {
        "aliases": ["E330", "2-Hydroxypropane-1,2,3-Tricarboxylic Acid"],
        "product_category": ["Acidulants", "Food Additives"],
    },
    "non gmo citric acid": {
        "aliases": ["Non-GMO Citric Acid", "E330"],
        "product_category": ["Acidulants", "Food Additives"],
    },
    "dl tartaric acid": {
        "aliases": ["Racemic Tartaric Acid", "E334"],
        "product_category": ["Acidulants", "Food Additives"],
    },
    "lactic acid": {
        "aliases": ["E270", "2-Hydroxypropanoic Acid", "Milk Acid"],
        "product_category": ["Acidulants", "Food Additives"],
    },
    "malic acid": {
        "aliases": ["E296", "Malate", "Apple Acid"],
        "product_category": ["Acidulants", "Food Additives"],
    },
    # --- Emulsifiers / Lecithins ---
    "lecithin": {
        "aliases": ["Phosphatidylcholine", "E322"],
        "product_category": ["Emulsifiers", "Lipids"],
    },
    "organic sunflower lecithin": {
        "aliases": ["Sunflower Phospholipids", "Organic Lecithin"],
        "product_category": ["Emulsifiers", "Lipids"],
    },
    "soy lecithin": {
        "aliases": ["Soya Lecithin", "E322(i)", "Soybean Phospholipids"],
        "product_category": ["Emulsifiers", "Lipids"],
    },
    "sunflower lecithin": {
        "aliases": ["Sunflower Phospholipids", "Non-GMO Lecithin"],
        "product_category": ["Emulsifiers", "Lipids"],
    },
    # --- Glycerin / Humectants ---
    "glycerin": {
        "aliases": ["Glycerol", "Glycerine", "E422"],
        "product_category": ["Excipients", "Humectants"],
    },
    # --- Starches / Maltodextrins ---
    "maltodextrin": {
        "aliases": ["Maltodex", "Corn Syrup Solids", "MDE"],
        "product_category": ["Excipients", "Carbohydrates"],
    },
    "organic maltodextrin": {
        "aliases": ["Organic Corn Maltodextrin", "Organic Tapioca Maltodextrin"],
        "product_category": ["Excipients", "Carbohydrates"],
    },
    "organic rice bran extract": {
        "aliases": ["Rice Bran Wax", "Oryzanol"],
        "product_category": ["Botanical Extracts", "Excipients"],
    },
    "organic rice dextrins": {
        "aliases": ["Rice Dextrin", "Organic Rice Soluble Fiber"],
        "product_category": ["Excipients", "Dietary Fiber"],
    },
    # --- Specialty / Complex Blends ---
    "digestive enzymes": {
        "aliases": ["Enzyme Blend", "Proteases Amylases Lipases"],
        "product_category": ["Nutraceuticals", "Digestive Health"],
    },
    "energy support botanicals nutrients": {
        "aliases": ["Energy Blend", "Botanical Energy Complex"],
        "product_category": ["Nutraceuticals", "Botanical Extracts"],
    },
    "fruit and vegetable juice": {
        "aliases": ["Fruit Veggie Juice Blend", "Juice Concentrate"],
        "product_category": ["Food Additives", "Botanical Extracts"],
    },
    "fruit nutrients": {
        "aliases": ["Fruit Complex", "Fruit Extract Blend"],
        "product_category": ["Botanical Extracts", "Nutraceuticals"],
    },
    "organic food complex": {
        "aliases": ["Organic Food Blend", "Organic Superfood Complex"],
        "product_category": ["Botanical Extracts", "Nutraceuticals"],
    },
    "organic food complex blend": {
        "aliases": ["Organic Food Blend", "Superfood Complex"],
        "product_category": ["Botanical Extracts", "Nutraceuticals"],
    },
    "performance support nutrients": {
        "aliases": ["Performance Blend", "Athletic Support Blend"],
        "product_category": ["Sports Nutrition", "Nutraceuticals"],
    },
    "vegetable nutrients": {
        "aliases": ["Vegetable Complex", "Veggie Blend"],
        "product_category": ["Botanical Extracts", "Nutraceuticals"],
    },
    "ferment media": {
        "aliases": ["Fermentation Media", "Culture Media"],
        "product_category": ["Excipients", "Probiotics"],
    },
    # --- Cocoa ---
    "cocoa": {
        "aliases": ["Cacao", "Theobroma Cacao", "Cocoa Powder"],
        "product_category": ["Food Additives", "Natural Flavors"],
    },
    "cocoa powder": {
        "aliases": ["Cacao Powder", "Theobroma Cacao Powder"],
        "product_category": ["Food Additives", "Natural Flavors"],
    },
    "cocoa powder processed with alkali": {
        "aliases": ["Dutch Process Cocoa", "Alkalized Cocoa"],
        "product_category": ["Food Additives", "Natural Flavors"],
    },
    "cocoa processed with alkali": {
        "aliases": ["Dutch Process Cocoa", "Alkalized Cacao"],
        "product_category": ["Food Additives", "Natural Flavors"],
    },
}


def get_meta(ingredient_name: str) -> dict:
    """Look up metadata, with pattern-based fallback."""
    name = ingredient_name.strip().lower()
    if name in INGREDIENT_META:
        return INGREDIENT_META[name]

    # Pattern-based fallbacks
    if re.search(r"\bvitamin\b", name):
        return {"aliases": [], "product_category": ["Vitamins"]}
    if re.search(r"\bmagnesium\b", name):
        return {"aliases": [], "product_category": ["Minerals"]}
    if re.search(r"\bcalcium\b", name):
        return {"aliases": [], "product_category": ["Minerals"]}
    if re.search(r"\bzinc\b", name):
        return {"aliases": [], "product_category": ["Minerals"]}
    if re.search(r"\biron\b|\bferr", name):
        return {"aliases": [], "product_category": ["Minerals"]}
    if re.search(r"\bpotassium\b", name):
        return {"aliases": [], "product_category": ["Minerals", "Electrolytes"]}
    if re.search(r"\bsodium\b", name):
        return {"aliases": [], "product_category": ["Minerals", "Electrolytes"]}
    if re.search(r"\bprotein\b|\bwhey\b|\bcollagen\b", name):
        return {"aliases": [], "product_category": ["Proteins"]}
    if re.search(r"\bcapsule\b|\bsoftgel\b|\bgelatin\b", name):
        return {"aliases": [], "product_category": ["Excipients", "Encapsulation"]}
    if re.search(r"\bcellulose\b|\bstarch\b|\bsilica\b|\btalc\b", name):
        return {"aliases": [], "product_category": ["Excipients"]}
    if re.search(r"\bflavor\b|\bflavour\b", name):
        return {"aliases": [], "product_category": ["Flavors", "Food Additives"]}
    if re.search(r"\bstevia\b|\bsucralose\b|\bmonk fruit\b|\bsugars?\b|\bsweet", name):
        return {"aliases": [], "product_category": ["Sweeteners"]}
    if re.search(r"\boil\b|\bmct\b", name):
        return {"aliases": [], "product_category": ["Oils", "Lipids"]}
    if re.search(r"\blecithin\b", name):
        return {"aliases": [], "product_category": ["Emulsifiers"]}
    if re.search(r"\bgum\b|\bcarrageen\b|\bxanthan\b|\bpectin\b", name):
        return {"aliases": [], "product_category": ["Gums", "Excipients"]}
    if re.search(r"\binulin\b|\bfos\b|\bprebiotic\b|\bfiber\b", name):
        return {"aliases": [], "product_category": ["Prebiotics", "Dietary Fiber"]}
    if re.search(r"\bprobiotic\b|\bbifidobacterium\b|\blactobacillus\b", name):
        return {"aliases": [], "product_category": ["Probiotics"]}
    if re.search(r"\bextract\b|\bherb\b|\broot\b|\bplant\b|\bleaf\b", name):
        return {"aliases": [], "product_category": ["Botanical Extracts"]}
    if re.search(r"\bacid\b", name):
        return {"aliases": [], "product_category": ["Acidulants", "Food Additives"]}
    if re.search(r"\bcolor\b|\blake\b|\bdye\b", name):
        return {"aliases": [], "product_category": ["Colorants"]}
    if re.search(r"\bglycerin\b|\bglycerol\b", name):
        return {"aliases": [], "product_category": ["Excipients", "Humectants"]}
    if re.search(r"\bwax\b|\bcoat\b", name):
        return {"aliases": [], "product_category": ["Excipients", "Coatings"]}

    return {"aliases": [], "product_category": ["Nutraceuticals"]}


# ---------------------------------------------------------------------------
# Main enrichment logic
# ---------------------------------------------------------------------------


def enrich(csv_path: str, output_path: str | None = None) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    # Drop previously enriched columns if present
    drop_cols = [
        c
        for c in ["RM_ingredient", "region", "aliases", "product_category"]
        if c in df.columns
    ]
    if drop_cols:
        df = df.drop(columns=drop_cols)

    # Extract readable ingredient name from RM_SKU
    df["RM_ingredient"] = (
        df["RM_SKU"].str.extract(r"RM-C\d+-(.+)-[a-f0-9]{8}$")[0].str.replace("-", " ")
    )

    # Compute per-supplier region
    df["_supplier_region"] = df["SupplierName"].map(classify_supplier_region)

    # Aggregate region per RM_SKU (each SKU may have multiple supplier rows)
    sku_region = (
        df.groupby("RM_SKU")["_supplier_region"]
        .apply(aggregate_region)
        .rename("region")
    )
    df = df.join(sku_region, on="RM_SKU")

    # Add aliases and product_category per RM_ingredient
    meta = df["RM_ingredient"].map(get_meta)
    df["aliases"] = meta.map(lambda m: str(m["aliases"]))
    df["product_category"] = meta.map(lambda m: str(m["product_category"]))

    df = df.drop(columns=["_supplier_region"])

    out = output_path or csv_path
    df.to_csv(out, index=False)
    print(f"Saved enriched CSV → {out}")
    print(f"Shape: {df.shape}")
    print("\nNew columns: RM_ingredient, aliases, product_category, region")
    print(
        df[["RM_ingredient", "aliases", "product_category", "region"]]
        .drop_duplicates("RM_ingredient")
        .head(10)
        .to_string()
    )
    return df


if __name__ == "__main__":
    import sys

    csv_path = sys.argv[1] if len(sys.argv) > 1 else "data/all_data.csv"
    enrich(csv_path)
