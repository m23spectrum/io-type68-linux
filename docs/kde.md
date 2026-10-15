# KDE Plasma 6 integration

`python3 install.py` installs the widget. Add **IO Type 68 Magnetic** through KDE's “Add Widgets”.

The widget requires Plasma 6, Kirigami, QtQuick Dialogs, Plasma Components and `org.kde.plasma.workspace.dbus`. Interface language: Russian.

The default popup is 680 × 800 logical pixels with scrolling. Plasma may restore a previous popup size; resize it if necessary.

## Embedding in a custom widget

Copy `plasmoid/contents/ui/IOKeyboardControls.qml` beside the custom widget's QML and add:

```qml
IOKeyboardControls {
    Layout.fillWidth: true
}
```

Import `QtQuick.Layouts` in the parent and allow approximately 680 px for the keyboard layout. The component communicates with the project's session D-Bus service.

Embedding in KDE's brightness menu requires a custom menu implementation. The installer adds a standalone widget.
