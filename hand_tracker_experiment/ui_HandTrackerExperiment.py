# Form implementation generated from reading ui file 'h:\Проекты\Для лабы\HandsTracker\HandTrackerExperiment\ui_HandTrackerExperiment.ui'
#
# Created by: PyQt6 UI code generator 6.4.2
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_HandTrackerExperiment(object):
    def setupUi(self, HandTrackerExperiment):
        HandTrackerExperiment.setObjectName("HandTrackerExperiment")
        HandTrackerExperiment.resize(482, 426)
        self.verticalLayout = QtWidgets.QVBoxLayout(HandTrackerExperiment)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.tabWidget = QtWidgets.QTabWidget(parent=HandTrackerExperiment)
        self.tabWidget.setTabPosition(QtWidgets.QTabWidget.TabPosition.North)
        self.tabWidget.setDocumentMode(False)
        self.tabWidget.setMovable(False)
        self.tabWidget.setTabBarAutoHide(False)
        self.tabWidget.setObjectName("tabWidget")
        self.tab_2 = QtWidgets.QWidget()
        self.tab_2.setObjectName("tab_2")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.tab_2)
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_3.setSpacing(0)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.capture_base_image_btn = QtWidgets.QPushButton(parent=self.tab_2)
        self.capture_base_image_btn.setObjectName("capture_base_image_btn")
        self.verticalLayout_3.addWidget(self.capture_base_image_btn)
        self.default_image = LabelImage(parent=self.tab_2)
        self.default_image.setText("")
        self.default_image.setObjectName("default_image")
        self.verticalLayout_3.addWidget(self.default_image)
        self.tabWidget.addTab(self.tab_2, "")
        self.tab = QtWidgets.QWidget()
        self.tab.setObjectName("tab")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.tab)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.controls = ExperimentControlWidget(parent=self.tab)
        self.controls.setObjectName("controls")
        self.verticalLayout_2.addWidget(self.controls)
        self.tabWidget.addTab(self.tab, "")
        self.verticalLayout.addWidget(self.tabWidget)

        self.retranslateUi(HandTrackerExperiment)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(HandTrackerExperiment)

    def retranslateUi(self, HandTrackerExperiment):
        _translate = QtCore.QCoreApplication.translate
        HandTrackerExperiment.setWindowTitle(_translate("HandTrackerExperiment", "Эксперимент: отслеживание руки"))
        self.capture_base_image_btn.setText(_translate("HandTrackerExperiment", "Заснять базовое изображение"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), _translate("HandTrackerExperiment", "Изображение по умолчанию"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), _translate("HandTrackerExperiment", "Настройка и управление"))
from forms.experiment_control_widget import ExperimentControlWidget
from forms.label_image import LabelImage
