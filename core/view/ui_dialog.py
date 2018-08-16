# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'dialog.ui'
#
# Created by: PyQt5 UI code generator 5.11.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.setWindowModality(QtCore.Qt.ApplicationModal)
        Dialog.resize(400, 165)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/picture/res/main.ico"), QtGui.QIcon.Normal, QtGui.QIcon.On)
        Dialog.setWindowIcon(icon)
        self.vboxlayout = QtWidgets.QVBoxLayout(Dialog)
        self.vboxlayout.setObjectName("vboxlayout")
        self.label = QtWidgets.QLabel(Dialog)
        self.label.setObjectName("label")
        self.vboxlayout.addWidget(self.label)
        self.label_2 = QtWidgets.QLabel(Dialog)
        self.label_2.setObjectName("label_2")
        self.vboxlayout.addWidget(self.label_2)
        self.label_3 = QtWidgets.QLabel(Dialog)
        self.label_3.setObjectName("label_3")
        self.vboxlayout.addWidget(self.label_3)
        self.label_6 = QtWidgets.QLabel(Dialog)
        self.label_6.setObjectName("label_6")
        self.vboxlayout.addWidget(self.label_6)
        self.label_4 = QtWidgets.QLabel(Dialog)
        self.label_4.setObjectName("label_4")
        self.vboxlayout.addWidget(self.label_4)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "关于"))
        self.label.setText(_translate("Dialog", "版本： 0.1.0"))
        self.label_2.setText(_translate("Dialog", "架构： x64"))
        self.label_3.setText(_translate("Dialog", "构建时间： 2018-08-20"))
        self.label_6.setText(_translate("Dialog", "Python: 3.6.6"))
        self.label_4.setText(_translate("Dialog", "Email: guobao.v@gmail.com"))


