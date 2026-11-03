# KDE Plasma integration

`python3 install.py` installs **Brightness & Color — IO Type 68**, a combined Plasma widget with KDE display brightness, Night Light and theme controls plus the keyboard controls. Enable the widget in the system tray's entries or add it through KDE's “Add Widgets”. The original Brightness & Color entry can be disabled in system tray settings if duplicate icons are unwanted. The installer does not modify the panel layout.

The interface uses English by default and Russian in a Russian locale. It uses KDE Plasma's private `org.kde.plasma.private.brightnesscontrolplugin` module and `org.kde.plasma.workspace.dbus`. The local implementation was exercised on Plasma 6.7.5; other versions may differ. Monitor brightness uses KDE's normal PowerDevil implementation. Hardware-specific PC lighting controls are not part of this project.

The brightness and color interface is adapted from KDE PowerDevil 6.7.5, `applets/brightness` (https://invent.kde.org/plasma/powerdevil/-/tree/v6.7.5/applets/brightness). Original copyright and SPDX notices are retained in the copied QML files.

## Embedding keyboard controls in another widget

Copy `plasmoid/contents/ui/IOKeyboardControls.qml` beside the custom widget's QML and add:

```qml
IOKeyboardControls {
    Layout.fillWidth: true
}
```

Import `QtQuick.Layouts` in the parent. The component communicates with the project's session D-Bus service.
