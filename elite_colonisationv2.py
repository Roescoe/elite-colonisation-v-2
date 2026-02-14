from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import *
from PyQt6 import uic, QtGui, QtCore
from PyQt6.QtGui import QFont, QColor
import asyncio
import sys
import os
import platform
import ctypes
import json
import ast
import time
import pickle
from datetime import datetime, timezone, timedelta
import glob
from createTable import createTable
from collections import OrderedDict

# This is a tool to print out Elite Dangerous colonisation data pulled from the user's logfiles
# Copyright (C) 2025 Roescoe

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


class LogFileDialogClass(QDialog):
    def __init__(self, *args, **kwargs):
        super(LogFileDialogClass, self).__init__()
        self.directory = ''
        print("loading file dialog")
        uic.loadUi('logfile_select.ui', self)

        self.getFileSettings()
        self.OpenFile.clicked.connect(lambda:self.openFileSystem())

    def openFileSystem(self):
        defaultFileDir = ''
        myappid = 'roescoe.colonisation.organisation.application'

        if(platform.system() == 'Windows'):
            defaultFileDir = os.path.expandvars(r"C:\Users\$USERNAME") + r'\Saved Games\Frontier Developments\Elite Dangerous'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        elif(platform.system() == 'Linux'):
            defaultFileDir = os.path.expanduser("~") + '/.local/share/Steam/steamapps/compatdata/359320/pfx/drive_c/users/steamuser/Saved Games/Frontier Developments/Elite Dangerous'
        else:
            print("OS not currently supported")
        logfileLocation = QFileDialog(self)
        directoryReturn = logfileLocation.setDirectory(defaultFileDir)
        print("directoryReturn: ",directoryReturn)
        logfileLocation.setFileMode(QFileDialog.FileMode.Directory)
        logfileLocation.setViewMode(QFileDialog.ViewMode.List)
        self.directory = logfileLocation.getExistingDirectory()
        self.FileNamelineEdit.setText(self.directory)

    def getFileSettings(self):
        if os.path.exists("settings.txt"):
            with open("settings.txt", "r") as f:
                testFileLine = f.readlines()
                for line in testFileLine:
                    if line.startswith("Folder_location:"):
                        self.FileNamelineEdit.setText(line.split("Folder_location: ",1)[1].strip())
                        print("found default folder:", line.split("Folder_location: ",1)[1].strip())


class UI(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(UI, self).__init__()
        #properties
        self.subVersion =".15a"
        self.olderThanNumDays = 0
        self.allTextSize = 12
        self.logfiles = []
        self.uniqueStations = []
        self.colonies = []
        self.eliteFileTime = 0
        self.mostRecentReadTime = 0
        self.lastFileName = ''
        self.resourceTypeDict = {}
        self.resourceTableList = QTableWidget()
        self.resourceTableRowsList = {}
        self.marketEntries = {}
        self.fleetCarrierMarket = []
        self.tableLabels = []
        self.ships = []
        # self.transactions = []
        self.previousStationIndex = -2

        #initialize windows
        uic.loadUi('elite_colonisationv2Alt.ui', self)
        self.setWindowIcon(QtGui.QIcon('ColoniseLogo.png'))
        app.setWindowIcon(QtGui.QIcon('ColoniseLogo.png'))
        self.show()
        self.LogFileDialog = LogFileDialogClass()

        #set up stuff
        self.getFileSettings()
        self.getLogFileData()
        
        self.displayColony()
        # self.calculateTransactions()


        #buttons
        self.actionSet_logfile_location.triggered.connect(lambda:self.showLogfileDialog())
        self.actionAll.triggered.connect(lambda:self.setLogfileLoadRange(10000,True))
        self.action1_Day.triggered.connect(lambda:self.setLogfileLoadRange(1000,True))
        self.action1_Week.triggered.connect(lambda:self.setLogfileLoadRange(100,True))
        self.action1_Month.triggered.connect(lambda:self.setLogfileLoadRange(10,True))
        self.action100_Days.triggered.connect(lambda:self.setLogfileLoadRange(1,True))
        self.action9pt_2.triggered.connect(lambda:self.setTextSize(10000))
        self.action10pt_2.triggered.connect(lambda:self.setTextSize(1000))
        self.action12pt_2.triggered.connect(lambda:self.setTextSize(100))
        self.action16pt_2.triggered.connect(lambda:self.setTextSize(10))
        self.action24pt_2.triggered.connect(lambda:self.setTextSize(1))
        self.actionHide_total_need.triggered.connect(lambda:self.formatResourceTable())
        self.actionHide_Finished_Resources.triggered.connect(lambda:self.formatResourceTable())
        self.stationList.activated.connect(lambda:self.updateTableData())
        self.shipList.currentIndexChanged.connect(lambda:self.updateCargo())
        self.update.clicked.connect(lambda:self.updateTableData())
        self.actionload_stats.triggered.connect(lambda:self.getScsStats())
        self.resourceTableList.horizontalHeader().sectionClicked.connect(self.sortedColumnFunction)

        self.actionQuit.triggered.connect(lambda:self.saveAndQuit())

    def showLogfileDialog(self):
        print("showing log file now... ")
        self.LogFileDialog.exec()
        if not os.path.isdir(self.LogFileDialog.FileNamelineEdit.text()):
            print("Invalid file path")
            self.LogFileDialog.FileNamelineEdit.setText("")

    def updateTableData(self):
        print("**Clicked Update or changed menu option**")
        self.getLogFileData()
        self.displayColony()

    def setLogfileLoadRange(self, loadTimeSelect, refreshList):
        
        currentTime = time.time()

        self.actionAll.setChecked(False)
        self.action1_Day.setChecked(False)
        self.action1_Week.setChecked(False)
        self.action1_Month.setChecked(False)
        self.action100_Days.setChecked(False)

        match loadTimeSelect:
            case 10000:
                self.actionAll.setChecked(True)
                self.olderThanNumDays = 0
            case 1000:
                self.action1_Day.setChecked(True)
                self.olderThanNumDays = currentTime - 3600*24*1
            case 100:
                self.action1_Week.setChecked(True)
                self.olderThanNumDays = currentTime - 3600*24*7
            case 10:
                self.action1_Month.setChecked(True)
                self.olderThanNumDays = currentTime - 3600*24*30
            case 1:
                self.action100_Days.setChecked(True)
                self.olderThanNumDays = currentTime - 3600*24*100
            case _:
                self.olderThanNumDays = 0

        self.getEliteTime(loadTimeSelect)
        if refreshList:
            self.updateTableData()

    def setTextSize(self, textsize):

        self.action9pt_2.setChecked(False)
        self.action10pt_2.setChecked(False)
        self.action12pt_2.setChecked(False)
        self.action16pt_2.setChecked(False)
        self.action24pt_2.setChecked(False)

        match textsize:
            case 10000:
                self.action9pt_2.setChecked(True)
                self.allTextSize = 9
            case 1000:
                self.action10pt_2.setChecked(True)
                self.allTextSize = 10
            case 100:
                self.action12pt_2.setChecked(True)
                self.allTextSize = 12
            case 10:
                self.action16pt_2.setChecked(True)
                self.allTextSize = 16
            case 1:
                self.action24pt_2.setChecked(True)
                self.allTextSize = 24
            case _:
                self.allTextSize = 14
        self.formatResourceTable()

    def getFileSettings(self):

        self.deleteOldLogFile("importantLogs.txt")
        self.deleteOldLogFile("currentImportantData.txt")
        self.setWindowTitle(f"CMDR Roescoe's Colonisation App v2{self.subVersion}")
        if os.path.exists("settings.txt"):
            with open("settings.txt", "r") as f:
                testFileLine = f.readlines()
                for line in testFileLine:
                    if line.startswith("Load_time_selection:"):
                        print("Found time in settings")
                        loadTimeSelect = int(line.split("Load_time_selection: ",1)[1].strip())
                        print("Loading from time:", loadTimeSelect)
                        if loadTimeSelect:
                            self.setLogfileLoadRange(loadTimeSelect, False)
                    if line.startswith("Table_size:"):
                        print("Found table size in settings")
                        if isinstance(int(line.split("Table_size: ",1)[1].strip()), int):
                            tableSizeIndex = int(line.split("Table_size: ",1)[1].strip())
                            self.setTextSize(tableSizeIndex)
                    if line.startswith("Hide_resources:"):
                        print("Found checkbox in settings \'"+ line.split("Hide_resources: ",1)[1].strip()+"\'")
                        if isinstance(int(line.split("Hide_resources: ",1)[1].strip()), int):
                            hideBoxIsChecked = bool(int(line.split("Hide_resources: ",1)[1].strip()))
                            self.actionHide_Finished_Resources.setChecked(hideBoxIsChecked)
                    if line.startswith("Hide_total_need:"):
                        print("Found checkbox in settings \'"+ line.split("Hide_total_need: ",1)[1].strip()+"\'")
                        if isinstance(int(line.split("Hide_total_need: ",1)[1].strip()), int):
                            hideBoxIsChecked = bool(int(line.split("Hide_total_need: ",1)[1].strip()))
                            self.actionHide_total_need.setChecked(hideBoxIsChecked)
                    if line.startswith("Get_stats:"):
                        if isinstance(int(line.split("Get_stats:",1)[1].strip()),int):
                            getStatsBoxIsChecked = bool(int(line.split("Get_stats: ",1)[1].strip()))
                            self.actionload_stats.setChecked(getStatsBoxIsChecked)

        if os.path.exists("stationList.pickle"):
            with open("stationList.pickle", 'rb') as st:
                self.uniqueStations = pickle.load(st)


    def getLogFileData(self):
        # self.transactions.clear()

        print("Starting logfile gathering")
        self.findLogfiles()
        for logfile in self.logfiles:
            self.getAllLogFileData(logfile)
        self.saveColonies("importantLogs.txt")
        self.populateStationList()
        self.populateShipList()
        # self.populateCarrierList()


    def findLogfiles(self):
        folderdir = self.LogFileDialog.FileNamelineEdit.text()
        createTime = []
        logFileList = []

        print(f"Getting files from ", {self.olderThanNumDays}, "secs ago, at", {folderdir})
        for path, dirc, files in os.walk(folderdir):
            for name in files:
                if name.endswith('.log'):
                    if os.path.getctime(os.path.join(path, name)) >= self.olderThanNumDays:
                        logFileList.append(os.path.join(path, name))
                        createTime.append(os.path.getctime(os.path.join(path, name)))
        logFileListSortedPairs = sorted(zip(createTime,logFileList))
        self.logfiles = [x for _, x in logFileListSortedPairs]
        # for printMeNow in logFileListSortedPairs:
        #     print("logFileListSortedPairs: ",printMeNow[1].split("Journal.",1)[1])
        self.logfiles.sort()

        # for logfile in self.logfiles:
        #     print("self.logfiles: ",logfile.split("Journal.",1)[1])

    def getAllLogFileData(self, logfile):
        isUnique = True
        stationType = ""

        print("Reading logfile: ", logfile.split("Journal.",1)[1])
        with open(logfile, "r", encoding='iso-8859-1') as f1:
            for line in f1:
                rawLine = json.loads(line)
                # self.mostRecentReadTime = rawLine["timestamp"]
                foundExistingColony = False
                if "ConstructionProgress" in rawLine:
                    # print("Found a construction landing")
                    for index,colony in enumerate(self.colonies):
                        if str(rawLine["MarketID"]) == str(colony["MarketID"]):
                            foundExistingColony = True
                            if str(rawLine["timestamp"]) > str(colony["timestamp"]):
                                self.colonies[index] = rawLine
                                break
                    if not foundExistingColony or not self.colonies:
                        print("Found an entry in the colony table " if self.colonies else "colony table has no entries in it")
                        self.colonies.append(rawLine)

                if "Loadout" in rawLine.values() and int(rawLine["CargoCapacity"]) > 0:
                    # print("Found a ship")
                    if "CargoCapacity" in rawLine:
                        if self.ships:
                            for ship in self.ships:
                                if str(rawLine["CargoCapacity"]) != str(ship[1]): # Cargo capacity is different
                                    self.ships.append([rawLine["ShipIdent"],rawLine["CargoCapacity"],rawLine["timestamp"]])
                                    break
                        else:
                            self.ships.append([rawLine["ShipIdent"],rawLine["CargoCapacity"],rawLine["timestamp"]])
                if "Docked" in rawLine.values():
                    isUnique = True
                    for i, station in enumerate(self.uniqueStations):
                        if str(rawLine["MarketID"]) == str(station[0]):
                            if str(rawLine["StationType"]) == "FleetCarrier":
                                cleanStationName = rawLine["StationName"] + " (" + str(rawLine["MarketID"])+")"
                                self.uniqueStations[i] = [rawLine["MarketID"], cleanStationName, rawLine["timestamp"], "fleet"]
                            isUnique = False
                            break
                    if isUnique == True:
                        if rawLine["StationName"].startswith("$EXT_PANEL_"):
                            cleanStationName = rawLine["StarSystem"] + ": " + rawLine["StationName"].split("$EXT_PANEL_",1)[1] + " (" + str(rawLine["MarketID"])+")"
                            stationType = "colony"
                        else:    
                            cleanStationName = rawLine["StationName"] + " (" + str(rawLine["MarketID"])+")"
                            StationTypeInFile = rawLine["StationType"]
                            if StationTypeInFile == "SpaceConstructionDepot" or StationTypeInFile == "PlanetaryConstructionDepot":
                                if "StationState" in rawLine:
                                    stationType = "constructed"
                                else:
                                    stationType = "colony"
                            else:
                                stationType = "other"
                        # Station format: ID, Name, time accessed, type
                        self.uniqueStations.append([rawLine["MarketID"], cleanStationName, rawLine["timestamp"], stationType])
                # if ("MarketSell" in rawLine.values() or "MarketBuy" in rawLine.values()):
                #     self.transactions.append(rawLine)

        self.lastFileName = logfile

    def saveColonies(self, outputFile):
        with open(outputFile,"w", encoding='iso-8859-1') as f2:
            for colony in self.colonies:
                f2.write(str(colony)+'\n')

    def populateStationList(self):
        # print("Stations and timeStamps: ",self.uniqueStations)
        if self.uniqueStations:
            self.uniqueStations.sort(key=lambda station:station[2], reverse=True)
            savedIndex = self.stationList.currentIndex()
            self.previousStationIndex = savedIndex
            self.stationList.clear()
            for station in self.uniqueStations:
                print(f"The station time? {station[2]} the file time? {self.eliteFileTime}")
                if self.eliteFileTime < station[2]:
                    if station[3] == "colony":
                        self.stationList.addItem(str(station[1]))
            print("Index of current colony: ", savedIndex)
            if savedIndex == -1:
                self.stationList.setCurrentIndex(0)
            else:
                self.stationList.setCurrentIndex(savedIndex)
        print(f"All stations: {self.uniqueStations}")


    def populateShipList(self):
        print(f"All the ships: {self.ships}")
        if self.ships:
            self.ships.sort(key=lambda ship:ship[2], reverse=True)

            for ship in self.ships:
                items = [self.shipList.itemText(i) for i in range(self.shipList.count())]
                if str(ship[1]) not in str(items):
                    self.shipList.addItem(str(f"{ship[0]} ({ship[1]:,})"))
        if self.shipList:
            current_ship = self.shipList.currentText()
            self.cargoSpace = int(current_ship.replace(",", "").split('(',1)[1].split(')',1)[0])
        print("Got Ships.")

    def updateCargo(self):
        if self.shipList:
            current_ship = self.shipList.currentText()
            self.cargoSpace = int(current_ship.replace(",", "").split('(',1)[1].split(')',1)[0])
        self.displayColony()

    def populateCarrierList(self):
        carriers = []
        if self.uniqueStations:
            self.carrierSelect.clear()
            # self.stationList.sort(key=lambda station:station[2], reverse=True)
            for station in self.uniqueStations:
                # print(f"is station: {station} a fleet Carrier?? {station[3] == 'fleet'}")

                if station[3] == "fleet":
                    items = [self.carrierSelect.itemText(i) for i in range(self.carrierSelect.count())]
                    print(f"items {items} station {station[3]}")
                    if station[3] not in items:
                        carriers.append([str(station[1]), station[2]])
            carriers.sort(key=lambda carrier:carrier[1], reverse=True)
            self.carrierSelect.addItems(carriers[0])

    def calculateTransactions(self):
        commodities = []
        transactionDict = {}
        currentCarrier = str(self.carrierSelect.currentText().split("(",1)[1].split(")",1)[0])
        cargoNaming = {}

        with open("MarketLines.json", "r", encoding='iso-8859-1') as mj:
            testFileLine = json.load(mj)

        for i in testFileLine:
            if "Name" in i and "Name_Localised" in i:
                cargoNaming[i["Name"].split("_",1)[0].split("$",1)[1]] = i["Name_Localised"]
        print(f"cargoNaming: {cargoNaming}")
        print(f"*********Transactions: {self.transactions}")
        for t in self.transactions:
            transationVal = 0
            if str(t["MarketID"]) == currentCarrier:
                transactionResource = cargoNaming[t['Type']]
                print(f"The type: {transactionResource}")
                if transactionDict:
                    if str(transactionResource) in transactionDict:
                        print(f"Updating: {transactionResource}")
                        if str(t["event"]) == "MarketSell":
                            print(f"Store {t['Count']}")
                            transationVal = int(t["Count"])
                        elif str(t["event"]) == "MarketBuy":
                            print(f"Withdraw {t['Count']}")
                            transationVal = int(t["Count"]) * -1
                        else:
                            transationVal = 0
                        transationVal += transactionDict[transactionResource]
                        transactionDict[transactionResource] =  transationVal
                    else:
                        print(f"Adding: {transactionResource}")
                        transactionDict[transactionResource] = t["Count"]
                else:
                    transactionDict[transactionResource] = t["Count"]
        print(f"The new cool table: {transactionDict}")
        for res in transactionDict:
            commodities = self.resourceTableList.findItems(res, Qt.MatchFlag.MatchContains)
            if commodities:
                commodityRow = commodities[0].row()
                needItem = self.resourceTableList.item(commodityRow, self.tableLabels.index("Current Need")).text().replace(",","")
                if needItem == "Done":
                    needItem = 0
                # print(f"how much we need right now: {needItem}")
                carrierNeed = str(int(needItem) - int(transactionDict[res]))
                # print(f"The carrier need: {carrierNeed}")

                qCarrierCurItem = QTableWidgetItem()
                qCarrierNeedItem = QTableWidgetItem()

                qCarrierCurItem.setTextAlignment(Qt.AlignmentFlag.AlignRight)
                qCarrierNeedItem.setTextAlignment(Qt.AlignmentFlag.AlignRight)

                qCarrierCurItem.setText(str(transactionDict[res]))
                qCarrierNeedItem.setText(carrierNeed)

                # self.resourceTableList.setItem(commodityRow, self.tableLabels.index("Carrier Current"), qCarrierCurItem)
                self.resourceTableList.setItem(commodityRow, self.tableLabels.index("Carrier Need"), qCarrierNeedItem)
        transactionDict.clear()

    def displayColony(self):
        selectedMarketID = -1

        selectedColony = self.stationList.currentText()
        print("Filling out ", selectedColony)
        # self.clear_layout(self.resourcesLayout)
        if selectedColony:
            selectedMarketID = int(selectedColony.split("(",1)[1].split(")",1)[0])

        print("selected ID:"+str(selectedMarketID))

        #TODO write to current data file also could just use other file
        readLocation = "currentImportantData.txt"
        if not self.findMarketEntry(selectedMarketID, readLocation):
            print("Not found in current file")
            readLocation = "importantLogs.txt"
            self.findMarketEntry(selectedMarketID, readLocation)
        else:
            print("Found in current file")
            pass

        self.setupResourceTable()
        self.formatResourceTable()
        self.displayColonyStats()
        # self.setFleetCarriers()

    def findMarketEntry(self, selectedMarketID, sourceFile):
        foundEntry = False
        self.marketEntries.clear()
        if os.path.exists(sourceFile):
            with open(sourceFile,"r", encoding='iso-8859-1') as f:
                for line in f:
                    dictLine = ast.literal_eval(line)
                    # for station in self.uniqueStations:
                    if "MarketID" in dictLine:
                        # print("Reading from station: ", type(dictLine["MarketID"]))
                        self.marketEntries[dictLine["MarketID"]] = dictLine
                        foundEntry = True
        # print(f"The entries: {self.marketEntries} were updated? {foundEntry}")
        return foundEntry

    def setupResourceTable(self):
        resourceOrder = []
        activeResources = []
        cargo = 0
        doneState = -1
        currentTable = {}
        currentMarket = ""

        if self.stationList.currentText():
            currentMarket = int(self.stationList.currentText().split("(",1)[1].split(")",1)[0])
        else:
            return -1

        # Clean out table        
        self.resourceTableList.setRowCount(0)
        self.resourceTableList.setHorizontalHeaderLabels([])
        self.resourceTableList.setVerticalHeaderLabels([])
        self.resourceTableList.setSortingEnabled(False)
        self.tableLabels.clear()

        if len(self.shipList) > 0:
            cargo = self.cargoSpace
        
        print("Ships?:", self.shipList)
        print("cargo?:", cargo)
        # print("First Entry:", self.marketEntries[0])

        for entry in self.marketEntries:
            print(f"entry {entry}")
            if "ResourcesRequired" in self.marketEntries[entry]:
                print(f"Reading market: {self.marketEntries[entry]['MarketID']}")
                resourceTable = createTable(self.marketEntries[entry], cargo)
                resourceTableRows = resourceTable.getRows()
                self.resourceTableRowsList[self.marketEntries[entry]["MarketID"]] = resourceTableRows


        if currentMarket in self.resourceTableRowsList:
            print(f"self.resourceTableRowsList current table: {self.resourceTableRowsList[currentMarket]}")
            currentTable = self.resourceTableRowsList[currentMarket]

        if self.resourceTableRowsList and currentTable:
            print(f'The rows object: {resourceTableRows}')

            self.tableLabels.append("Category")
            self.tableLabels.append("Resource")
            self.tableLabels.append("Total Need")
            self.tableLabels.append("Current Need")
            self.tableLabels.append("Trips Remaining")
            self.resourceTableList.setRowCount(len(currentTable))
            self.resourceTableList.setColumnCount(len(self.tableLabels))
            print(f"tableLabels: {self.tableLabels}")
            self.resourceTableList.setHorizontalHeaderLabels(self.tableLabels)

            for i,row in enumerate(currentTable):
                print(f"The row here: {i} and {row}")
                self.resourceTableList.setItem(i, self.tableLabels.index("Category"), currentTable[row][0])
                self.resourceTableList.setItem(i, self.tableLabels.index("Resource"), currentTable[row][1])
                self.resourceTableList.setItem(i, self.tableLabels.index("Total Need"), currentTable[row][2])
                needIndex = self.tableLabels.index("Current Need")
                self.resourceTableList.setItem(i, needIndex, currentTable[row][3][0])
                if currentTable[row][3][1] == 1:
                    self.resourceTableList.item(i, needIndex).setBackground(QColor("green"))
                elif currentTable[row][3][1] == -1:
                    self.resourceTableList.item(i, needIndex).setBackground(QColor("#c32148"))
                elif currentTable[row][3][1] == 0:
                    self.resourceTableList.item(i, needIndex).setBackground(QColor("#281E5D"))
                self.resourceTableList.setItem(i, self.tableLabels.index("Trips Remaining"), currentTable[row][4])

    def formatResourceTable(self):
        hiddenRows = []
        hiddenRows.clear()

        print("Formatting table...")

        if self.tableLabels:
            # unhide all rows to update them properly
            for column in range(self.resourceTableList.columnCount()):
                self.resourceTableList.showColumn(column)
            for row in range(self.resourceTableList.rowCount()):
                self.resourceTableList.showRow(row)

            print(f"Updating row/column display, rows: {self.resourceTableList.rowCount()}, columns: {self.resourceTableList.columnCount()}")
            if self.actionHide_total_need.isChecked():
                self.resourceTableList.setColumnHidden(self.tableLabels.index("Total Need"), True)
            else:
                self.resourceTableList.setColumnHidden(self.tableLabels.index("Total Need"), False)
            if self.actionHide_Finished_Resources.isChecked():
                for row in range(self.resourceTableList.rowCount()):
                    if self.resourceTableList.item(row, self.tableLabels.index("Current Need")) is not None:
                        if self.resourceTableList.item(row, self.tableLabels.index("Current Need")).text() == 'Done':
                            print(f"The item being hidden: {self.resourceTableList.item(row, self.tableLabels.index('Resource')).text()}")
                            hiddenRows.append(self.resourceTableList.item(row, self.tableLabels.index('Resource')).text())
                            self.resourceTableList.setRowHidden(row, True)
                print(f"Rows to hide: {hiddenRows}")
            # resize table
            self.resourceTableList.horizontalHeader().setStyleSheet("QHeaderView::section {color: snow; font-size: {self.allTextSize}px; font-weight: bold; background-color: rgb(20, 28, 160);}")
            self.resourceTableList.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

            for i in range(self.resourceTableList.rowCount()):
                self.resourceTableList.setRowHeight(i, self.allTextSize+15)
            if len(self.tableLabels) > 0:
                self.resourceTableList.setColumnWidth(self.tableLabels.index("Category"), int(13 * self.allTextSize))
                self.resourceTableList.setColumnWidth(self.tableLabels.index("Resource"), int(18 * self.allTextSize))
                self.resourceTableList.setColumnWidth(self.tableLabels.index("Total Need"), int(7 * self.allTextSize))
                self.resourceTableList.setColumnWidth(self.tableLabels.index("Current Need"), int(8 * self.allTextSize))
                self.resourceTableList.setColumnWidth(self.tableLabels.index("Trips Remaining"), int(9 * self.allTextSize))
            self.resourceTableList.setFont(QFont('Calibri',self.allTextSize))

            self.resourceTableList.setSortingEnabled(True)
            self.resourceTableList.verticalHeader().setVisible(False)
            # self.tableDisplayWidget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.tableDisplayLayout.addWidget(self.resourceTableList)

    def displayColonyStats(self):
        tripsCalc = 0
        percentPerTrip = 0
        totalMaterials = 0
        stillNeeded = 0
        percentComplete = 0
        carrierNeed = []
        carrierCurrent = []
        cargo = -1

        print("Calculating various stats...")

        if self.resourceTableList and len(self.tableLabels) > 0:
            for trip in range(self.resourceTableList.rowCount()):
                if self.resourceTableList.item(trip, self.tableLabels.index("Total Need")):
                    totalMaterials += int(self.resourceTableList.item(trip, self.tableLabels.index("Total Need")).text().replace(',', ''))
                if self.resourceTableList.item(trip, self.tableLabels.index("Current Need")) and self.resourceTableList.item(trip, self.tableLabels.index("Current Need")).text() != "Done":
                    stillNeeded += int(self.resourceTableList.item(trip, self.tableLabels.index("Current Need")).text().replace(',', ''))
        if self.cargoSpace:
            cargo = self.cargoSpace
        tripsCalc = round(stillNeeded/cargo, 2)

        if totalMaterials > 0:
            percentPerTrip = round((100 * cargo) / totalMaterials, 2)
        if stillNeeded > 0:
            percentComplete = round(100 * (1 - stillNeeded/totalMaterials), 2)
        else:
            percentComplete = "Done!"

        self.ship_label.setFont(QFont('Calibri',14))
        self.trips_left.setFont(QFont('Calibri',14))
        self.percent_per_trip.setFont(QFont('Calibri',14))
        self.total_materials.setFont(QFont('Calibri',14))
        self.percent_complete.setFont(QFont('Calibri',14))

        self.ship_label.setText(f"Ship:")
        self.trips_left.setText(f"({tripsCalc} Trips)")
        self.percent_per_trip.setText(f"Percent/Trip: {percentPerTrip}%")
        self.total_materials.setText(f"Remaining Materials:   {stillNeeded:,} / {totalMaterials:,}")
        self.percent_complete.setText(f"Progress: {percentComplete}%")

    def clear_layout(self, layout):
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            print("Item to be deleted: ", item)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()  # Safely delete the widget
                layout.removeItem(item)  # Remove the item from the layout

    async def monitor_directory(self):

        print("Checking for new file...")
        folderdir = self.LogFileDialog.FileNamelineEdit.text()
        expectedFile = time.strftime("%Y-%m-%dT%H", time.localtime())
        expectedFile =os.path.join(folderdir, "Journal." + expectedFile + '*'+".log")

        print("Looking for file like: ", expectedFile)
        realFiles = glob.glob(expectedFile, recursive=False)
        if realFiles and realFiles[0] != self.lastFileName:
            self.lastFileName = realFiles[0]
            print("Discovered new file: ", self.lastFileName)


    def getEliteTime(self, adjustmentHours):
        timeAgo = 0
        match adjustmentHours:
            case 10000:
                timeAgo = -1
            case 1000:
                timeAgo = 24*1
            case 100:
                timeAgo = 24*7
            case 10:
                timeAgo = 24*30
            case 1:
                timeAgo = 24*100

        if timeAgo == -1:
            self.eliteFileTime = "2014-12-16T12:00:00Z"
        else:
            formatted_time = datetime.now(timezone.utc) - timedelta(hours = timeAgo)
            formatted_time.strftime("%Y-%m-%dT%H:%M:%SZ")
            print("Time now: ", formatted_time)
            self.eliteFileTime = str(formatted_time.strftime("%Y-%m-%dT%H:%M:%SZ"))

    def sortedColumnFunction(self, index):
        print(f"You just sorted column {index} called: {self.resourceTableList.horizontalHeaderItem(index).text()}")
        currentMarket = int(self.stationList.currentText().split("(",1)[1].split(")",1)[0])
        resortedRowList = self.resourceTableRowsList[currentMarket]
        print(f"The list being sorted: {resortedRowList.items()}")
        # resortedRowList = OrderedDict(sorted(resortedRowList.items(), key=lambda item: item[index].text()))
        # print(f"New order: {self.resourceTableRowsList[currentMarket]}")

    def getScsStats(self):
        highestResource = {}
        lowestResource = {}
        averageResource = {}
        scsMarketIDs = []
        completedScsMarketIDs = []
        notOutpost = False
        totalStations = 0

        for station in self.uniqueStations:
            if "ColonisationShip" in station[1]:
                scsMarketIDs.append(station[0])
        with open("importantLogs.txt","r", encoding='iso-8859-1') as f:
            for line in f:
                if notOutpost == True:
                    notOutpost = False
                    break
                dictLine = ast.literal_eval(line)
                if "MarketID" in dictLine and dictLine["MarketID"] in scsMarketIDs:
                    resources = dictLine["ResourcesRequired"]
                    for i in range(len(resources)):
                        resourceLabel = resources[i]["Name_Localised"]
                        resourceAmount = str(resources[i]["RequiredAmount"])
                        if resourceLabel == "Aluminium":
                            if int(resourceAmount) > int("1000"):
                                totalStations -= 1
                                notOutpost = True
                                break
                        if resourceLabel in highestResource:
                            if int(highestResource[resourceLabel]) < int(resourceAmount):
                                highestResource[resourceLabel] = resourceAmount
                        else:
                            highestResource[resourceLabel] = resourceAmount
                        if resourceLabel in lowestResource:
                            if int(lowestResource[resourceLabel]) > int(resourceAmount):
                                lowestResource[resourceLabel] = resourceAmount
                        else:
                            lowestResource[resourceLabel] = resourceAmount
                        if dictLine["MarketID"] not in completedScsMarketIDs:
                            if resourceLabel in averageResource:
                                averageResource[resourceLabel] = str(int(averageResource[resourceLabel]) + int(resourceAmount))
                            else:
                                averageResource[resourceLabel] = str(int(resourceAmount))
                    if dictLine["MarketID"] not in completedScsMarketIDs:
                        totalStations += 1
                        completedScsMarketIDs.append(dictLine["MarketID"])


        for resource in averageResource:
            averageResource[resource] = str(int(averageResource[resource])/totalStations)
        with open("OutpostScsStat.txt", "w") as g:
            g.write("highest outpost:\n" + str(highestResource))
            g.write("\nlowest outpost:\n" + str(lowestResource))
            g.write("\naverage outpost:\n" + str(averageResource))
        return 1

    def deleteOldLogFile(self, filename):
        try:
            os.remove(filename)
        except OSError:
            pass

    async def check_for_new_files(self):
        defaultFileDir = ''
        if(platform.system() == 'Windows'):
            defaultFileDir = os.path.expandvars(r"C:\Users\$USERNAME") + r'\Saved Games\Frontier Developments\Elite Dangerous'
        elif(platform.system() == 'Linux'):
            defaultFileDir = os.path.expanduser("~") + '/.local/share/Steam/steamapps/compatdata/359320/pfx/drive_c/users/steamuser/Saved Games/Frontier Developments/Elite Dangerous'

        while True:
            await asyncio.sleep(300)  # Wait for 5 minutes
            print("Check/update files now")
            # current_files = set(os.listdir(directory_to_watch))

            # new_files = current_files - seen_files
            # if new_files:
            #     print(f"New files detected: {new_files}")
            #     seen_files = current_files  # Update the seen files


    def saveAndQuit(self):
        with open("settings.txt", "w") as f:
            f.write("Folder_location: ")
            f.write(self.LogFileDialog.FileNamelineEdit.text())
            f.write("\nLoad_time_selection: ")
            f.write(str(int(self.actionAll.isChecked()))
                + str(int(self.action1_Day.isChecked()))
                + str(int(self.action1_Week.isChecked()))
                + str(int(self.action1_Month.isChecked()))
                + str(int(self.action100_Days.isChecked())))
            f.write("\nTable_size: ")
            f.write(str(int(self.action9pt_2.isChecked()))
                + str(int(self.action10pt_2.isChecked()))
                + str(int(self.action12pt_2.isChecked()))
                + str(int(self.action16pt_2.isChecked()))
                + str(int(self.action24pt_2.isChecked())))
            f.write("\nHide_resources: ")
            f.write(str(int(self.actionHide_Finished_Resources.isChecked())))
            f.write("\nHide_total_need: ")
            f.write(str(int(self.actionHide_total_need.isChecked())))
            f.write("\nGet_stats: ")
            f.write(str(int(self.actionload_stats.isChecked())))

            with open("stationList.pickle", 'wb') as st:
                pickle.dump(self.uniqueStations, st)
        sys.exit()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    uIWindow = UI()
    print("In main function")
    uIWindow.displayColony()
    # asyncio.run(uIWindow.check_for_new_files())
    app.exec()
