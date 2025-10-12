from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import *
from PyQt6 import uic, QtGui
from PyQt6.QtGui import QFont
import sys
import os
import platform
import ctypes
import json
import ast
import time
from operator import itemgetter
import pickle
from datetime import datetime, timezone, timedelta
from threading import Timer
import glob
# import copy

# This is a tool to print out Elite Dangerous colonization data pulled from the user's logfiles
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

def watch_file(filename, time_limit=3600, check_interval=60):
    """Return true if filename exists, if not keep checking once every check_interval seconds for time_limit seconds.
    time_limit defaults to 1 hour
    check_interval defaults to 1 minute
    """
    now = time.time()
    last_time = now + time_limit
    
    while time.time() <= last_time:
        if os.path.exists(filename):
            return True
        else:
            # Wait for check interval seconds, then check again.
            time.sleep(check_interval)
    return False

class RepeatedTimer(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer     = None
        self.interval   = interval
        self.function   = function
        self.args       = args
        self.kwargs     = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False

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
        self.allTextSize = 0
        self.logfiles = []
        self.uniqueStations = []
        self.colonies = []
        self.eliteFileTime = 0
        self.lastFileName = ''
        self.resourceTypeDict = {}
        self.resourceTableView = QTableView()
        self.resourceTableList = QTableWidget()

        #initialize windows
        uic.loadUi('elite-colonisationv2.0.ui', self)
        self.setWindowIcon(QtGui.QIcon('ColoniseLogo.png'))
        app.setWindowIcon(QtGui.QIcon('ColoniseLogo.png'))
        self.show()
        self.LogFileDialog = LogFileDialogClass()
        self.getFileSettings()

        #set up stuff
        self.getLogFileData()
        self.setGoodsList()
        self.getScsStats()
        self.displayColony(self.stationList.currentText())

        # rt = RepeatedTimer(60, self.monitor_directory) # it auto-starts, no need of rt.start()
        # try:
        #     time.sleep(5) # your long-running job goes here...
        # finally:
        #     rt.stop() # better in a try/finally block to make sure the program ends!
        # self.thread = Thread(target=self.monitor_directory)
        # self.thread.start()
        # self.populateStationList()


        #buttons
        self.actionSet_logfile_location.triggered.connect(lambda:self.showLogfileDialog())
        self.actionAll.triggered.connect(lambda:self.setLogfileLoadRange(10000))
        self.action1_Day.triggered.connect(lambda:self.setLogfileLoadRange(1000))
        self.action1_Week.triggered.connect(lambda:self.setLogfileLoadRange(100))
        self.action1_Month.triggered.connect(lambda:self.setLogfileLoadRange(10))
        self.action100_Days.triggered.connect(lambda:self.setLogfileLoadRange(1))
        self.action12pt_2.triggered.connect(lambda:self.setTextSize(10000))
        self.action14pt_2.triggered.connect(lambda:self.setTextSize(1000))
        self.action16pt_2.triggered.connect(lambda:self.setTextSize(100))
        self.action20pt_2.triggered.connect(lambda:self.setTextSize(10))
        self.action32pt_2.triggered.connect(lambda:self.setTextSize(1))
        self.actionHide_Finished_Resources.triggered.connect(lambda:self.displayColony(self.stationList.currentText()))
        self.stationList.currentIndexChanged.connect(lambda:self.displayColony(self.stationList.currentText()))

        self.actionQuit.triggered.connect(lambda:self.saveAndQuit())

    def showLogfileDialog(self):
        print("showing log file now... ")
        self.LogFileDialog.exec()

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
        self.populateStationList()
        self.displayColony(self.stationList.currentText())

    def setTextSize(self,textsize):

        self.action12pt_2.setChecked(False)
        self.action14pt_2.setChecked(False)
        self.action16pt_2.setChecked(False)
        self.action20pt_2.setChecked(False)
        self.action32pt_2.setChecked(False)

        match textsize:
            case 10000:
                self.action12pt_2.setChecked(True)
                self.allTextSize = 12
            case 1000:
                self.action14pt_2.setChecked(True)
                self.allTextSize = 14
            case 100:
                self.action16pt_2.setChecked(True)
                self.allTextSize = 16
            case 10:
                self.action20pt_2.setChecked(True)
                self.allTextSize = 20
            case 1:
                self.action32pt_2.setChecked(True)
                self.allTextSize = 32
            case _:
                self.action14pt_2 = 14
        self.formatResourceTable()

    def getFileSettings(self):

        self.deleteOldLogFile("importantLogs.txt")
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
                            self.setTextSize(tableSizeIndex)
                    if line.startswith("Hide_resources:"):
                        print("Found checkbox in settings \'"+ line.split("Hide_resources: ",1)[1].strip()+"\'")
                        if isinstance(int(line.split("Hide_resources: ",1)[1].strip()), int):
                            hideBoxIsChecked = bool(int(line.split("Hide_resources: ",1)[1].strip()))
                            self.actionHide_Finished_Resources.setChecked(hideBoxIsChecked)
                    if line.startswith("Hide_notes:"):
                        print("Found checkbox in settings \'"+ line.split("Hide_notes: ",1)[1].strip()+"\'")
                        if isinstance(int(line.split("Hide_notes: ",1)[1].strip()), int):
                            hideBoxIsChecked = bool(int(line.split("Hide_notes: ",1)[1].strip()))
                            self.actionHide_Notes.setChecked(hideBoxIsChecked)
                    if line.startswith("Get_stats:"):
                        if isinstance(int(line.split("Get_stats:",1)[1].strip()),int):
                            getStatsBoxIsChecked = bool(int(line.split("Get_stats: ",1)[1].strip()))
                            self.actionload_stats_on_start.setChecked(getStatsBoxIsChecked)

        if os.path.exists("stationList.pickle"):
            with open("stationList.pickle", 'rb') as st:
                self.uniqueStations = pickle.load(st)
            self.populateStationList()


    def getLogFileData(self):
        print("Starting logfile gathering")
        self.findLogfiles()
        for logfile in self.logfiles:
            self.readLogFile(logfile)
        

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
        self.logfiles.sort(reverse = True)
        # for logfile in self.logfiles:
        #     print("self.logfiles: ",logfile.split("Journal.",1)[1])
        self.lastFileName = self.logfiles[0]

    def readLogFile(self, logfile):
        # TODO only call on first pass or pass only latest file
        self.getAllLogFileData(logfile)

    def getAllLogFileData(self, logfile):
        isUnique = True
        stationType = "other"

        print("Reading logfile: ", logfile.split("Journal.",1)[1])
        with open(logfile, "r", encoding='iso-8859-1') as f1, open("importantLogs.txt","a", encoding='iso-8859-1') as f2:
            for line in f1:
                rawLine = json.loads(line)
                # print("LogFile: ",logfile)
                if "ConstructionProgress" in rawLine:
                    # print("Found a construction landing")
                    f2.write(str(rawLine)+'\n')
                if "Loadout" in rawLine.values():
                    # print("Found a ship")
                    f2.write(str(rawLine)+'\n')
                if "Docked" in rawLine.values():
                    isUnique = True
                    for stationIndex, station in enumerate(self.uniqueStations):
                        if rawLine["MarketID"] == station[0]:
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
        self.uniqueStations = sorted(self.uniqueStations, key=lambda station:self.uniqueStations[2])
        self.populateStationList()
        self.lastFileName = logfile

    def populateStationList(self):
        self.stationList.clear()
        if self.uniqueStations:
            for station in self.uniqueStations:
                if self.eliteFileTime < station[2]:
                    if station[3] == "colony":
                        self.stationList.addItem(str(station[1]))

    def displayColony(self, selectedColony):
        selectedMarketID = ""
        lastMarketEntry = {}
        qTypeItems = []
        qResourceItems = []
        qAmountItems = []
        qCurrentItems = []

        print("Filling out ", selectedColony)
        # self.clear_layout(self.resourcesLayout)
        if selectedColony:
            selectedMarketID = int(selectedColony.split("(",1)[1].split(")",1)[0])

        print("selected ID:"+str(selectedMarketID))
        if os.path.exists("importantLogs.txt"):
            with open("importantLogs.txt","r", encoding='iso-8859-1') as f:
                for line in f:
                    dictLine = ast.literal_eval(line)
                    # for station in self.uniqueStations:
                    # print("Reading from station: ", dictLine["MarketID"])
                    if "MarketID" in dictLine:
                        if dictLine["MarketID"] == selectedMarketID:
                            if lastMarketEntry:
                                if dictLine["timestamp"] > lastMarketEntry["timestamp"]:
                                    lastMarketEntry = dictLine
                            else:
                                lastMarketEntry = dictLine
        print("Latest Entry:", lastMarketEntry)
        if "ResourcesRequired" in lastMarketEntry:
            self.resourceTableList.setRowCount(len(lastMarketEntry["ResourcesRequired"]))
            self.resourceTableList.setColumnCount(5)
            print(f'The last one: {len(lastMarketEntry["ResourcesRequired"])}')
            for i in range(len(lastMarketEntry["ResourcesRequired"])):
                
                total_need = lastMarketEntry["ResourcesRequired"][i]["RequiredAmount"]
                current_provided = lastMarketEntry["ResourcesRequired"][i]["ProvidedAmount"]
                current_need = int(total_need) - int(current_provided)
                print(f"Provided {current_provided}, Needed {current_need}")
                if current_need == 0 and self.actionHide_Finished_Resources.isChecked():
                    continue

                qTypeItem = QTableWidgetItem()
                qResourceItem = QTableWidgetItem()
                qAmountItem = QTableWidgetItem()
                qCurrentItem = QTableWidgetItem()
                

                qTypeItem.setText(str(self.resourceTypeDict[lastMarketEntry["ResourcesRequired"][i]["Name_Localised"]]) + " " * 5)
                qResourceItem.setText(str(lastMarketEntry["ResourcesRequired"][i]["Name_Localised"]) + " " * 5)
                qAmountItem.setText(str(total_need) + " " * 5)
                qCurrentItem.setText(str(current_need) + " " * 5)

                qTypeItem.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                qResourceItem.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                qAmountItem.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                qCurrentItem.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)

                qTypeItems.append(qTypeItem)
                qResourceItems.append(qResourceItem)
                qAmountItems.append(qAmountItem)
                qCurrentItems.append(qCurrentItem)


        for i, qResource in enumerate(qResourceItems):
            self.resourceTableList.setItem(i, 0, qTypeItems[i])
            self.resourceTableList.setItem(i, 1, qResource)
            self.resourceTableList.setItem(i, 2, qAmountItems[i])
            self.resourceTableList.setItem(i, 3, qCurrentItems[i])
        # self.resourceTableList.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # self.resourceTableList.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # self.resourceTableList.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.formatResourceTable()

    def formatResourceTable(self):
        for i in range(self.resourceTableList.rowCount()):
            self.resourceTableList.setRowHeight(i, self.allTextSize+15)
        self.resourceTableList.setFont(QFont('Calibri',self.allTextSize))
        self.resourceTableList.setColumnWidth(0, 175)
        self.resourceTableList.setColumnWidth(1, 230)
        self.resourceTableList.setColumnWidth(2, 120)
        self.resourceTableList.horizontalHeader().setVisible(False)
        self.resourceTableList.verticalHeader().setVisible(False)
        self.resourcesLayout.setRowStretch(0, 1)
        self.resourcesLayout.setColumnStretch(0, 1)
        self.resourcesLayout.addWidget(self.resourceTableList,0,0)

    def clear_layout(self, layout):
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            print("Item to be deleted: ", item)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()  # Safely delete the widget
                layout.removeItem(item)  # Remove the item from the layout

    def monitor_directory(self):
        print("Checking for new file...")
        if(platform.system() == 'Windows'):
            defaultFileDir = os.path.expandvars(r"C:\Users\$USERNAME") + r'\Saved Games\Frontier Developments\Elite Dangerous'
        elif(platform.system() == 'Linux'):
            defaultFileDir = os.path.expanduser("~") + '/.local/share/Steam/steamapps/compatdata/359320/pfx/drive_c/users/steamuser/Saved Games/Frontier Developments/Elite Dangerous'
        expectedFile = time.strftime("%Y-%m-%dT%H", time.localtime())
        expectedFile =os.path.join(defaultFileDir, "Journal." + expectedFile + '*'+".log")

        print("Looking for file like: ", expectedFile)
        realFiles = glob.glob(expectedFile, recursive=False)
        if realFiles:
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
        if not self.actionload_stats_on_start.isChecked():
            return 0

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
            f.write(str(int(self.action12pt_2.isChecked()))
                + str(int(self.action14pt_2.isChecked()))
                + str(int(self.action16pt_2.isChecked()))
                + str(int(self.action20pt_2.isChecked()))
                + str(int(self.action32pt_2.isChecked())))
            f.write("\nHide_resources: ")
            f.write(str(int(self.actionHide_Finished_Resources.isChecked())))
            f.write("\nHide_notes: ")
            f.write(str(int(self.actionHide_Notes.isChecked())))
            f.write("\nGet_stats: ")
            f.write(str(int(self.actionload_stats_on_start.isChecked())))

            with open("stationList.pickle", 'wb') as st:
                pickle.dump(self.uniqueStations, st)
        sys.exit()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    uIWindow = UI()
    app.exec()
