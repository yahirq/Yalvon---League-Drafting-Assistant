# Yalvon - League Drafting Assistant
Yalvon is a League of Legends drafting assistant that utitlizes AI to create assisted suggestions and simulations of draft states.
This repository contains all that is used to build the .exe via pyinstaller

## Table of Contents
- [Installation](#installation)
- [Usage](#Usage) 
- [License](#License)

## Installation 
The application is built using the pyinstaller module in python, required modules needed to run the python are listed in **requirements.text** (if ran through the .py)

Clone the repository, and install required modules. 
eg.
```
pip install -r requirements.text
```
After everything is installed, you can run **yalvon.py** to open the main application window

v- These are instructions for building the .exe via pyinstaller -v
Pyinstaller flags that were used.
```
pyinstaller --name "Yalvon - Draft Assistant" `
 --onefile `
 --windowed `
 --add-data "cbmodels/CatModel.cbm;cbmodels" `
 --add-data "csvdata;csvdata" `
 --add-data "images;images" `
 --collect-submodules google `
 --collect-submodules google.genai `
 --collect-submodules dotenv `
 --collect-submodules catboost `
 --collect-submodules pandas `
 --hidden-import PyQt5.sip `
 --hidden-import PyQt5.QtCore `
 --hidden-import PyQt5.QtGui `
 --hidden-import PyQt5.QtWidgets `
 --hidden-import AI.GeminiManager `
 --hidden-import AI.DraftService `
 yalvon.py
```

## Usage
If built through pyinstaller with the flags, you should get a .exe. The .exe will generate a .env file where the api key if entered is stored locally on the computer.
However you can also run yalvon.py directly if all modules from the **requirements.text** are installed.

**This application requires a gemini api key to use the AI features**

Once a valid api key is entered at the top right (stored locally) the AI chat assistant can be used by entering a prompt at the bottom left corner.

Otherwise the application functions as a League of Legends draft simulator, where you can pick/ban according to turn order (displayed at the top left). Champions available are from the latest patch as of January 2026, winrates, games picked, and predicted winrate from the Catboost model are all from historical pro League of Legends games as of December 2025.

Each champion on the champion grid in the middle have a winrate, games played and a delta w/r percentage, which displays how much the predicted winrate bar will change for the team that has the turn. Turn order follows the same order held in pro matches.

## License

Licensed under *Apache License 2.0*

