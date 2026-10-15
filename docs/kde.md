# KDE Plasma 6 integration

The standalone widget contains the keyboard controls from the original brightness-menu integration. Installation adds an independent widget; it never patches system QML or rewrites the panel configuration.

To embed it into a custom brightness widget, copy `plasmoid/contents/ui/IOKeyboardControls.qml` beside that widget's QML and add:

```qml
IOKeyboardControls {
    Layout.fillWidth: true
}
```

The parent needs `import QtQuick.Layouts` and enough width for the keyboard layout (approximately 680 px). The component uses Plasma Components, Kirigami, QtQuick Dialogs and `org.kde.plasma.workspace.dbus`. It requires the session D-Bus service supplied by this project. Russian labels are retained from the original prototype; translated UI catalogs are not yet provided.

This intentionally does not vendor KDE's native brightness, night light or theme controls. KDE's shipped brightness widget may live in a compiled plugin, and its internal QML API is version-specific. There is no stable supported upstream extension hook claimed here. A custom menu must keep its own KDE license notices and be tested against its Plasma release.

The prior all-in-one bridge has extra PC RGB/monitor methods. Keep that bridge if those features are needed: the new CLI and keyboard control component use the same keyboard API, while the keyboard-only service does not replace the extra APIs.

The default popup is 680 × 800 logical pixels with padding, and remains scrollable on smaller displays. Plasma may retain the size from a previously installed widget; resize its popup if an old size is restored.
