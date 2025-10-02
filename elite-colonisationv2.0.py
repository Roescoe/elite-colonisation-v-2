from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import *
from PyQt6 import uic, QtGui
import sys
import os
import platform
import json
import ast
import time
import copy
import pickle
import ctypes

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
        uic.loadUi('elite-colonisationv2.0.ui', self)
        self.setWindowIcon(QtGui.QIcon('ColoniseLogo.png'))
        app.setWindowIcon(QtGui.QIcon('ColoniseLogo.png'))
        self.show()
        self.LogFileDialog = LogFileDialogClass()

        self.actionSet_logfile_location.triggered.connect(lambda:self.showLogfileDialog())
        self.actionAll.triggered.connect(lambda:self.setLogfileLoadRange(0))
        self.action1_Day.triggered.connect(lambda:self.setLogfileLoadRange(1))
        self.action1_Week.triggered.connect(lambda:self.setLogfileLoadRange(2))
        self.action1_Month.triggered.connect(lambda:self.setLogfileLoadRange(3))
        self.action100_Days.triggered.connect(lambda:self.setLogfileLoadRange(4))

        self.actionQuit.triggered.connect(lambda:self.saveAndQuit())

        self.getFileSettings()

    def showLogfileDialog(self):
        print("showing log file now... ", type(self.LogFileDialog))
        self.LogFileDialog.exec()

    def setLogfileLoadRange(self, logfileRange):
        self.olderThanNumDays = 0
        currentTime = time.time()

        self.actionAll.setChecked(False)
        self.action1_Day.setChecked(False)
        self.action1_Week.setChecked(False)
        self.action1_Month.setChecked(False)
        self.action100_Days.setChecked(False)
        print("The time situation: ", logfileRange)

        match logfileRange:
            case 0:
                self.olderThanNumDays = 0
                self.actionAll.setChecked(True)
            case 1:
                self.olderThanNumDays = currentTime - 3600*24*1
                self.action1_Day.setChecked(True)
            case 2:
                self.olderThanNumDays = currentTime - 3600*24*7
                self.action1_Week.setChecked(True)
            case 3:
                self.olderThanNumDays = currentTime - 3600*24*30
                self.action1_Month.setChecked(True)
            case 4:
                self.olderThanNumDays = currentTime - 3600*24*100
                self.action100_Days.setChecked(True)
            case _:
                self.olderThanNumDays = 0
        return self.olderThanNumDays

    def getFileSettings(self):
        if os.path.exists("settings.txt"):
            with open("settings.txt", "r") as f:
                testFileLine = f.readlines()
                for line in testFileLine:
                    if line.startswith("Load_time_selection:"):
                        print("Found time in settings")
                        loadTimeSelect = int(line.split("Load_time_selection: ",1)[1].strip())
                        print("Loading from time:", loadTimeSelect)
                        match loadTimeSelect:
                            case 10000:
                                self.actionAll.setChecked(True)
                            case 1000:
                                self.action1_Day.setChecked(True)
                            case 100:
                                self.action1_Week.setChecked(True)
                            case 10:
                                self.action1_Month.setChecked(True)
                            case 1:
                                self.action100_Days.setChecked(True)
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
                    if line.startswith("Table_size:"):
                        print("Found table size in settings")
                        if isinstance(int(line.split("Table_size: ",1)[1].strip()), int):
                            tableSizeIndex = int(line.split("Table_size: ",1)[1].strip())
                            #set actions, action12pt_2, action14pt_2, action16pt_2, action20pt_2, action32pt_2

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
            f.write("\nHide_resources: ")
            f.write(str(int(self.actionHide_Finished_Resources.isChecked())))
            f.write("\nHide_notes: ")
            f.write(str(int(self.actionHide_Notes.isChecked())))
        sys.exit()



if __name__ == '__main__':
    app = QApplication(sys.argv)
    uIWindow = UI()
    app.exec()