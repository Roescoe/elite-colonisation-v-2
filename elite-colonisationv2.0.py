from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import *
from PyQt6 import uic, QtGui
import sys
import os
import platform
import ctypes
import json
import ast
import time
from operator import itemgetter
import pickle
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
        self.tempCount = 0 #delete me!!!!

        #initialize windows
        uic.loadUi('elite-colonisationv2.0.ui', self)
        self.setWindowIcon(QtGui.QIcon('ColoniseLogo.png'))
        app.setWindowIcon(QtGui.QIcon('ColoniseLogo.png'))
        self.show()
        self.LogFileDialog = LogFileDialogClass()
        self.getFileSettings()

        #set up stuff
        self.getLogFileData()
        self.populateStationList()
        # print(self.uniqueStations)

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
        self.stationList.currentIndexChanged.connect(lambda:self.displayColony(self.stationList.currentIndex()))
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

    def getFileSettings(self):
        loadTimeSelect = 0
        if os.path.exists("settings.txt"):
            with open("settings.txt", "r") as f:
                testFileLine = f.readlines()
                for line in testFileLine:
                    if line.startswith("Load_time_selection:"):
                        print("Found time in settings")
                        loadTimeSelect = int(line.split("Load_time_selection: ",1)[1].strip())
                        print("Loading from time:", loadTimeSelect)
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
        for printMeNow in logFileListSortedPairs:
            print("logFileListSortedPairs: ",printMeNow[1].split("Journal.",1)[1])
        self.logfiles.sort(reverse = True)
        for logfile in self.logfiles:
            print("self.logfiles: ",logfile.split("Journal.",1)[1])

    def readLogFile(self, logfile):
        # TODO only call on first pass or pass only latest file
        self.getAllLogFileData(logfile)




    def getAllLogFileData(self, logfile):
        isUnique = True
        print("Reading logfile: ", logfile.split("Journal.",1)[1])
        with open(logfile, "r", encoding='iso-8859-1') as f1, open("importantLogs.txt","w", encoding='iso-8859-1') as f2:
            for line in f1:
                rawLine = json.loads(line)
                # print("LogFile: ",logfile)
                if "ConstructionProgress" in rawLine:
                    # print("Found a construction landing")
                    f2.write(str(rawLine)+'\n')
                if "Loadout" in rawLine.values():
                    print("Found a ship")
                    f2.write(str(rawLine)+'\n')
                if "Docked" in rawLine.values():
                    isUnique = True
                    for stationIndex, station in enumerate(self.uniqueStations):
                        print()
                        if rawLine["MarketID"] == station[0]:
                            print("Found same")
                            print("The station list: ",self.uniqueStations[stationIndex])
                            # self.uniqueStations[stationIndex][2] = rawLine["timestamp"]
                            isUnique = False
                            break
                    if isUnique == True:
                        if rawLine["StationName"].startswith("$EXT_PANEL_"):
                            cleanStationName = rawLine["StarSystem"] + ": " + rawLine["StationName"].split("$EXT_PANEL_",1)[1] 
                        else:    
                            cleanStationName = rawLine["StationName"]
                        self.uniqueStations.append([rawLine["MarketID"], cleanStationName, rawLine["timestamp"]])

          



        with open("stationList.pickle", 'wb') as st:
            pickle.dump(self.uniqueStations, st)

        self.populateStationList()

    def populateStationList(self):
        self.stationList.clear()
        if self.uniqueStations:
            for station in self.uniqueStations:
                self.stationList.addItem(str(station[1]))

    def displayColony(self, selectedColony):

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
        sys.exit()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    uIWindow = UI()
    app.exec()