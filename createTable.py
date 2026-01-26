from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import *
import json
from collections import OrderedDict

class createTable():
    def __init__(self, lastMarketEntry, cargoSpace):
        self.marketEntry = lastMarketEntry
        self.resourceTypeDict = {}
        self.resourceTableRows = OrderedDict()
        self.cargo = cargoSpace

        self.setGoodsList()
        self.create()

    def create(self):
        resourceOrder = []
        activeResources = []
        doneState = -1

        for i in range(len(self.marketEntry["ResourcesRequired"])):
            
            total_need = self.marketEntry["ResourcesRequired"][i]["RequiredAmount"]
            current_provided = self.marketEntry["ResourcesRequired"][i]["ProvidedAmount"]
            current_need = int(total_need) - int(current_provided)
            if self.cargo == 0:
                trips_remaining = 0
            else:
                trips_remaining = round(current_need/self.cargo, 1)

            qTypeItem = QTableWidgetItem()
            qResourceItem = QTableWidgetItem()
            qAmountItem = QTableWidgetItem()
            qCurrentItem = QTableWidgetItem()
            qTripItem = QTableWidgetItem()
            

            qTypeItem.setText(str(self.resourceTypeDict[self.marketEntry["ResourcesRequired"][i]["Name_Localised"]]))
            qResourceItem.setText(str(self.marketEntry["ResourcesRequired"][i]["Name_Localised"]))
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

            self.resourceTableRows[qResourceItem.text()] = (qTypeItem,qResourceItem,qAmountItem,[qCurrentItem, doneState],qTripItem)
            print(f"The row tuple to print: {qTypeItem.text()}, {qResourceItem.text()}, {qAmountItem.text()}, [{qCurrentItem.text()}, {doneState}], {qTripItem.text()}")

    def setGoodsList(self):
        with open("MarketLines.json", "r", encoding='iso-8859-1') as f:
            testFileLine = json.load(f)

        for i in testFileLine:
            if "Name_Localised" in i and "Category_Localised" in i:
                self.resourceTypeDict[i["Name_Localised"]] = i["Category_Localised"]
        # print(f"All the resources: {self.resourceTypeDict}")
    def getRows(self):
        return self.resourceTableRows
