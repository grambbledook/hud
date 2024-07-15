#include <QMainWindow>
#include <QGridLayout>
#include <QWidget>
#include <QSpacerItem>
#include <QSizePolicy>

#include "Labels.h"
#include "SelectDevicePanel.h"

#include <iostream>

#include "StyleSheets.h"

#include <iostream>
#include <qboxlayout.h>
#include <qevent.h>
#include <QListWidget>

SelectDevicePanel::SelectDevicePanel(
    const std::string &normal_icon_path,
    const std::string &highlighted_icon_path,
    QWidget *parent
) : QMainWindow(parent) {
    const auto selectIcon = new ClickableLabel(normal_icon_path, highlighted_icon_path, this);
    selectIcon->setToolTip("No device selected");
    connect(selectIcon, &ClickableLabel::clicked, this, &SelectDevicePanel::showDeviceDialog);

    const auto metricLabel = new ValueLabel("--/--", LabelSize::MEDIUM, this);
    metricLabel->setToolTip("No device selected");

    const auto spacer = new QSpacerItem(20, 20, QSizePolicy::Minimum, QSizePolicy::Expanding);

    const auto layout = new QGridLayout(this);
    layout->addWidget(selectIcon, 0, 0, Qt::AlignCenter);
    layout->addItem(spacer, 1, 0, Qt::AlignCenter);
    layout->addWidget(metricLabel, 2, 0, Qt::AlignCenter);

    const auto centralWidget = new QWidget(this);
    centralWidget->setLayout(layout);
    setCentralWidget(centralWidget);

    setStyleSheet((StyleSheets::THEME_DARK + StyleSheets::SCALE_MEDIUM).data());
}

void SelectDevicePanel::showDeviceDialog() {
    std::cout << "SelectDevicePanel::show_device_dialog()" << std::endl;
    dialog = std::make_shared<DeviceDialog>(this);
    dialog->show();
    dialog->setFocus();
}
