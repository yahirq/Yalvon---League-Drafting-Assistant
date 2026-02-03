# Yalvon---League-Drafting-Assistant
Yalvon is a League of Legends drafting assistant that utitlizes AI to create assisted suggestions and simulations of draft states.

This repository contains all that is used to build the .exe via pyinstaller

Below are pyinstaller flags that were used.
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
