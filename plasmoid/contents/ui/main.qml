// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.components as PC
import org.kde.kirigami as Kirigami
PlasmoidItem {
    id: applet
    Plasmoid.icon: "input-keyboard"
    compactRepresentation: PC.ToolButton {
        icon.name: "input-keyboard"
        Accessible.name: "IO Type 68 Magnetic"
        onClicked: applet.expanded = !applet.expanded
    }
    fullRepresentation: PC.ScrollView {
        implicitWidth: 620
        implicitHeight: 650
        contentWidth: availableWidth
        IOKeyboardControls { width: parent.width }
    }
}
