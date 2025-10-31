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
        uic.loadUi('logfile-select.ui', self)

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
        self.lastMarketEntry = {}
        self.fleetCarrierMarket = []
        self.tableLabels = []
        self.ships = []

        #initialize windows
        uic.loadUi('elite-colonisationv2.0.ui', self)
        self.setWindowIcon(QtGui.QIcon('ColoniseLogo.png'))
        app.setWindowIcon(QtGui.QIcon('ColoniseLogo.png'))
        self.show()
        self.LogFileDialog = LogFileDialogClass()

        #set up stuff
        self.getFileSettings()
        self.getLogFileData()
        self.setGoodsList()
        self.populateShipList()
        self.displayColony()

        # loop = asyncio.new_event_loop()
        # asyncio.set_event_loop(loop)
        # loop.create_task(self.monitor_directory())
        # loop.run_forever()



        #buttons
        self.actionSet_logfile_location.triggered.connect(lambda:self.showLogfileDialog())
        self.actionAll.triggered.connect(lambda:self.setLogfileLoadRange(10000))
        self.action1_Day.triggered.connect(lambda:self.setLogfileLoadRange(1000))
        self.action1_Week.triggered.connect(lambda:self.setLogfileLoadRange(100))
        self.action1_Month.triggered.connect(lambda:self.setLogfileLoadRange(10))
        self.action100_Days.triggered.connect(lambda:self.setLogfileLoadRange(1))
        self.action9pt_2.triggered.connect(lambda:self.setTextSize(10000))
        self.action10pt_2.triggered.connect(lambda:self.setTextSize(1000))
        self.action12pt_2.triggered.connect(lambda:self.setTextSize(100))
        self.action16pt_2.triggered.connect(lambda:self.setTextSize(10))
        self.action24pt_2.triggered.connect(lambda:self.setTextSize(1))
        self.actionHide_total_need.triggered.connect(lambda:self.updateTableDisplay())
        self.actionHide_carrier_cargo.triggered.connect(lambda:self.updateTableDisplay())
        self.actionHide_Finished_Resources.triggered.connect(lambda:self.displayColony())
        self.stationList.currentIndexChanged.connect(lambda:self.displayColony())
        self.shipList.currentIndexChanged.connect(lambda:self.displayColony())
        self.update.clicked.connect(lambda:self.getLogFileData())
        self.actionload_stats.triggered.connect(lambda:self.getScsStats())


        self.actionQuit.triggered.connect(lambda:self.saveAndQuit())

    def showLogfileDialog(self):
        print("showing log file now... ")
        self.LogFileDialog.exec()
        if not os.path.isdir(self.LogFileDialog.FileNamelineEdit.text()):
            print("Invalid file path")
            self.LogFileDialog.FileNamelineEdit.setText("")


    def setLogfileLoadRange(self, loadTimeSelect):
        
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
        self.getLogFileData()

    def setTextSize(self,textsize):

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
        if os.path.exists("settings.txt"):
            with open("settings.txt", "r") as f:
                testFileLine = f.readlines()
                for line in testFileLine:
                    if line.startswith("Load_time_selection:"):
                        print("Found time in settings")
                        loadTimeSelect = int(line.split("Load_time_selection: ",1)[1].strip())
                        print("Loading from time:", loadTimeSelect)
                        if loadTimeSelect:
                            self.setLogfileLoadRange(loadTimeSelect)
                    if line.startswith("Table_size:"):
                        print("Found table size in settings")
                        if isinstance(int(line.split("Table_size: ",1)[1].strip()), int):
                            tableSizeIndex = int(line.split("Table_size: ",1)[1].strip())
                    if line.startswith("Hide_resources:"):
                        print("Found checkbox in settings \'"+ line.split("Hide_resources: ",1)[1].strip()+"\'")
                        if isinstance(int(line.split("Hide_resources: ",1)[1].strip()), int):
                            hideBoxIsChecked = bool(int(line.split("Hide_resources: ",1)[1].strip()))
                            self.actionHide_Finished_Resources.setChecked(hideBoxIsChecked)
                    if line.startswith("Hide_carrier_cargo:"):
                        print("Found checkbox in settings \'"+ line.split("Hide_carrier_cargo: ",1)[1].strip()+"\'")
                        if isinstance(int(line.split("Hide_carrier_cargo: ",1)[1].strip()), int):
                            hideBoxIsChecked = bool(int(line.split("Hide_carrier_cargo: ",1)[1].strip()))
                            self.actionHide_carrier_cargo.setChecked(hideBoxIsChecked)
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
        print("Starting logfile gathering")
        self.findLogfiles()
        for logfile in self.logfiles:
            self.getAllLogFileData(logfile)
        self.saveColonies("importantLogs.txt")
        self.populateStationList()

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
        stationType = "other"

        print("Reading logfile: ", logfile.split("Journal.",1)[1])
        with open(logfile, "r", encoding='iso-8859-1') as f1, open("ships.txt","w", encoding='iso-8859-1') as f3:
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

                    # f2.write(str(rawLine)+'\n')
                if "Loadout" in rawLine.values() and int(rawLine["CargoCapacity"]) > 0:
                    # print("Found a ship")
                    f3.write(str(rawLine)+'\n')
                if "Docked" in rawLine.values():
                    isUnique = True
                    for station in self.uniqueStations:
                        if str(rawLine["MarketID"]) == str(station[0]):
                            isUnique = False
                            break
                    if isUnique == True:
                        if rawLine["StationName"].startswith("$EXT_PANEL_"):
                            cleanStationName = rawLine["StarSystem"] + ": " + rawLine["StationName"].split("$EXT_PANEL_",1)[1] + " (" + str(rawLine["MarketID"])+")"
                        else:    
                            cleanStationName = rawLine["StationName"] + " (" + str(rawLine["MarketID"])+")"
                        print("Saving " +cleanStationName+" to data struc")
                        if rawLine["StationType"] == "SurfaceStation" or rawLine["StationType"] == "SpaceConstructionDepot":
                            if "StationState" in rawLine:
                                stationType = "constructed"
                            else:
                                stationType = "colony"
                        elif rawLine["StationType"] == "FleetCarrier":
                            stationType = "fleet"
                        else:
                            stationType = "other"
                        # Station format: ID, Name, time accessed, type
                        self.uniqueStations.append([rawLine["MarketID"], cleanStationName, rawLine["timestamp"], stationType])

        self.lastFileName = logfile

    def saveColonies(self, outputFile):
        with open(outputFile,"w", encoding='iso-8859-1') as f2:
            for colony in self.colonies:
                f2.write(str(colony)+'\n')

    def populateStationList(self):
        # print("Stations and timeStamps: ",self.uniqueStations)
        if self.uniqueStations:
            self.uniqueStations = sorted(self.uniqueStations, key=lambda station:station[2], reverse=True)
            savedIndex = self.stationList.currentIndex()
            self.stationList.clear()
            for station in self.uniqueStations:
                if self.eliteFileTime < station[2]:
                    if station[3] == "colony":
                        self.stationList.addItem(str(station[1]))
            print("Index of current colony: ", savedIndex)
            if savedIndex == -1:
                self.stationList.setCurrentIndex(0)
            else:
                self.stationList.setCurrentIndex(savedIndex)


    def populateShipList(self):
        print("Getting Ships...")
        if os.path.exists("ships.txt"):
            with open("ships.txt","r", encoding='iso-8859-1') as f:
                for line in f:
                    rawLine = ast.literal_eval(line)
                    if "CargoCapacity" in rawLine:
                        if rawLine["CargoCapacity"] not in self.ships:
                            self.ships.append([rawLine["ShipIdent"],rawLine["CargoCapacity"],rawLine["timestamp"]])
        print(f"All the ships: {self.ships}")
        if self.ships:
            self.ships.sort(key=lambda ship:ship[2], reverse=True)

            for ship in self.ships:
                items = [self.shipList.itemText(i) for i in range(self.shipList.count())]
                if str(ship[1]) not in str(items):
                    self.shipList.addItem(str(f"{ship[0]} ({ship[1]})"))
        if self.shipList:
            current_ship = self.shipList.currentText()
            self.cargoSpace.setText(current_ship.split("(",1)[1].split(")",1)[0])
        print("Got Ships.")

    def updateTableDisplay(self):
        if self.actionHide_total_need.isChecked():
            self.resourceTableList.setColumnHidden(self.tableLabels.index("Total Need"), True)
        else:
            self.resourceTableList.setColumnHidden(self.tableLabels.index("Total Need"), False)
        if self.actionHide_carrier_cargo.isChecked():
            self.resourceTableList.setColumnHidden(self.tableLabels.index("Carrier Need"), True)
        else:
            self.resourceTableList.setColumnHidden(self.tableLabels.index("Carrier Need"), False)

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

    def findMarketEntry(self, selectedMarketID, sourceFile):
        foundEntry = False
        self.lastMarketEntry.clear()
        if os.path.exists(sourceFile):
            with open(sourceFile,"r", encoding='iso-8859-1') as f:
                for line in f:
                    dictLine = ast.literal_eval(line)
                    # for station in self.uniqueStations:
                    if "MarketID" in dictLine:
                        # print("Reading from station: ", type(dictLine["MarketID"]))
                        if dictLine["MarketID"] == selectedMarketID:
                            if self.lastMarketEntry:
                                if dictLine["timestamp"] > self.lastMarketEntry["timestamp"]:
                                    self.lastMarketEntry = dictLine
                                    foundEntry = True
                            else:
                                self.lastMarketEntry = dictLine
                                foundEntry = True
        print(f"The entry we're using: {self.lastMarketEntry} was updated? {foundEntry}")
        return foundEntry

    def findFleetCarrierEntry(self, fleetCarrier, sourceFile):
        pass

    def setupResourceTable(self):
        qTypeItems = []
        qResourceItems = []
        qAmountItems = []
        qCurrentItems = []
        qTripItems = []
        qFleetCarrier = []
        cargo = 0
        doneState = -1

        if len(self.shipList) > 0:
            cargo = int(self.cargoSpace.text())
        self.resourceTableList.clear()
        self.tableLabels.clear()

        print("Latest Entry:", self.lastMarketEntry)
        if "ResourcesRequired" in self.lastMarketEntry:
            print(f'Num resources listed: {len(self.lastMarketEntry["ResourcesRequired"])}')
            for i in range(len(self.lastMarketEntry["ResourcesRequired"])):
                
                total_need = self.lastMarketEntry["ResourcesRequired"][i]["RequiredAmount"]
                current_provided = self.lastMarketEntry["ResourcesRequired"][i]["ProvidedAmount"]
                current_need = int(total_need) - int(current_provided)
                if cargo == 0:
                    trips_remaining = 0
                else:
                    trips_remaining = round(current_need/cargo, 1)

                if current_need == 0 and self.actionHide_Finished_Resources.isChecked():
                    continue

                qTypeItem = QTableWidgetItem()
                qResourceItem = QTableWidgetItem()
                qAmountItem = QTableWidgetItem()
                qCurrentItem = QTableWidgetItem()
                qTripItem = QTableWidgetItem()
                

                qTypeItem.setText(str(self.resourceTypeDict[self.lastMarketEntry["ResourcesRequired"][i]["Name_Localised"]]))
                qResourceItem.setText(str(self.lastMarketEntry["ResourcesRequired"][i]["Name_Localised"]))
                qAmountItem.setText(f"{total_need:,}".rjust(7))
                qTripItem.setText(str(trips_remaining).rjust(7))

                print(f"The need: {int(current_need)} The total: {int(total_need)}")
                if int(current_need) == 0:
                    doneState = 1
                    qCurrentItem.setText("Done")
                    qCurrentItem.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                elif(int(current_need) == int(total_need)):
                    doneState = -1
                    qCurrentItem.setText(f"{current_need:,}".rjust(7))
                    qCurrentItem.setTextAlignment(Qt.AlignmentFlag.AlignRight)
                else:
                    doneState = 0
                    qCurrentItem.setText(f"{current_need:,}".rjust(7))
                    qCurrentItem.setTextAlignment(Qt.AlignmentFlag.AlignRight)

                qTypeItem.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                qResourceItem.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                qAmountItem.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                qCurrentItem.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                qTripItem.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)

                qAmountItem.setTextAlignment(Qt.AlignmentFlag.AlignRight)
                qTripItem.setTextAlignment(Qt.AlignmentFlag.AlignRight)

                qTypeItems.append(qTypeItem)
                qResourceItems.append(qResourceItem)
                qAmountItems.append(qAmountItem)
                qCurrentItems.append([qCurrentItem, doneState])
                qTripItems.append(qTripItem)


        self.tableLabels.append("Category")
        self.tableLabels.append("Resource")
        self.tableLabels.append("Total Need")
        self.tableLabels.append("Current Need")
        self.tableLabels.append("Trips Remaining")
        self.tableLabels.append("Carrier Need")
        self.resourceTableList.setRowCount(len(self.lastMarketEntry["ResourcesRequired"]))
        self.resourceTableList.setColumnCount(len(self.tableLabels))
        print(f"tableLabels: {self.tableLabels}")

        currentColumn = 0
        for i, qResource in enumerate(qResourceItems):
            self.resourceTableList.setItem(i, self.tableLabels.index("Category"), qTypeItems[i])
            self.resourceTableList.setItem(i, self.tableLabels.index("Resource"), qResource)
            self.resourceTableList.setItem(i, self.tableLabels.index("Total Need"), qAmountItems[i])
            needIndex = self.tableLabels.index("Current Need")
            self.resourceTableList.setItem(i, needIndex, qCurrentItems[i][0])
            if qCurrentItems[i][1] == 1:
                self.resourceTableList.item(i, needIndex).setBackground(QColor("green"))
            elif qCurrentItems[i][1] == -1:
                self.resourceTableList.item(i, needIndex).setBackground(QColor("#c32148"))
            elif qCurrentItems[i][1] == 0:
                self.resourceTableList.item(i, needIndex).setBackground(QColor("#281E5D"))
            self.resourceTableList.setItem(i, self.tableLabels.index("Trips Remaining"), qTripItems[i])
        self.resourceTableList.setHorizontalHeaderLabels(self.tableLabels)

        # self.resourceTableList.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # self.resourceTableList.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # self.resourceTableList.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)

    def formatResourceTable(self):
        print("Formatting table...")
        for i in range(self.resourceTableList.rowCount()):
            self.resourceTableList.setRowHeight(i, self.allTextSize+15)
        self.resourceTableList.setFont(QFont('Calibri',self.allTextSize))
        self.resourceTableList.setColumnWidth(self.tableLabels.index("Category"), int(13 * self.allTextSize))
        self.resourceTableList.setColumnWidth(self.tableLabels.index("Resource"), int(18 * self.allTextSize))
        self.resourceTableList.setColumnWidth(self.tableLabels.index("Total Need"), int(7 * self.allTextSize))
        self.resourceTableList.setColumnWidth(self.tableLabels.index("Current Need"), int(8 * self.allTextSize))
        self.resourceTableList.setColumnWidth(self.tableLabels.index("Trips Remaining"), int(9 * self.allTextSize))
        self.resourceTableList.setColumnWidth(self.tableLabels.index("Carrier Need"), int(15 * self.allTextSize))
        self.resourceTableList.verticalHeader().setVisible(False)
        self.resourceTableList.setSortingEnabled(True)
        self.resourceTableList.horizontalHeader().setStyleSheet(f"color: snow; font-size: {self.allTextSize}px; font-weight: bold; background-color: rgb(20, 28, 160)")

        self.scrollArea.setWidget(self.resourceTableList)

    def displayColonyStats(self):
        tripsCalc = 0
        percentPerTrip = 0
        totalMaterials = 0
        stillNeeded = 0
        percentComplete = 0

        print("Calculating various stats...")

        if self.resourceTableList:
            for trip in range(self.resourceTableList.rowCount()):
                if "Trips Remaining" in self.tableLabels:
                    tripsCalc += float(self.resourceTableList.item(trip, 4).text())
                if self.resourceTableList.item(trip, 2):
                    totalMaterials += int(self.resourceTableList.item(trip, 2).text().replace(',', ''))
                if self.resourceTableList.item(trip, 3) and self.resourceTableList.item(trip, 3).text() != "Done":
                    stillNeeded += int(self.resourceTableList.item(trip, 3).text().replace(',', ''))
        tripsCalc = round(tripsCalc, 2)

        if totalMaterials > 0:
            percentPerTrip = round(100 * int(self.cargoSpace.text()) / totalMaterials, 2)
        if stillNeeded > 0:
            percentComplete = round(100 * (1 - stillNeeded/totalMaterials), 2)


        self.trips_left.setFont(QFont('Calibri',14))
        self.percent_per_trip.setFont(QFont('Calibri',14))
        self.total_materials.setFont(QFont('Calibri',14))
        self.materials_still_needed.setFont(QFont('Calibri',14))
        self.percent_complete.setFont(QFont('Calibri',14))

        self.trips_left.setText(f"Trips left: {tripsCalc}")
        self.percent_per_trip.setText(f"Percent per Trip: {percentPerTrip}%")
        self.total_materials.setText(f"Total Materials: {totalMaterials:,}")
        self.materials_still_needed.setText(f"Materials Still Needed: {stillNeeded:,}")
        self.percent_complete.setText(f"Percent Complete: {percentComplete}%")

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
                timeAgo = 0
            case 1000:
                timeAgo = 24*1
            case 100:
                timeAgo = 24*7
            case 10:
                timeAgo = 24*30
            case 1:
                timeAgo = 24*100

        formatted_time = datetime.now(timezone.utc) - timedelta(hours = timeAgo)
        formatted_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        print("Time now: ", formatted_time)
        self.eliteFileTime = str(formatted_time)
    def setGoodsList(self):
        with open("Market.json", "r", encoding='iso-8859-1') as f:
            testFileLine = json.load(f)

        for i in testFileLine["Items"]:
            if "Name_Localised" in i and "Category_Localised" in i:
                self.resourceTypeDict[i["Name_Localised"]] = i["Category_Localised"]

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
            f.write("\nHide_carrier_cargo: ")
            f.write(str(int(self.actionHide_carrier_cargo.isChecked())))
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
    # asyncio.run(uIWindow.check_for_new_files())
    app.exec()
