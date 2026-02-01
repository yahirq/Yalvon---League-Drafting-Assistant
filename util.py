import os
import requests
import re
import json
import tkinter as tk


# fetch champion data from urls (images, champ list) store result in output.txt and images folder
def fetch_champions():
    champ_url = "https://ddragon.leagueoflegends.com/cdn/15.24.1/data/en_US/champion.json"
    square_url = "https://ddragon.leagueoflegends.com/cdn/15.24.1/img/champion"
    response = requests.get(champ_url).json()

    champs = response["data"]

    img_folder = "images"
    if not os.path.exists(img_folder):
            print(f"Image folder '{img_folder}' does not exist... creating folder")
            os.makedirs(img_folder, exist_ok=True)
    

    with open("output.txt", "w") as f:
        for name, info in champs.items():
            champ_id = info["key"]

            square_img = requests.get(f"{square_url}/{name}.png")
            square_filepath = os.path.join(img_folder, f"{name}.png")

            f.write(f"{name} {champ_id},\n")

            with open(square_filepath, "wb") as t:
                t.write(square_img.content)

def name_cleanup(name: str) -> str:
    """
    Normalize champion identifiers to their display names.

    Handles:
    - Known aliases and Riot internal keys (e.g., 'MonkeyKing' -> 'Wukong')
    - Missing apostrophes (e.g., 'KSante' -> 'K'Sante', 'KaiSa' -> 'Kai'Sa')
    - CamelCase spacing fallback (e.g., 'LeeSin' -> 'Lee Sin')

    The mapping is case-insensitive.
    """
    if not name:
        return name

    raw = name.strip()

    # Normalize underscores/hyphens to nothing for lookup
    key = raw.replace("_", "").replace("-", "")
    key_lower = key.lower()

    # Known canonical display names and aliases
    exceptions = {
        # Apostrophes
        "ksante": "K'Sante",
        "kaisa": "Kai'Sa",
        "kogmaw": "Kog'Maw",
        "rek'sai": "Rek'Sai",      # already proper, here for completeness
        "reksai": "Rek'Sai",
        "velkoz": "Vel'Koz",
        "xinzhao": "Xin Zhao",     # no apostrophe but keep here for alias
        "cho'gath": "Cho'Gath",
        "chogath": "Cho'Gath",
        "kha'zix": "Kha'Zix",
        "khazix": "Kha'Zix",
        "tahmkench": "Tahm Kench",
        "jarvaniv": "Jarvan IV",
        "drmundo": "Dr. Mundo",
        "dr.mundo": "Dr. Mundo",
        "drmundo": "Dr. Mundo",
        "missfortune": "Miss Fortune",
        "leesin": "Lee Sin",
        "leblanc": "LeBlanc",

        # Canonical Riot keys/aliases
        "monkeyking": "Wukong",
        "fiddlesticks": "Fiddlesticks",
        "wukong": "Wukong",
        "aurelionsol": "Aurelion Sol",
        "masteryi": "Master Yi",
        "taliyah": "Taliyah",
        "renataglasc": "Renata Glasc",
        "belveth": "Bel'Veth",
        "kaisa": "Kai'Sa",
        "ksante": "K'Sante",
        "nunuwillump": "Nunu & Willump",
        "xinzhao": "Xin Zhao",
        "jarvaniv": "Jarvan IV",
        "missfortune": "Miss Fortune",
        "drmundo": "Dr. Mundo",
        "kogmaw": "Kog'Maw",
        "velkoz": "Vel'Koz",
        "reksai": "Rek'Sai",
        "khazix": "Kha'Zix",
        "chogath": "Cho'Gath",
        "kled": "Kled",  # example stable
    }

    # If exact alias exists
    if key_lower in exceptions:
        return exceptions[key_lower]

    # Handle common special cases heuristically before fallback:
    # Insert apostrophes for patterns like "KaiSa" -> "Kai'Sa", "KSante" -> "K'Sante"
    # Heuristic patterns for known pairs:
    heuristics = {
        # pattern (lower) -> replacement with apostrophe
        "kaisa": "Kai'Sa",
        "ksante": "K'Sante",
        "kogmaw": "Kog'Maw",
        "velkoz": "Vel'Koz",
        "reksai": "Rek'Sai",
        "khazix": "Kha'Zix",
        "chogath": "Cho'Gath",
        "belveth": "Bel'Veth",
    }
    if key_lower in heuristics:
        return heuristics[key_lower]

    # Fallback: split CamelCase into words
    # Example: "LeeSin" -> "Lee Sin", "JarvanIV" -> "Jarvan IV"
    spaced = re.sub(r'(\w)([A-Z])', r'\1 \2', raw)

    # Small fix-ups for roman numerals and common tokens
    spaced = spaced.replace(" Ii", " II").replace(" Iii", " III").replace(" Iv", " IV").replace(" Vi", " VI")
    spaced = re.sub(r'\b([IVX])\s+([IVX])\b', r'\1\2', spaced)
    # Normalize multiple spaces
    spaced = re.sub(r'\s+', ' ', spaced).strip()

    return spaced

def to_image_key(display_name: str) -> str:
    """
    Convert a proper display name (e.g., \"K'Sante\", \"Cho'Gath\", \"Miss Fortune\")
    into the Data Dragon image file stem used in your images folder (e.g., \"KSante\", \"ChoGath\", \"MissFortune\").

    Returns a string without extension, so you can build paths like f\"images/{key}.png\".
    """
    if not display_name:
        return display_name

    name = display_name.strip()

    # Canonical exceptions where the image key differs from a naive removal of spaces/apostrophes/dots
    # Note: These are DDragon sprite keys (not internal aliases). Keep only cases where punctuation/spacing matters.
    exceptions = {
        "K'Sante": "KSante",
        "Kai'Sa": "KaiSa",
        "Kog'Maw": "KogMaw",
        "Vel'Koz": "VelKoz",
        "Rek'Sai": "RekSai",
        "Kha'Zix": "KhaZix",
        "Cho'Gath": "ChoGath",
        "Bel'Veth": "BelVeth",
        "Dr. Mundo": "DrMundo",
        "Miss Fortune": "MissFortune",
        "Lee Sin": "LeeSin",
        "Jarvan IV": "JarvanIV",
        "Master Yi": "MasterYi",
        "Aurelion Sol": "AurelionSol",
        "Xin Zhao": "XinZhao",
        "Tahm Kench": "TahmKench",
        "Renata Glasc": "RenataGlasc",
        "Nunu & Willump": "Nunu",   # DDragon uses Nunu.png (legacy key)
        # Add any other quirky ones you need here
    }

    # Fast path for known names (case-insensitive compare)
    for disp, key in exceptions.items():
        if disp.lower() == name.lower():
            return key

    # Generic normalization:
    # - Remove apostrophes
    # - Remove spaces
    # - Remove dots/periods
    # - Remove ampersand and the word 'and' (Nunu & Willump -> NunuWillump -> we special-cased to Nunu above anyway)
    # - TitleCase the result to match typical DDragon casing
    simplified = name
    simplified = simplified.replace("'", "")
    simplified = simplified.replace(".", "")
    simplified = simplified.replace("&", " ")
    simplified = re.sub(r'\band\b', ' ', simplified, flags=re.IGNORECASE)
    simplified = re.sub(r'\s+', ' ', simplified).strip()

    # Remove spaces to form the key
    key = simplified.replace(" ", "")

    # Heuristic: ensure roman numerals are uppercase and glued (Jarvan IV -> JarvanIV handled by spaces removal)
    # Also keep typical capitalization (first letter of each token uppercase)
    # If the user passed something all-lowercase, Title-case tokens:
    if not any(c.isupper() for c in key):
        key = "".join(part.capitalize() for part in simplified.split())

    return key

# reads output.txt and returns either clean name or id based on input type (raw name | integer id)
def champ_lookup(champ: str | int):
    with open("output.txt", "r") as f:
        for line in f:
            curr_name, curr_id = line.split(' ', 1)
            curr_id = int(curr_id.split(',')[0]) 
            if isinstance(champ, str) and curr_name.lower() == champ.lower():
                return curr_id
            elif isinstance(champ, int) and curr_id == champ:
                return curr_name
    return None

#not used in app, but useful for testing search functionality
def filter_names(text):
    text = text.lower()
    filtered_names = []
    with open("output.txt", "r") as f:
        for line in f:
            curr_name, curr_id = line.split(' ', 1)
            curr_id = int(curr_id.split(',')[0]) 
            if curr_name.lower().startswith(text):
                print(f"{curr_name} starts with {text}!")
                filtered_names.append((curr_name, curr_id))
    # print(filtered_names)
    return filtered_names


#region tkinter search example (not used in app)
# def on_change(*args):
#     query = search_var.get()
#     matches = filter_names(query)
#     results_list.delete(0, tk.END)
#     for m in matches:
#         results_list.insert(tk.END, m)

# root = tk.Tk()
# search_var = tk.StringVar()
# search_var.trace_add("write", on_change)

# entry = tk.Entry(root, textvariable=search_var)
# entry.pack()

# results_list = tk.Listbox(root)
# results_list.pack()

# root.mainloop()
#endregion

if __name__ == "__main__":
   
    try:
        #filter_names("T")
        fetch_champions()
        #print(champ_lookup("Aatrox"))
    except requests.HTTPError as e:
        print(f"HTTP error occurred: {e}")
    except requests.RequestException as e:
        print(f"Request error occurred: {e}")
    except ValueError:
        print("Error parsing JSON response")

